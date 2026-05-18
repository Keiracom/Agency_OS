"""KEI-126 — tests for scripts/backup_postgres.sh.

Mocks pg_dump + aws + date binaries via PATH override so the test suite
runs without a live Postgres / S3 endpoint. Asserts:
  - Missing required env → exit non-zero with clear error
  - pg_dump invoked with the right flags (-Fc, --no-owner, --no-acl)
  - aws s3 cp targets the correct bucket + key
  - Retention prune runs aws s3 rm on old keys (older than retention cutoff)
  - Empty snapshot (<1KB) refused (security: don't overwrite good backup with empty)
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "backup_postgres.sh"


def _make_fake_bin(tmp_path: Path, *, snapshot_bytes: int = 4096) -> Path:
    """Build a tmp bin/ dir with fake pg_dump, aws, stat. PATH override
    intercepts them so the script runs without real binaries."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)

    # Fake pg_dump: write a file of the configured size + log invocation.
    pg_dump = bin_dir / "pg_dump"
    pg_dump.write_text(
        f"""#!/usr/bin/env bash
echo "pg_dump $*" >> "{tmp_path}/calls.log"
# Find --file=PATH or -f PATH
out=""
for ((i=1; i<=$#; i++)); do
    if [[ "${{!i}}" == --file=* ]]; then
        out="${{!i#--file=}}"
        break
    fi
done
[[ -z "$out" ]] && out="/tmp/postgres-backup.dump"
head -c {snapshot_bytes} /dev/urandom > "$out"
"""
    )
    pg_dump.chmod(0o755)

    # Fake aws: log invocation, return canned list-objects-v2 output on demand.
    aws = bin_dir / "aws"
    aws.write_text(
        f"""#!/usr/bin/env bash
echo "aws $*" >> "{tmp_path}/calls.log"
# Simulate `aws s3api list-objects-v2 --query '...' --output text` returning
# 2 keys: one fresh (today), one stale (14 days ago).
if [[ "$1" == "s3api" && "$2" == "list-objects-v2" ]]; then
    today="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
    stale="$(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%S.000Z)"
    printf 'postgres/today.dump\\t%s\\npostgres/stale.dump\\t%s\\n' "$today" "$stale"
fi
exit 0
"""
    )
    aws.chmod(0o755)

    return bin_dir


def _env(bin_dir: Path, **overrides) -> dict:
    """Build a clean env with the required vars set + PATH override."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("AWS_", "DATABASE_", "SUPABASE_DB_"))
    }
    env.update(
        {
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "AWS_S3_BUCKET": "test-bucket",
            "AWS_S3_ENDPOINT": "https://s3.example.com",
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "POSTGRES_BACKUP_RETENTION_DAYS": "7",
        }
    )
    env.update(overrides)
    return env


def _run(env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
    )


# ─── missing env ─────────────────────────────────────────────────────────


def test_fails_when_dsn_missing(tmp_path):
    bin_dir = _make_fake_bin(tmp_path)
    env = _env(bin_dir)
    env.pop("DATABASE_URL", None)
    env.pop("SUPABASE_DB_URL", None)
    result = _run(env)
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr or "SUPABASE_DB_URL" in result.stderr


def test_fails_when_aws_bucket_missing(tmp_path):
    bin_dir = _make_fake_bin(tmp_path)
    env = _env(bin_dir)
    env.pop("AWS_S3_BUCKET")
    result = _run(env)
    assert result.returncode != 0
    assert "AWS_S3_BUCKET" in result.stderr


# ─── happy path ───────────────────────────────────────────────────────────


def test_pg_dump_invoked_with_correct_flags(tmp_path):
    bin_dir = _make_fake_bin(tmp_path)
    env = _env(bin_dir)
    result = _run(env)
    assert result.returncode == 0, result.stderr
    calls = (tmp_path / "calls.log").read_text()
    # pg_dump must run with custom format + no-owner + no-acl + DSN
    assert "pg_dump" in calls
    assert "-Fc" in calls
    assert "--no-owner" in calls
    assert "--no-acl" in calls
    assert "--file=" in calls
    assert "postgresql://test:test@localhost/test" in calls


def test_aws_s3_cp_targets_correct_bucket(tmp_path):
    bin_dir = _make_fake_bin(tmp_path)
    env = _env(bin_dir)
    result = _run(env)
    assert result.returncode == 0, result.stderr
    calls = (tmp_path / "calls.log").read_text()
    assert "aws s3 cp" in calls
    assert "s3://test-bucket/postgres/" in calls
    assert "https://s3.example.com" in calls  # endpoint url


def test_strips_asyncpg_suffix_from_dsn(tmp_path):
    bin_dir = _make_fake_bin(tmp_path)
    env = _env(bin_dir)
    env["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"
    result = _run(env)
    assert result.returncode == 0, result.stderr
    calls = (tmp_path / "calls.log").read_text()
    # pg_dump should NOT see the +asyncpg suffix
    assert "+asyncpg" not in calls
    assert "postgresql://test:test@localhost/test" in calls


# ─── retention prune ─────────────────────────────────────────────────────


def test_prunes_stale_snapshots(tmp_path):
    """Fake aws list returns 2 keys: today (keep) + 14d-old (prune).
    Script must aws s3 rm only the stale one."""
    bin_dir = _make_fake_bin(tmp_path)
    env = _env(bin_dir)
    result = _run(env)
    assert result.returncode == 0, result.stderr
    calls = (tmp_path / "calls.log").read_text()
    assert "aws s3 rm" in calls
    assert "postgres/stale.dump" in calls
    # Today's snapshot must NOT be in the rm call
    rm_lines = [line for line in calls.splitlines() if "s3 rm" in line]
    assert all("today.dump" not in line for line in rm_lines), (
        f"today's snapshot was incorrectly pruned: {rm_lines}"
    )


# ─── security: empty / tiny snapshot refused ─────────────────────────────


def test_refuses_empty_snapshot(tmp_path):
    """pg_dump produces a 0-byte file (e.g. permission denied) → backup
    script refuses to overwrite the existing good snapshot in S3."""
    bin_dir = _make_fake_bin(tmp_path, snapshot_bytes=0)
    env = _env(bin_dir)
    result = _run(env)
    assert result.returncode != 0
    assert "snapshot suspiciously small" in result.stderr
    # MUST NOT have called aws s3 cp
    calls = (tmp_path / "calls.log").read_text() if (tmp_path / "calls.log").exists() else ""
    assert "aws s3 cp" not in calls


def test_refuses_tiny_snapshot_under_1kb(tmp_path):
    """Sub-1KB snapshot = likely failure mode (truncated dump). Refuse."""
    bin_dir = _make_fake_bin(tmp_path, snapshot_bytes=512)
    env = _env(bin_dir)
    result = _run(env)
    assert result.returncode != 0
    assert "<1KB" in result.stderr or "suspiciously small" in result.stderr
    calls = (tmp_path / "calls.log").read_text() if (tmp_path / "calls.log").exists() else ""
    assert "aws s3 cp" not in calls
