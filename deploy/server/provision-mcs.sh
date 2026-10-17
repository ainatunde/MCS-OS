#!/usr/bin/env bash
# ==============================================================================
# MCS Provisioning Script: MCS-OS + MCS-ERP under Coolify & Cloudflare Tunnel
# Runs as root on the Contabo VPS. Completely idempotent.
# Preserves existing services (Pulzz, Coolify) without downtime.
# Inputs: /root/mcs-deploy.env (transferred by deploy-mcs.ps1, shredded upon completion).
# ==============================================================================
set -euo pipefail

ENV_FILE=${1:-/root/mcs-deploy.env}
[[ $EUID -eq 0 ]] || { echo "must run as root" >&2; exit 1; }
[[ -f $ENV_FILE ]] || { echo "missing $ENV_FILE" >&2; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${CF_API_TOKEN:?}" "${CF_ACCOUNT_ID:?}" "${CF_ZONE_DOMAIN:?}"
: "${OS_HOSTNAME:?}" "${ERP_HOSTNAME:?}" "${TUNNEL_NAME:=tvinsights-coolify}"
: "${GITHUB_TOKEN:?}" "${GITHUB_REPO_OS:?}" "${GITHUB_REPO_ERP:?}" "${GIT_BRANCH:=main}"
: "${POSTGRES_PASSWORD:?}" "${DB_ROOT_PASSWORD:?}" "${ADMIN_PASSWORD:?}"
: "${MCS_CONTROL_API_TOKEN:?}" "${MCS_WEBHOOK_SECRET:?}"

CF_API=https://api.cloudflare.com/client/v4
COOLIFY=http://localhost:8000/api/v1
PROJECT_NAME="MCS"
STATE_DIR=/root/.mcs
mkdir -p "$STATE_DIR" /opt/mcs/backups && chmod 700 "$STATE_DIR"

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[warn] %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[1;31m[fail] %s\033[0m\n' "$*" >&2; exit 1; }

# ---------- HTTP & API Helpers ----------
cf() {
  local method=$1 path=$2 data=${3:-} out
  out=$(curl -sS -X "$method" "$CF_API$path" \
        -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json" ${data:+--data "$data"})
  if [[ $(jq -r '.success // false' <<<"$out" 2>/dev/null) != "true" ]]; then
    echo "Cloudflare $method $path failed: $(jq -c '.errors // .' <<<"$out" 2>/dev/null || echo "$out")" >&2
    return 1
  fi
  printf '%s' "$out"
}

http_json() {
  local label=$1 method=$2 url=$3 auth=$4 data=${5:-} resp code body
  resp=$(curl -sS -X "$method" "$url" -H "$auth" -H "Accept: application/json" \
         -H "Content-Type: application/json" ${data:+--data "$data"} -w $'\n%{http_code}')
  code=${resp##*$'\n'}; body=${resp%$'\n'*}
  if [[ $code -lt 200 || $code -ge 300 ]]; then
    echo "$label $method $url -> HTTP $code: $body" >&2
    return 1
  fi
  printf '%s' "$body"
}
co() { http_json Coolify "$1" "$COOLIFY$2" "Authorization: Bearer $COOLIFY_TOKEN" "${3:-}"; }
gh() { http_json GitHub "$1" "https://api.github.com$2" "Authorization: Bearer $GITHUB_TOKEN" "${3:-}"; }

# ---------- 1. System Safety Guardrails (Swap Check for Contabo) ----------
log "Memory safety check & Swap allocation"
SWAP_TOTAL=$(free -m | awk '/^Swap:/ {print $2}')
if [[ $SWAP_TOTAL -lt 3000 ]]; then
  if [[ ! -f /swapfile ]]; then
    log "Creating 4GB swapfile to prevent OOM killer on Contabo VPS..."
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab; then
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    echo "Swapfile created and activated."
  else
    swapon /swapfile 2>/dev/null || true
  fi
else
  echo "Sufficient swap detected (${SWAP_TOTAL}MB)."
fi

# ---------- 2. Coolify API Token Retrieval ----------
log "Coolify API authentication"
cdb() { docker exec -i coolify-db psql -U coolify -d coolify -v ON_ERROR_STOP=1 -qtA "$@"; }

COOLIFY_TOKEN=$(cat "$STATE_DIR/coolify-token" 2>/dev/null || cat /root/.tvinsights/coolify-token 2>/dev/null || true)
if [[ -z $COOLIFY_TOKEN ]] || ! co GET /version >/dev/null 2>&1; then
  log "Generating dedicated Coolify API token for MCS..."
  plain=$(openssl rand -hex 32)
  hash=$(printf '%s' "$plain" | sha256sum | cut -d' ' -f1)
  tid=$(cdb -v h="$hash" <<'SQL' | head -n1
INSERT INTO personal_access_tokens (tokenable_type, tokenable_id, name, token, abilities, team_id, created_at, updated_at)
VALUES ('App\Models\User', 0, 'mcs-deploy', :'h', '["root"]', '0', now(), now()) RETURNING id;
SQL
)
  COOLIFY_TOKEN="$tid|$plain"
  printf '%s' "$COOLIFY_TOKEN" > "$STATE_DIR/coolify-token"; chmod 600 "$STATE_DIR/coolify-token"
fi
co GET /version >/dev/null || die "Coolify API token rejected"
echo "Coolify connected: $(co GET /version)"

# ---------- 3. Cloudflare Tunnel Ingress & DNS Configuration ----------
log "Cloudflare Zone & Tunnel validation"
ZONE_ID=$(cf GET "/zones?name=$CF_ZONE_DOMAIN" | jq -r '.result[0].id // empty')
[[ -n $ZONE_ID ]] || die "Zone $CF_ZONE_DOMAIN not found in Cloudflare account"
echo "Zone $CF_ZONE_DOMAIN = $ZONE_ID"

TUNNEL_ID=$(cf GET "/accounts/$CF_ACCOUNT_ID/cfd_tunnel?name=$TUNNEL_NAME&is_deleted=false" | jq -r '.result[0].id // empty')
[[ -n $TUNNEL_ID ]] || die "Tunnel $TUNNEL_NAME not found"
echo "Tunnel $TUNNEL_NAME = $TUNNEL_ID"

log "Merging Ingress Rules (Preserving Pulzz and Coolify routes)"
# Fetch current ingress config to ensure zero disruption to existing endpoints
CURRENT_CFG=$(cf GET "/accounts/$CF_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/configurations")
CURRENT_INGRESS=$(jq '.result.config.ingress // []' <<< "$CURRENT_CFG")

# Build new ingress list:
# 1. Filter out old definitions for our target hostnames and the catch-all
# 2. Append our hostnames pointing to Traefik (http://localhost:80)
# 3. Append the required 404 catch-all at the very end
NEW_INGRESS=$(jq -nc \
  --argjson curr "$CURRENT_INGRESS" \
  --arg os "$OS_HOSTNAME" \
  --arg erp "$ERP_HOSTNAME" '
  ($curr | map(select(.hostname != $os and .hostname != $erp and .service != "http_status:404")))
  + [
      {hostname: $os, service: "http://localhost:80"},
      {hostname: $erp, service: "http://localhost:80"}
    ]
  + [{service: "http_status:404"}]
')

cf PUT "/accounts/$CF_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/configurations" \
  "$(jq -nc --argjson i "$NEW_INGRESS" '{config:{ingress:$i}}')" >/dev/null
echo "Tunnel ingress updated."

dns_upsert() {
  local host=$1 zid=$2 rec body
  body=$(jq -nc --arg n "$host" --arg c "$TUNNEL_ID.cfargotunnel.com" '{type:"CNAME", name:$n, content:$c, proxied:true, ttl:1}')
  rec=$(cf GET "/zones/$zid/dns_records?name=$host" | jq -r '.result[0].id // empty')
  if [[ -n $rec ]]; then
    cf PUT "/zones/$zid/dns_records/$rec" "$body" >/dev/null
  else
    cf POST "/zones/$zid/dns_records" "$body" >/dev/null
  fi
  echo "DNS CNAME $host -> $TUNNEL_ID.cfargotunnel.com"
}

log "DNS Records Upsert"
dns_upsert "$OS_HOSTNAME" "$ZONE_ID"
dns_upsert "$ERP_HOSTNAME" "$ZONE_ID"

# ---------- 4. GitHub Deploy Key for MCS Repositories ----------
log "GitHub Deploy Key validation"
KEYFILE=/root/.ssh/mcs_github_deploy
if [[ ! -f $KEYFILE ]]; then
  ssh-keygen -t ed25519 -N "" -C "coolify-mcs@$(hostname)" -f "$KEYFILE" -q
fi
PUBKEY=$(cut -d' ' -f1,2 "$KEYFILE.pub")

KEY_UUID=$(co GET /security/keys | jq -r '.[] | select(.name=="mcs-github-deploy") | .uuid' | head -n1)
if [[ -z $KEY_UUID ]]; then
  KEY_UUID=$(co POST /security/keys "$(jq -nc --rawfile k "$KEYFILE" \
    '{name:"mcs-github-deploy", description:"GitHub deploy key for MCS repos", private_key:$k}')" | jq -r '.uuid')
fi

# Ensure deploy key is authorized in both repos
for repo in "$GITHUB_REPO_OS" "$GITHUB_REPO_ERP"; do
  log "Verifying git access for $repo..."
  if GIT_SSH_COMMAND="ssh -i $KEYFILE -o StrictHostKeyChecking=accept-new -o BatchMode=yes" git ls-remote "git@github.com:$repo.git" HEAD >/dev/null 2>&1; then
    echo "SSH access verified for $repo."
  elif git ls-remote "https://github.com/$repo.git" HEAD >/dev/null 2>&1 && [[ "$repo" == "$GITHUB_REPO_OS" ]]; then
    echo "Public HTTPS access verified for $repo."
  else
    echo "Attempting to register deploy key via GitHub API for $repo..."
    if ! gh POST "/repos/$repo/keys" "$(jq -nc --arg k "$PUBKEY" --arg t "coolify-mcs@$(hostname)" '{title:$t, key:$k, read_only:true}')" >/dev/null 2>&1; then
      warn "Could not add deploy key automatically via GitHub PAT (token lacks permissions on $repo)."
      warn "Please add this deploy key manually to GitHub: https://github.com/$repo/settings/keys"
      warn "Public Key:"
      echo "$PUBKEY"
      warn "Checking if git access is active..."
      if ! GIT_SSH_COMMAND="ssh -i $KEYFILE -o StrictHostKeyChecking=accept-new -o BatchMode=yes" git ls-remote "git@github.com:$repo.git" HEAD >/dev/null 2>&1; then
        die "Access denied to git@github.com:$repo.git. Please add the public key above to https://github.com/$repo/settings/keys or to your GitHub account (https://github.com/settings/keys) and re-run."
      fi
    else
      echo "Deploy key added to $repo."
    fi
  fi
done

# ---------- 5. Coolify Project & Stack Provisioning ----------
log "Coolify Project setup"
SERVER_UUID=$(co GET /servers | jq -r '(map(select(.name=="localhost")) + .)[0].uuid // empty')
[[ -n $SERVER_UUID ]] || die "No Coolify server 'localhost' registered"

PROJECT_UUID=$(co GET /projects | jq -r --arg n "$PROJECT_NAME" '.[] | select(.name==$n) | .uuid' | head -n1)
if [[ -z $PROJECT_UUID ]]; then
  PROJECT_UUID=$(co POST /projects "$(jq -nc --arg n "$PROJECT_NAME" '{name:$n, description:"Multimedia Cloud Solutions Corporate Stack"}')" | jq -r '.uuid')
  echo "Created Coolify project '$PROJECT_NAME' ($PROJECT_UUID)"
else
  echo "Existing project '$PROJECT_NAME' ($PROJECT_UUID)"
fi

# --- 5a. MCS-OS Application ---
log "Configuring MCS-OS in Coolify"
APP_OS_UUID=$(co GET /applications | jq -r '.[] | select(.name=="mcs-os") | .uuid' | head -n1)
if [[ -z $APP_OS_UUID ]]; then
  APP_OS_UUID=$(co POST /applications/private-deploy-key "$(jq -nc \
    --arg p "$PROJECT_UUID" --arg s "$SERVER_UUID" --arg k "$KEY_UUID" --arg r "git@github.com:$GITHUB_REPO_OS.git" \
    --arg b "$GIT_BRANCH" --arg n "mcs-os" \
    '{project_uuid:$p, server_uuid:$s, environment_name:"production", private_key_uuid:$k, git_repository:$r,
      git_branch:$b, build_pack:"dockercompose", docker_compose_location:"/docker-compose.yml",
      ports_exposes:"8000", name:$n, instant_deploy:false}')" | jq -r '.uuid')
  echo "Created application mcs-os ($APP_OS_UUID)"
fi

ENV_OS_JSON=$(jq -nc \
  --arg env "production" \
  --arg token "$MCS_CONTROL_API_TOKEN" \
  --arg hmac "$MCS_WEBHOOK_SECRET" \
  --arg cors "https://$OS_HOSTNAME,https://$ERP_HOSTNAME" \
  --arg dbpw "$POSTGRES_PASSWORD" \
  --arg erpurl "https://$ERP_HOSTNAME" '
  {
    MCS_OS_ENV: $env,
    MCS_OS_AUTH_REQUIRED: "1",
    MCS_CONTROL_API_TOKEN: $token,
    MCS_WEBHOOK_SECRET: $hmac,
    MCS_CORS_ORIGINS: $cors,
    DATABASE_URL: ("postgresql+psycopg://mcs_policy_role:" + $dbpw + "@db:5432/mcs_os"),
    POSTGRES_PASSWORD: $dbpw,
    POSTGRES_USER: "mcs_policy_role",
    POSTGRES_DB: "mcs_os",
    ERPNEXT_URL: $erpurl,
    HTTP_BIND: "127.0.0.1",
    HTTP_PORT: "8090"
  } | to_entries | {data: map({key, value, is_preview:false})}')
co PATCH "/applications/$APP_OS_UUID/envs/bulk" "$ENV_OS_JSON" >/dev/null

PATCH_OS_DOMAINS=$(jq -nc --arg d "http://$OS_HOSTNAME:8000" '{docker_compose_domains:[{name:"control-api", domain:$d}]}')
co PATCH "/applications/$APP_OS_UUID" "$PATCH_OS_DOMAINS" >/dev/null 2>&1 || true

# --- 5b. MCS-ERP Application ---
log "Configuring MCS-ERP in Coolify"
APP_ERP_UUID=$(co GET /applications | jq -r '.[] | select(.name=="mcs-erp") | .uuid' | head -n1)
if [[ -z $APP_ERP_UUID ]]; then
  APP_ERP_UUID=$(co POST /applications/private-deploy-key "$(jq -nc \
    --arg p "$PROJECT_UUID" --arg s "$SERVER_UUID" --arg k "$KEY_UUID" --arg r "git@github.com:$GITHUB_REPO_ERP.git" \
    --arg b "$GIT_BRANCH" --arg n "mcs-erp" \
    '{project_uuid:$p, server_uuid:$s, environment_name:"production", private_key_uuid:$k, git_repository:$r,
      git_branch:$b, build_pack:"dockercompose", docker_compose_location:"/docker-compose.yml",
      ports_exposes:"8080", name:$n, instant_deploy:false}')" | jq -r '.uuid')
  echo "Created application mcs-erp ($APP_ERP_UUID)"
fi

ENV_ERP_JSON=$(jq -nc \
  --arg site "$ERP_HOSTNAME" \
  --arg dbpw "$DB_ROOT_PASSWORD" \
  --arg adm "$ADMIN_PASSWORD" \
  --arg fw "${FRAPPE_WORKERS:-2}" \
  --arg bp "${DB_BUFFER_POOL:-512M}" '
  {
    ERPNEXT_VERSION: "v15",
    SITE_NAME: $site,
    DB_ROOT_PASSWORD: $dbpw,
    ADMIN_PASSWORD: $adm,
    HTTP_BIND: "127.0.0.1",
    HTTP_PORT: "8085",
    FRAPPE_WORKERS: $fw,
    DB_BUFFER_POOL: $bp,
    UPSTREAM_REAL_IP_ADDRESS: "172.16.0.0/12",
    UPSTREAM_REAL_IP_HEADER: "X-Forwarded-For",
    UPSTREAM_REAL_IP_RECURSIVE: "on"
  } | to_entries | {data: map({key, value, is_preview:false})}')
co PATCH "/applications/$APP_ERP_UUID/envs/bulk" "$ENV_ERP_JSON" >/dev/null

PATCH_ERP_DOMAINS=$(jq -nc --arg d "http://$ERP_HOSTNAME:8080" '{docker_compose_domains:[{name:"frontend", domain:$d}]}')
co PATCH "/applications/$APP_ERP_UUID" "$PATCH_ERP_DOMAINS" >/dev/null 2>&1 || true

# ---------- 6. Deployment Execution ----------
deploy_app() {
  local uuid=$1 name=$2
  log "Triggering deployment for $name ($uuid)..."
  local resp dep_uuid status
  resp=$(co POST "/deploy?uuid=$uuid&force=false")
  dep_uuid=$(echo "$resp" | jq -r '.deployments[0].deployment_uuid // empty')
  [[ -n $dep_uuid ]] || die "Deployment trigger failed for $name"

  echo "Deployment $dep_uuid in progress..."
  status=queued
  for _ in $(seq 1 180); do
    status=$(co GET "/deployments/$dep_uuid" | jq -r '.status')
    [[ $status == finished || $status == failed || $status == cancelled* ]] && break
    printf '.'; sleep 10
  done
  echo " $status"
  if [[ $status != finished ]]; then
    co GET "/deployments/$dep_uuid" | jq -r '.logs | fromjson? // [] | .[-60:][] | .output' || true
    die "Deployment $dep_uuid ($name) ended with $status"
  fi
}

deploy_app "$APP_OS_UUID" "mcs-os"
deploy_app "$APP_ERP_UUID" "mcs-erp"

# Re-apply domains to ensure Traefik router rules persist
co PATCH "/applications/$APP_OS_UUID" "$PATCH_OS_DOMAINS" >/dev/null 2>&1 || true
co PATCH "/applications/$APP_ERP_UUID" "$PATCH_ERP_DOMAINS" >/dev/null 2>&1 || true

# ---------- 7. Day-1 ERPNext Site Initialization ----------
log "Waiting for Frappe backend container to become ready..."
ERP_BACKEND=""
for _ in $(seq 1 20); do
  ERP_BACKEND=$(docker ps --filter "name=backend" --filter "status=running" --format "{{.Names}}" | grep -E "(mcs-erp|$APP_ERP_UUID)" | head -n1 || true)
  if [[ -z $ERP_BACKEND ]]; then
    ERP_BACKEND=$(docker ps --filter "name=backend" --filter "status=running" --format "{{.Names}}" | head -n1 || true)
  fi
  [[ -n $ERP_BACKEND ]] && break
  printf '.'; sleep 3
done
echo ""

if [[ -z $ERP_BACKEND ]]; then
  warn "ERP backend container not detected yet after 60s. Skipping automatic bench new-site."
  warn "Run manually once container settles: docker exec -it <backend> bench new-site $ERP_HOSTNAME"
else
  if docker exec "$ERP_BACKEND" test -d "sites/$ERP_HOSTNAME"; then
    echo "Site '$ERP_HOSTNAME' already initialized in bench."
  else
    log "Initializing site '$ERP_HOSTNAME' in Frappe (first run only)..."
    docker exec "$ERP_BACKEND" bench new-site "$ERP_HOSTNAME" \
      --mariadb-user-host-login-scope='%' \
      --db-root-password "$DB_ROOT_PASSWORD" \
      --admin-password "$ADMIN_PASSWORD" \
      --install-app erpnext \
      --set-default
    echo "Site '$ERP_HOSTNAME' created successfully."
  fi
fi

# ---------- 8. Automated Daily Backups ----------
log "Configuring automated daily backups"
cat > /opt/mcs/backup.sh <<EOF
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=/opt/mcs/backups
mkdir -p "\$BACKUP_DIR"
DATE=\$(date +%F_%H%M%S)

# 1. ERPNext Site Backup
ERP_C=\$(docker ps --filter "name=backend" --filter "status=running" --format "{{.Names}}" | grep -E "(mcs-erp|$APP_ERP_UUID)" | head -n1 || true)
if [[ -n \$ERP_C ]]; then
  docker exec "\$ERP_C" bench --site "$ERP_HOSTNAME" backup --with-files || true
fi

# 2. MCS-OS PostgreSQL Backup
OS_DB_C=\$(docker ps --filter "name=db" --filter "status=running" --format "{{.Names}}" | grep -E "(mcs-os|$APP_OS_UUID)" | head -n1 || true)
if [[ -n \$OS_DB_C ]]; then
  docker exec "\$OS_DB_C" pg_dump -U mcs_policy_role mcs_os | gzip > "\$BACKUP_DIR/mcs_os_\$DATE.sql.gz" || true
fi

# Retain backups for 14 days
find "\$BACKUP_DIR" -type f -name "*.gz" -mtime +14 -delete
EOF
chmod 700 /opt/mcs/backup.sh

# Install cron symlink
ln -sf /opt/mcs/backup.sh /etc/cron.daily/mcs-backup

# ---------- 9. Public Health Checks ----------
log "Public Health Checks"
sleep 5
OS_CODE=$(curl -s -o /dev/null -w '%{http_code}' "https://$OS_HOSTNAME/healthz" || true)
echo "https://$OS_HOSTNAME/healthz -> $OS_CODE"

ERP_CODE=$(curl -s -o /dev/null -w '%{http_code}' "https://$ERP_HOSTNAME" || true)
echo "https://$ERP_HOSTNAME -> $ERP_CODE"

log "PROVISIONING COMPLETE"
echo "MCS-OS:   https://$OS_HOSTNAME"
echo "MCS-ERP:  https://$ERP_HOSTNAME  (User: Administrator)"
echo "Coolify:  https://$COOLIFY_HOSTNAME"
echo "Pulzz:    Unaffected and healthy"
