# Off-host backups

Pulzz, MCS-OS and MCS-ERP share one Contabo VPS. A copy on that VPS is not a backup, so every night
`mcs-backup.sh` takes a verified copy of all three and ships it, encrypted, to Cloudflare R2.

| What | How | Verified before upload by |
| --- | --- | --- |
| Pulzz PostgreSQL | `pg_dump --format=custom` in its `db` container | reading the dump's table of contents |
| MCS-OS PostgreSQL | same | same |
| MCS-ERP (MariaDB + public/private files + site config) | `bench backup --with-files` | `gzip -t`, `tar -t`, site config present |
| Pulzz evidence vault | only files not shipped before (they never change) | uploaded size |

Each night's databases go into one archive with a `manifest.json` of SHA-256 sums, encrypted with
[age](https://age-encryption.org) to a **public** key. The private key never sits on the server, so
someone who takes over the VPS can't read old backups. With the bucket lock below, they can't
delete them either. Any failed step fails the run. Nothing is masked with `|| true`.

## One-time setup

**1. Encryption key (on your own machine, not the VPS)**

```bash
age-keygen -o mcs-backup.key
```

The file contains the private key and prints the public key (`age1…`). Put the private key in your
password manager **and** keep an offline copy. Without it, no backup can be restored.

**2. R2 bucket (Cloudflare dashboard → R2)**

1. Create bucket `mcs-backups`.
2. *Settings → Bucket lock rules*:
   * prefix `daily/`, `weekly/`, `monthly/`: retain **30 days**
   * prefix `vault/`: retain **indefinitely**
3. *Settings → Object lifecycle rules*: delete `daily/` after **35 days**, `weekly/` after **90 days**, `monthly/` after **400 days**.
   Never expire `vault/`.
4. *Manage API tokens*: create an **Object Read & Write** token **scoped to `mcs-backups` only**, for the VPS.
   Create a second **Object Read only** token for restore drills on your machine.

That keeps 35 daily, about 13 weekly and 13 monthly copies. At today's sizes (about 0.5 GB a night)
that's around 30 GB, under US$0.50 a month. R2 doesn't charge for downloads, so drills are free.

**3. Optional off-host alarm.** Create a check at healthchecks.io (or similar) with a 1-day period,
and put its URL in `HEARTBEAT_URL`. The Guardian runs on the same VPS, so if the VPS goes down the
Guardian goes with it. An outside check still alerts you.

## Install on the VPS

```bash
scp -r deploy/backup root@<vps>:/root/mcs-backup
ssh root@<vps> /root/mcs-backup/install.sh      # writes /etc/mcs-backup/backup.env, then stops
ssh root@<vps> nano /etc/mcs-backup/backup.env  # AGE_RECIPIENT, R2_*, HEARTBEAT_URL
ssh root@<vps> /root/mcs-backup/install.sh      # checks R2 access, installs the timer
ssh root@<vps> 'systemctl start mcs-backup; journalctl -u mcs-backup -n 50 --no-pager'
```

The timer runs at 02:30 WAT. `install.sh` also removes the old `/etc/cron.daily/mcs-backup` job,
which kept dumps on the VPS only and ignored failures.

## Monitoring

The job writes `/var/lib/mcs-backup/status.json`. MCS-OS mounts it read-only, and in production the
Guardian reports `offhost_backup_fresh`. That check fails if the last successful upload is more than
26 hours old, or if no upload has ever succeeded. **Expect the check to show `degraded` from the
first MCS-OS deploy that includes it until the first backup succeeds.** That's correct: until then
there is no off-host copy.

## Restore drill (monthly)

On your own machine, with Docker, `age`, `rclone` and `jq` installed and an rclone remote that uses
the **read-only** token:

```bash
./restore-drill.sh ~/secure/mcs-backup.key r2:mcs-backups
```

The drill downloads the newest nightly backup, checks every SHA-256, and restores Pulzz and MCS-OS
into throwaway Postgres containers built from the images that produced them. It restores ERPNext
into a throwaway MariaDB 10.6 and prints table and row counts. Compare the counts with the live
apps, then record the date and result.

## Real restore

Never restore over live accounting data. Restore into a new database or site, check it, then switch
over. Decrypt with `age -d -i mcs-backup.key mcs-<stamp>.tar.age | tar -xf -`, then:

* Postgres: `pg_restore --no-owner -d <new db> pulzz.dump`. Recreate the runtime roles
  (`mcs_control_runtime` and the others) as described in the release notes.
* ERPNext: `bench --site <site> restore <file>-database.sql.gz --with-public-files … --with-private-files …`.
  The `site_config_backup.json` holds the site's `encryption_key`; without it, stored passwords
  can't be decrypted.
* Vault: extract every `vault/vault-*.tar.age` in name order into the volume.
