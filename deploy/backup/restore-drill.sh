#!/usr/bin/env bash
# Monthly restore drill. Run on a machine OTHER than the VPS (a laptop with Docker is enough):
#
#   ./restore-drill.sh <age private key file> <rclone remote:bucket> [object path]
#
# Downloads the newest daily backup (or the given object), decrypts it, checks every file against the
# manifest, and restores all three databases into throwaway containers built from the same images that
# produced them. Nothing touches production. Prints row counts you can compare with the live apps.
set -Eeuo pipefail
KEY=${1:?age private key file}
REMOTE=${2:?rclone remote, e.g. r2:mcs-backups}
OBJECT=${3:-}
RUN=mcs-drill-$(date +%s)-$RANDOM
DIR=$(mktemp -d)
cleanup() { docker rm -f "$RUN-pulzz" "$RUN-mcs-os" "$RUN-erp" >/dev/null 2>&1 || true; rm -rf "$DIR"; }
trap cleanup EXIT

if [[ -z $OBJECT ]]; then
  OBJECT=$(rclone lsf -R "$REMOTE/daily" --files-only | sort | tail -n 1)
  OBJECT="daily/$OBJECT"
fi
echo "== $OBJECT"
rclone copyto "$REMOTE/$OBJECT" "$DIR/backup.tar.age"
mkdir "$DIR/x"
age -d -i "$KEY" "$DIR/backup.tar.age" | tar -C "$DIR/x" -xf -
cd "$DIR/x"
jq -r '.sha256 | to_entries[] | "\(.value)  \(.key)"' manifest.json | sha256sum -c --quiet
echo "checksums: ok ($(jq '.sha256 | length' manifest.json) files)"

restore_pg() {  # name, image
  local name=$1 image=$2 c="$RUN-$1"
  docker run -d --name "$c" -e POSTGRES_PASSWORD=drill -e POSTGRES_DB=drill "$image" >/dev/null
  # TCP only answers once the image has finished its init-time restart.
  until docker exec "$c" pg_isready -h 127.0.0.1 -U postgres -d drill >/dev/null 2>&1; do sleep 1; done
  docker exec -i "$c" pg_restore -U postgres -d drill --no-owner --no-privileges --exit-on-error < "$name.dump"
  echo "$name: $(docker exec "$c" psql -U postgres -d drill -Atc \
    "select count(*) || ' tables, alembic ' || coalesce((select string_agg(version_num, ',') from alembic_version), '-')
       from information_schema.tables where table_schema = 'public'" 2>/dev/null \
    || docker exec "$c" psql -U postgres -d drill -Atc "select count(*) || ' tables' from information_schema.tables where table_schema = 'public'")"
}
restore_pg pulzz "$(jq -r .images.pulzz_db manifest.json)"
restore_pg mcs-os "$(jq -r .images.mcs_os_db manifest.json)"

c="$RUN-erp"
docker run -d --name "$c" -e MARIADB_ROOT_PASSWORD=drill -e MARIADB_DATABASE=erp mariadb:10.6 >/dev/null
until docker exec "$c" mariadb -h 127.0.0.1 -uroot -pdrill -e 'select 1' >/dev/null 2>&1; do sleep 1; done
gunzip -c erp/*-database.sql.gz | docker exec -i "$c" mariadb -uroot -pdrill erp
echo "erp: $(docker exec "$c" mariadb -uroot -pdrill erp -N -e \
  "select concat((select count(*) from \`tabSales Invoice\`), ' sales invoices, ',
                 (select count(*) from \`tabCustomer\`), ' customers, ',
                 (select count(*) from \`tabLead\`), ' leads')")"
for t in erp/*files*.tar; do echo "$(basename "$t"): $(tar -tf "$t" | wc -l) entries"; done

vault=$(rclone lsf "$REMOTE/vault" --files-only | wc -l)
echo "vault: $vault incremental archives in $REMOTE/vault"
echo "DRILL PASSED for $OBJECT"
