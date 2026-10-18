"""One-time SSH key install on a fresh VPS using its root password (Windows OpenSSH cannot take a password non-interactively).

Env: VPS_IP, VPS_SSH_PORT, VPS_SSH_USER, VPS_ROOT_PASSWORD. Arg: path to the public key. Idempotent.
"""
from __future__ import annotations

import os
import shlex
import sys

import paramiko


def main() -> int:
    pub = open(sys.argv[1], encoding="utf-8").read().strip()
    host, port = os.environ["VPS_IP"], int(os.environ.get("VPS_SSH_PORT") or 22)
    user, password = os.environ.get("VPS_SSH_USER") or "root", os.environ["VPS_ROOT_PASSWORD"]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # first contact with a brand-new host (TOFU)
    try:
        client.connect(host, port=port, username=user, password=password, look_for_keys=False, allow_agent=False, timeout=20)
    except paramiko.AuthenticationException:
        print("SSH password authentication failed (wrong password, or the provider forces a password change on "
              "first login — log in once manually to set it).", file=sys.stderr)
        return 2
    cmd = (
        "umask 077; mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && "
        f"(grep -qxF {shlex.quote(pub)} ~/.ssh/authorized_keys || echo {shlex.quote(pub)} >> ~/.ssh/authorized_keys) && "
        "echo key-installed"
    )
    try:
        _, stdout, stderr = client.exec_command(cmd, timeout=30)
        out, err, rc = stdout.read().decode(), stderr.read().decode(), stdout.channel.recv_exit_status()
    finally:
        client.close()
    if rc != 0 or "key-installed" not in out:
        print(f"key install failed (rc={rc}): {err or out}", file=sys.stderr)
        return 1
    print("SSH key installed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
