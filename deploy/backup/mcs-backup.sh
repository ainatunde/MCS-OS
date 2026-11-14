#!/usr/bin/env bash
# Nightly encrypted off-host backup of Pulzz, MCS-OS and MCS-ERP to object storage (Cloudflare R2).
#
#   mcs-backup.sh            run once (systemd runs it nightly, see mcs-backup.timer)
#
# Every artifact is verified before upload and encrypted on this host with `age` to a public key.
# The private key is never on the server, so a compromised VPS can neither read nor (with the bucket
# lock described in README.md) delete earlier backups. Any failed step fails the whole run: nothing
# is masked, the status file records the failure and the Guardian reports `offhost_backup_fresh`.
set -Eeuo pipefail
umask 077

CONFIG=${MCS_BACKUP_CONFIG:-/etc/mcs-backup/backup.env}
# shellcheck source=/dev/null
source "$CONFIG"
: "${AGE_RECIPIENT:?set AGE_RECIPIENT (age public key) in $CONFIG}"
: "${RCLONE_REMOTE:?set RCLONE_REMOTE (e.g. r2:mcs-backups) in $CONFIG}"
: "${PULZZ_APP:?set the Pulzz Coolify application id in $CONFIG}"
: "${OS_APP:?set the MCS-OS Coolify application id in $CONFIG}"
: "${ERP_APP:?set the MCS-ERP Coolify application id in $CONFIG}"
: "${ERP_SITE:?set ERP_SITE in $CONFIG}"
WORK_ROOT=${WORK_ROOT:-/var/backups/mcs}
STATE_DIR=${STATE_DIR:-/var/lib/mcs-backup}
MIN_FREE_MB=${MIN_FREE_MB:-3072}
KEEP_LOCAL=${KEEP_LOCAL:-2}
VAULT_MOUNT=${VAULT_MOUNT:-/app/data/vault}
export RCLONE_CONFIG=${RCLONE_CONFIG:-/etc/mcs-backup/rclone.conf}

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DAY=$(date -u +%F)
WORK="$WORK_ROOT/work-$STAMP"
ARCHIVE="$WORK_ROOT/mcs-$STAMP.tar.age"
STEP=startup
STARTED=$(date +%s)

# stderr, so messages from inside $(...) still reach the journal
log() { printf '%s [%s] %s\n' "$(date -u +%FT%TZ)" "$STEP" "$*" >&2; }

write_status() {  # result, extra JSON merged into the status document
  local result=$1 extra=${2:-'{}'} previous='{}'
  [[ -s "$STATE_DIR/status.json" ]] && previous=$(cat "$STATE_DIR/status.json")
  jq -n --argjson prev "$previous" --argjson extra "$extra" --arg result "$result" --arg step "$STEP" \
        --argjson at "$(date +%s)" --argjson started "$STARTED" \
     '$prev + {last_attempt_at: $at, last_attempt_started_at: $started, last_result: $result}
      + (if $result == "ok" then {last_success_at: $at, failed_step: null} else {failed_step: $step} end)
      + $extra' > "$STATE_DIR/status.json.tmp"
  chmod 644 "$STATE_DIR/status.json.tmp"
  mv "$STATE_DIR/status.json.tmp" "$STATE_DIR/status.json"
}

ping_heartbeat() {  # healthchecks.io-style dead man's switch; off-host, so it still alerts if this VPS is gone
  [[ -n "${HEARTBEAT_URL:-}" ]] || return 0
  curl -fsS -m 10 --retry 3 "${HEARTBEAT_URL%/}$1" >/dev/null || log "heartbeat ping failed"
}

on_error() {
  local code=$?
  trap - ERR
  # set -E hands this trap to $(...) subshells too; report once, from the main shell.
  [[ $BASH_SUBSHELL -eq 0 ]] || exit "$code"
  log "FAILED (exit $code)"
  write_status failed || true
  ping_heartbeat /fail
  exit "$code"
}
trap on_error ERR
trap 'rm -rf "$WORK" "$ARCHIVE.partial"' EXIT

