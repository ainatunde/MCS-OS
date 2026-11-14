"""Which commit this build is, without trusting a hand-set deployment variable.

Coolify does not pass the deployed commit to a Compose application, so a stored SOURCE_COMMIT went stale the moment
the branch changed. The image keeps the checkout's HEAD and branch refs (see .dockerignore) and this module reads them.
An explicit SOURCE_COMMIT / BUILD_SHA still wins when it is a real commit id.
"""
import os
import re
from functools import lru_cache
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}$")
ROOT = Path(__file__).resolve().parents[2]


def commit_from_git(git_dir):
    """The commit id HEAD points at in a plain .git directory, or None. Reads files only; never runs git."""
    try:
        git_dir = Path(git_dir)
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if _SHA.match(head):
            return head
        if not head.startswith("ref: "):
            return None
        ref = head[5:].strip()
        if ".." in ref or not ref.startswith("refs/"):
            return None
        loose = git_dir / ref
        if loose.is_file():
            value = loose.read_text(encoding="utf-8").strip()
            return value if _SHA.match(value) else None
        for line in (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines():
            value, _, name = line.partition(" ")
            if name.strip() == ref and _SHA.match(value):
                return value
    except (OSError, ValueError):
        pass
    return None


def resolve_commit(environ=None, git_dir=None):
    environ = os.environ if environ is None else environ
    for key in ("SOURCE_COMMIT", "BUILD_SHA"):
        value = (environ.get(key) or "").strip().lower()
        if _SHA.match(value):
            return value
    return commit_from_git(ROOT / ".git" if git_dir is None else git_dir) or "unknown"


@lru_cache(maxsize=1)
def current_commit():
    return resolve_commit()
