#!/usr/bin/env bash
# Install the nightly off-host backup on the VPS. Run as root from this directory:
#
#   sudo ./install.sh
#
# First run copies backup.env.example to /etc/mcs-backup/backup.env and stops so you can fill it in.
# Re-running is safe. It does not start a backup; run `systemctl start mcs-backup` to take the first one.
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run as root" >&2; exit 1; }

CONF_DIR=/etc/mcs-backup
CONFIG=$CONF_DIR/backup.env
install -d -m 700 "$CONF_DIR" /var/backups/mcs
# The Guardian containers mount this read-only to read status.json.
install -d -m 755 /var/lib/mcs-backup

if [[ ! -f $CONFIG ]]; then
  install -m 600 backup.env.example "$CONFIG"
  echo "Wrote $CONFIG. Fill in AGE_RECIPIENT and the R2_* values, then re-run install.sh."
  exit 0
fi
chmod 600 "$CONFIG"
# shellcheck source=/dev/null
source "$CONFIG"
[[ ${AGE_RECIPIENT:-} == age1* ]] || { echo "AGE_RECIPIENT must be an age public key (age1...)" >&2; exit 1; }
for v in R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY RCLONE_REMOTE; do
  [[ -n ${!v:-} ]] || { echo "$v is not set in $CONFIG" >&2; exit 1; }
done

missing=()
for tool in age rclone jq; do command -v "$tool" >/dev/null || missing+=("$tool"); done
if [[ ${#missing[@]} -gt 0 ]]; then
  apt-get update -qq
  apt-get install -y -qq "${missing[@]}"
fi

# provider=Other works with the older rclone in distribution packages; the bucket is created in the
# Cloudflare dashboard, so the token never needs bucket-creation rights.
umask 077
cat > "$CONF_DIR/rclone.conf" <<EOF
[r2]
type = s3
provider = Other
access_key_id = $R2_ACCESS_KEY_ID
secret_access_key = $R2_SECRET_ACCESS_KEY
endpoint = https://$R2_ACCOUNT_ID.r2.cloudflarestorage.com
region = auto
no_check_bucket = true
EOF
umask 022
RCLONE_CONFIG="$CONF_DIR/rclone.conf" rclone lsjson "$RCLONE_REMOTE" --max-depth 1 >/dev/null \
  || { echo "cannot list $RCLONE_REMOTE: check the bucket name and the R2 token" >&2; exit 1; }

install -m 700 mcs-backup.sh /usr/local/sbin/mcs-backup.sh
install -m 644 mcs-backup.service mcs-backup.timer /etc/systemd/system/

# The provisioning-era job kept dumps on this host only and ignored failures (`|| true`).
if [[ -e /etc/cron.daily/mcs-backup ]]; then
  rm -f /etc/cron.daily/mcs-backup
  echo "Removed legacy /etc/cron.daily/mcs-backup (old dumps in /opt/mcs/backups are left in place)."
fi

systemctl daemon-reload
systemctl enable --now mcs-backup.timer
systemctl list-timers mcs-backup.timer --no-pager
echo "Installed. Take the first backup now with: systemctl start mcs-backup && journalctl -u mcs-backup -n 50"
