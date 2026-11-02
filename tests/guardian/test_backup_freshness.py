"""Off-host backup freshness as the Guardian reads it from deploy/backup's status.json."""
import json

from services.control.guardian import BACKUP_MAX_AGE, backup_fresh


def write(tmp_path, body):
    path = tmp_path / "status.json"
    path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return path


def test_recent_success_is_fresh(tmp_path):
    assert backup_fresh(write(tmp_path, {"last_success_at": 1000, "last_result": "ok"}), 1000 + 3600)


def test_stale_success_is_not_fresh_even_after_a_later_failure(tmp_path):
    path = write(tmp_path, {"last_success_at": 1000, "last_result": "failed", "last_attempt_at": 1000 + BACKUP_MAX_AGE})
    assert not backup_fresh(path, 1000 + BACKUP_MAX_AGE + 1)


def test_recent_failure_does_not_hide_an_earlier_success_window(tmp_path):
    assert backup_fresh(write(tmp_path, {"last_success_at": 1000, "last_result": "failed"}), 2000)


def test_never_succeeded_missing_or_corrupt_status_is_not_fresh(tmp_path):
    assert not backup_fresh(write(tmp_path, {"last_result": "failed"}), 1000)
    assert not backup_fresh(write(tmp_path, "{not json"), 1000)
    assert not backup_fresh(tmp_path / "absent.json", 1000)