mkdir -p "$WORK_ROOT" "$STATE_DIR"
exec 9>"$STATE_DIR/lock"
flock -n 9 || { echo "another backup is running" >&2; exit 75; }

container() {  # the one running container of a Coolify service: <service>-<app id>-<deploy stamp>
  local names
  names=$(docker ps --filter status=running --format '{{.Names}}' | grep -E "^$1-$2(-|$)" || true)
  if [[ $(grep -c . <<<"$names" || true) -ne 1 ]]; then
    log "expected exactly one running '$1' container for app $2, found: ${names:-none}"
    return 1
  fi
  printf '%s' "$names"
}

dump_postgres() {  # name, container -> $WORK/<name>.dump (custom format), verified by reading its table of contents
  local name=$1 c=$2 out="$WORK/$1.dump" tables
  STEP="dump-$name"
  log "pg_dump from $c"
  docker exec "$c" sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$out.partial"
  docker exec -i "$c" pg_restore --list < "$out.partial" > "$WORK/$name.toc"
  tables=$(grep -c ' TABLE DATA ' "$WORK/$name.toc" || true)
  [[ $tables -gt 0 ]] || { log "dump has no table data"; return 1; }
  mv "$out.partial" "$out"
  log "ok: $(du -h "$out" | cut -f1), $tables tables"
}

STEP=preflight
for tool in docker jq age rclone flock sha256sum; do command -v "$tool" >/dev/null || { log "missing $tool"; false; }; done
free_mb=$(df -Pm "$WORK_ROOT" | awk 'NR==2 {print $4}')
[[ $free_mb -ge $MIN_FREE_MB ]] || { log "only ${free_mb}MB free in $WORK_ROOT, need $MIN_FREE_MB"; false; }
mkdir -p "$WORK/erp"
PULZZ_DB=$(container db "$PULZZ_APP")
PULZZ_WEB=$(container web "$PULZZ_APP")
OS_DB=$(container db "$OS_APP")
ERP_BACKEND=$(container backend "$ERP_APP")

dump_postgres pulzz "$PULZZ_DB"
dump_postgres mcs-os "$OS_DB"

