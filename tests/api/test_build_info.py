from services.control.build_info import commit_from_git, resolve_commit

A = "a" * 40
B = "b" * 40


def make_git(tmp_path, head, loose=None, packed=None):
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text(head + "\n")
    if loose:
        (git / "refs" / "heads" / "main").write_text(loose + "\n")
    if packed:
        (git / "packed-refs").write_text("# pack-refs with: peeled fully-peeled sorted\n" + packed + "\n")
    return git


def test_branch_checkout_reads_the_loose_ref(tmp_path):
    assert commit_from_git(make_git(tmp_path, "ref: refs/heads/main", loose=A)) == A


def test_branch_checkout_falls_back_to_packed_refs(tmp_path):
    git = make_git(tmp_path, "ref: refs/heads/main", packed=f"{B} refs/remotes/origin/main\n{A} refs/heads/main")
    assert commit_from_git(git) == A


def test_detached_checkout_reads_head(tmp_path):
    assert commit_from_git(make_git(tmp_path, B)) == B


def test_missing_or_odd_git_data_is_unknown_not_an_error(tmp_path):
    assert commit_from_git(tmp_path / "absent") is None
    assert commit_from_git(make_git(tmp_path, "ref: ../../etc/passwd")) is None
    assert resolve_commit({}, tmp_path / "absent") == "unknown"


def test_placeholder_variable_does_not_hide_the_real_commit(tmp_path):
    git = make_git(tmp_path, "ref: refs/heads/main", loose=A)
    assert resolve_commit({"SOURCE_COMMIT": "unknown"}, git) == A
    assert resolve_commit({"SOURCE_COMMIT": ""}, git) == A


def test_an_explicit_commit_id_still_wins(tmp_path):
    git = make_git(tmp_path, "ref: refs/heads/main", loose=A)
    assert resolve_commit({"SOURCE_COMMIT": B}, git) == B
    assert resolve_commit({"BUILD_SHA": B.upper()}, git) == B