STEP=dump-erp
log "bench backup --with-files from $ERP_BACKEND"
# A private path, so bench's own scheduled backups in sites/<site>/private/backups are not swept up.
docker exec "$ERP_BACKEND" bench --site "$ERP_SITE" backup --with-files --backup-path "/tmp/mcs-backup-$STAMP" >/dev/null
docker cp "$ERP_BACKEND:/tmp/mcs-backup-$STAMP/." "$WORK/erp/"
docker exec "$ERP_BACKEND" rm -rf "/tmp/mcs-backup-$STAMP"
shopt -s nullglob
erp_db=("$WORK"/erp/*-database.sql.gz)
erp_config=("$WORK"/erp/*-site_config_backup.json)
[[ ${#erp_db[@]} -eq 1 && ${#erp_config[@]} -eq 1 ]] || { log "bench output incomplete: $(ls "$WORK/erp")"; false; }
gzip -t "${erp_db[0]}"
for tarball in "$WORK"/erp/*files*.tar; do tar -tf "$tarball" >/dev/null; done
shopt -u nullglob
log "ok: $(du -sh "$WORK/erp" | cut -f1)"

STEP=manifest
jq -n --arg stamp "$STAMP" --arg host "$(hostname)" \
      --arg pulzz_image "$(docker inspect -f '{{.Config.Image}}' "$PULZZ_DB")" \
      --arg os_image "$(docker inspect -f '{{.Config.Image}}' "$OS_DB")" \
      --arg erp_image "$(docker inspect -f '{{.Config.Image}}' "$ERP_BACKEND")" \
      --arg erp_site "$ERP_SITE" \
      --argjson files "$(cd "$WORK" && find . -type f ! -name '*.toc' -printf '%P\n' | sort | xargs sha256sum \
                          | jq -R 'split("  ") | {(.[1]): .[0]}' | jq -s add)" \
   '{stamp: $stamp, host: $host, erp_site: $erp_site,
     images: {pulzz_db: $pulzz_image, mcs_os_db: $os_image, erp_backend: $erp_image}, sha256: $files}' \
   > "$WORK/manifest.json"

STEP=encrypt
tar -C "$WORK" -cf - . | age -r "$AGE_RECIPIENT" > "$ARCHIVE.partial"
mv "$ARCHIVE.partial" "$ARCHIVE"
size=$(stat -c %s "$ARCHIVE")
log "ok: $(du -h "$ARCHIVE" | cut -f1)"

STEP=upload
dest="daily/$DAY/mcs-$STAMP.tar.age"
rclone copyto "$ARCHIVE" "$RCLONE_REMOTE/$dest" --s3-no-check-bucket
remote_size=$(rclone lsjson "$RCLONE_REMOTE/$dest" --s3-no-check-bucket | jq '.[0].Size')
[[ $remote_size == "$size" ]] || { log "uploaded size $remote_size != local $size"; false; }
copies=("$dest")
if [[ $(date -u +%u) == 7 ]]; then copies+=("weekly/$DAY/mcs-$STAMP.tar.age"); fi
if [[ $(date -u +%d) == 01 ]]; then copies+=("monthly/${DAY%-*}/mcs-$STAMP.tar.age"); fi
for extra in "${copies[@]:1}"; do
  rclone copyto "$RCLONE_REMOTE/$dest" "$RCLONE_REMOTE/$extra" --s3-no-check-bucket
done
log "ok: ${copies[*]}"

STEP=vault
# Pulzz evidence files are content-addressed and never change: upload only the ones not shipped yet.
vault_src=$(docker inspect -f "{{range .Mounts}}{{if eq .Destination \"$VAULT_MOUNT\"}}{{.Source}}{{end}}{{end}}" "$PULZZ_WEB")
[[ -n $vault_src && -d $vault_src ]] || { log "vault volume not found on $PULZZ_WEB"; false; }
touch "$STATE_DIR/vault.shipped"
(cd "$vault_src" && find . -type f -printf '%P\n' | LC_ALL=C sort) > "$WORK/vault.now"
LC_ALL=C comm -23 "$WORK/vault.now" <(LC_ALL=C sort "$STATE_DIR/vault.shipped") > "$WORK/vault.new"
new_files=$(grep -c . "$WORK/vault.new" || true)
if [[ $new_files -gt 0 ]]; then
  vault_archive="$WORK_ROOT/vault-$STAMP.tar.age"
  tar -C "$vault_src" -cf - -T "$WORK/vault.new" | age -r "$AGE_RECIPIENT" > "$vault_archive"
  rclone copyto "$vault_archive" "$RCLONE_REMOTE/vault/vault-$STAMP.tar.age" --s3-no-check-bucket
  [[ $(rclone lsjson "$RCLONE_REMOTE/vault/vault-$STAMP.tar.age" --s3-no-check-bucket | jq '.[0].Size') == "$(stat -c %s "$vault_archive")" ]] \
    || { log "vault upload size mismatch"; false; }
  rm -f "$vault_archive"
  cat "$WORK/vault.new" >> "$STATE_DIR/vault.shipped"
fi
log "ok: $new_files new evidence files"

STEP=retain-local
# Keep the newest encrypted archives here for a fast restore; R2 lifecycle rules handle remote retention.
ls -1t "$WORK_ROOT"/mcs-*.tar.age | tail -n +"$((KEEP_LOCAL + 1))" | xargs -r rm -f

STEP=done
write_status ok "$(jq -n --arg object "$dest" --argjson bytes "$size" --argjson vault_new "$new_files" \
                   '{last_object: $object, last_bytes: $bytes, last_vault_files: $vault_new}')"
ping_heartbeat ""
log "backup complete in $(( $(date +%s) - STARTED ))s"
