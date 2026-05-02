"""Tests for scripts/phase3_readiness_check.py"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup path to import the phase3_readiness_check module
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Import the check functions
from scripts import phase3_readiness_check as p3


class TestCheck1QueueKeys:
    """Test check1_queue_keys: verify Redis key existence."""

    @patch("scripts.phase3_readiness_check._get_redis")
    def test_all_keys_exist(self, mock_get_redis):
        """Should pass when all 8 expected keys exist."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Setup: all keys exist with various depths
        mock_redis.exists.side_effect = [1, 1, 1, 1, 1, 1, 1, 1]
        mock_redis.llen.side_effect = [5, 3, 0, 1, 2, 4, 1, 2]
        mock_redis.type.return_value = "list"

        passed, detail, depths = p3.check1_queue_keys()

        assert passed is True
        assert "8/8 found" in detail
        assert len(depths) == 8
        # Verify depths are captured
        assert depths["relay:inbox:elliot"] == 5
        assert depths["relay:inbox:aiden"] == 3

    @patch("scripts.phase3_readiness_check._get_redis")
    def test_required_keys_missing(self, mock_get_redis):
        """Should fail when required keys (elliot, aiden) are missing."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Setup: elliot key missing, aiden exists
        exists_values = [0, 1, 1, 1, 1, 1, 1, 1]  # relay:inbox:elliot is missing
        mock_redis.exists.side_effect = exists_values
        mock_redis.llen.side_effect = [0, 3, 0, 1, 2, 4, 1, 2]
        mock_redis.type.return_value = "list"

        passed, detail, depths = p3.check1_queue_keys()

        assert passed is False
        assert "missing" in detail
        assert depths["relay:inbox:elliot"] is None

    @patch("scripts.phase3_readiness_check._get_redis")
    def test_only_required_keys_exist(self, mock_get_redis):
        """Should pass when at least required keys (elliot, aiden) exist."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Setup: only elliot and aiden exist, others missing
        exists_values = [1, 1, 0, 0, 0, 0, 0, 0]
        mock_redis.exists.side_effect = exists_values
        mock_redis.llen.side_effect = [5, 3, 0, 0, 0, 0, 0, 0]
        mock_redis.type.return_value = "list"

        passed, detail, depths = p3.check1_queue_keys()

        assert passed is True
        assert "2/8 found" in detail
        assert "missing" in detail

    @patch("scripts.phase3_readiness_check._get_redis")
    def test_key_depths_captured(self, mock_get_redis):
        """Should capture queue depths in depths dict."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        mock_redis.exists.side_effect = [1] * 8
        mock_redis.llen.side_effect = [10, 20, 0, 5, 15, 25, 3, 7]
        mock_redis.type.return_value = "list"

        passed, detail, depths = p3.check1_queue_keys()

        assert depths["relay:inbox:elliot"] == 10
        assert depths["relay:inbox:aiden"] == 20
        assert depths["relay:inbox:scout"] == 0
        assert depths["dispatch:atlas"] == 3


class TestCheck2DualWrite:
    """Test check2_dual_write: report queue depths and warn if all empty."""

    def test_queues_have_depth(self):
        """Should pass when existing keys have depth > 0."""
        depths = {
            "relay:inbox:elliot": 5,
            "relay:inbox:aiden": 3,
            "relay:inbox:scout": 0,
            "relay:outbox:atlas": 1,
        }

        passed, detail = p3.check2_dual_write(depths)

        assert passed is True
        assert "queues with depth > 0" in detail
        assert "elliot=5" in detail or "aiden=3" in detail

    def test_all_queues_empty(self):
        """Should pass but warn when all queues have depth 0 (normal for active consumer)."""
        depths = {
            "relay:inbox:elliot": 0,
            "relay:inbox:aiden": 0,
            "relay:inbox:scout": 0,
            "relay:outbox:atlas": 0,
        }

        passed, detail = p3.check2_dual_write(depths)

        # Pass is based on existing keys, not depth > 0
        assert passed is True
        assert "0 queues with depth > 0" in detail

    def test_no_existing_keys(self):
        """Should fail when no keys exist at all."""
        depths = {
            "relay:inbox:elliot": None,
            "relay:inbox:aiden": None,
            "relay:inbox:scout": None,
            "relay:outbox:atlas": None,
        }

        passed, detail = p3.check2_dual_write(depths)

        assert passed is False

    def test_mixed_depths(self):
        """Should report correctly with mixed depths."""
        depths = {
            "relay:inbox:elliot": 5,
            "relay:inbox:aiden": None,  # missing
            "relay:inbox:scout": 0,
            "relay:outbox:atlas": 2,
        }

        passed, detail = p3.check2_dual_write(depths)

        assert passed is True
        assert "elliot=5" in detail
        assert "scout=0" in detail
        assert "atlas=2" in detail


class TestCheck3HMACRoundtrip:
    """Test check3_hmac_roundtrip: sign, push, pop, verify."""

    @patch.dict(os.environ, {"INBOX_HMAC_SECRET": "test-secret"})
    @patch("scripts.phase3_readiness_check._get_redis")
    def test_hmac_roundtrip_success(self, mock_get_redis):
        """Should pass when HMAC roundtrip succeeds."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Prepare signed payload
        secret = "test-secret"
        payload = {
            "type": "readiness_check",
            "from": "phase3_checker",
            "brief": "HMAC roundtrip test",
            "created_at": int(time.time()),
        }

        # Create a mock signed payload with valid HMAC
        import hashlib
        import hmac as hmac_mod

        filtered = {k: v for k, v in payload.items() if k != "hmac"}
        canonical = json.dumps(filtered, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected_hmac = hmac_mod.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()

        signed_payload = {**payload, "hmac": expected_hmac}

        # Mock Redis operations: push succeeds, pop returns the signed payload
        mock_redis.lpush.return_value = 1
        mock_redis.brpop.return_value = ("dispatch:_readiness_test", json.dumps(signed_payload))

        # Mock the sign function in sys.modules
        mock_security = MagicMock()
        mock_inbox_hmac = MagicMock()
        mock_inbox_hmac.sign = MagicMock(return_value=signed_payload)

        with patch.dict(
            "sys.modules",
            {"src.security": mock_security, "src.security.inbox_hmac": mock_inbox_hmac},
        ):
            passed, detail = p3.check3_hmac_roundtrip()

        assert passed is True
        assert "OK" in detail

    @patch.dict(os.environ, {}, clear=True)
    def test_hmac_no_secret(self):
        """Should fail when INBOX_HMAC_SECRET is not set."""
        # Ensure INBOX_HMAC_SECRET is not in environment
        if "INBOX_HMAC_SECRET" in os.environ:
            del os.environ["INBOX_HMAC_SECRET"]

        # Even though the function returns early, mock modules in case it's called
        mock_security = MagicMock()
        mock_inbox_hmac = MagicMock()

        with patch.dict(
            "sys.modules",
            {"src.security": mock_security, "src.security.inbox_hmac": mock_inbox_hmac},
        ):
            passed, detail = p3.check3_hmac_roundtrip()

        assert passed is False
        assert "not set" in detail

    @patch.dict(os.environ, {"INBOX_HMAC_SECRET": "test-secret"})
    @patch("scripts.phase3_readiness_check._get_redis")
    def test_hmac_pop_timeout(self, mock_get_redis):
        """Should fail when brpop times out."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        signed_payload = {"type": "readiness_check", "from": "phase3_checker", "hmac": "abc123"}

        # Simulate timeout
        mock_redis.brpop.return_value = None

        mock_security = MagicMock()
        mock_inbox_hmac = MagicMock()
        mock_inbox_hmac.sign = MagicMock(return_value=signed_payload)

        with patch.dict(
            "sys.modules",
            {"src.security": mock_security, "src.security.inbox_hmac": mock_inbox_hmac},
        ):
            passed, detail = p3.check3_hmac_roundtrip()

        assert passed is False
        assert "timed out" in detail

    @patch.dict(os.environ, {"INBOX_HMAC_SECRET": "test-secret"})
    @patch("scripts.phase3_readiness_check._get_redis")
    def test_hmac_mismatch(self, mock_get_redis):
        """Should fail when HMAC verification fails."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        signed_payload = {
            "type": "readiness_check",
            "from": "phase3_checker",
            "hmac": "wrong-hmac-value",
        }
        mock_redis.brpop.return_value = ("dispatch:_readiness_test", json.dumps(signed_payload))

        mock_security = MagicMock()
        mock_inbox_hmac = MagicMock()
        mock_inbox_hmac.sign = MagicMock(return_value=signed_payload)

        with patch.dict(
            "sys.modules",
            {"src.security": mock_security, "src.security.inbox_hmac": mock_inbox_hmac},
        ):
            passed, detail = p3.check3_hmac_roundtrip()

        assert passed is False
        assert "mismatch" in detail or "HMAC" in detail


class TestCheck4ConsumerDryRun:
    """Test check4_consumer_dry_run: import relay_consumer, validate QUEUE_MAP, check tmux."""

    @patch("subprocess.run")
    def test_import_failure(self, mock_subprocess):
        """Should fail when relay_consumer cannot be imported."""
        with patch.dict("sys.modules", {"src.relay.relay_consumer": None}):
            passed, detail = p3.check4_consumer_dry_run()

            assert passed is False
            assert "import failed" in detail

    @patch("subprocess.run")
    def test_queue_map_wrong_size(self, mock_subprocess):
        """Should fail when QUEUE_MAP doesn't have 8 entries."""
        mock_relay = MagicMock()
        mock_relay.QUEUE_MAP = {"queue1": {}, "queue2": {}}  # Only 2 entries

        with patch.dict(
            "sys.modules", {"src.relay": MagicMock(), "src.relay.relay_consumer": mock_relay}
        ):
            passed, detail = p3.check4_consumer_dry_run()

            assert passed is False
            assert "QUEUE_MAP has 2 entries" in detail

    @patch("subprocess.run")
    def test_tmux_sessions_live(self, mock_subprocess):
        """Should pass when enough tmux sessions are live."""
        # Mock subprocess to return success for tmux has-session
        mock_subprocess.return_value = MagicMock(returncode=0)

        mock_relay = MagicMock()
        queue_map = {
            "queue1": {"tmux": "elliottbot:consumer"},
            "queue2": {"tmux": "aiden:consumer"},
            "queue3": {"tmux": "scout:consumer"},
            "queue4": {"tmux": "elliottbot:other"},
            "queue5": {"tmux": "aiden:other"},
            "queue6": {"tmux": "max:consumer"},
            "queue7": {"tmux": "atlas:consumer"},
            "queue8": {"tmux": "orion:consumer"},
        }
        mock_relay.QUEUE_MAP = queue_map

        with patch.dict(
            "sys.modules", {"src.relay": MagicMock(), "src.relay.relay_consumer": mock_relay}
        ):
            passed, detail = p3.check4_consumer_dry_run()

            assert passed is True
            assert "live" in detail

    @patch("subprocess.run")
    def test_tmux_sessions_dead(self, mock_subprocess):
        """Should fail when required sessions (elliottbot, aiden) are dead."""
        # Mock subprocess to return failure for all sessions
        mock_subprocess.return_value = MagicMock(returncode=1)

        mock_relay = MagicMock()
        queue_map = {
            "queue1": {"tmux": "elliottbot:consumer"},
            "queue2": {"tmux": "aiden:consumer"},
            "queue3": {"tmux": "scout:consumer"},
            "queue4": {"tmux": "unknown:consumer"},
            "queue5": {"tmux": "unknown:other"},
            "queue6": {"tmux": "unknown:consumer"},
            "queue7": {"tmux": "unknown:consumer"},
            "queue8": {"tmux": "unknown:consumer"},
        }
        mock_relay.QUEUE_MAP = queue_map

        with patch.dict(
            "sys.modules", {"src.relay": MagicMock(), "src.relay.relay_consumer": mock_relay}
        ):
            passed, detail = p3.check4_consumer_dry_run()

            assert passed is False
            assert "dead" in detail or "0" in detail

    @patch("subprocess.run")
    def test_mixed_tmux_sessions(self, mock_subprocess):
        """Should handle mix of live and dead sessions."""

        # Mock: return code 0 for sessions that start with "elliot" or "aiden", 1 for others
        def side_effect_fn(cmd, **kwargs):
            session_name = cmd[
                3
            ]  # Get the session name from ["tmux", "has-session", "-t", session_name]
            if session_name in ("elliottbot", "aiden"):
                return MagicMock(returncode=0)
            return MagicMock(returncode=1)

        mock_subprocess.side_effect = side_effect_fn

        mock_relay = MagicMock()
        queue_map = {
            "queue1": {"tmux": "elliottbot:consumer"},
            "queue2": {"tmux": "aiden:consumer"},
            "queue3": {"tmux": "scout:consumer"},
            "queue4": {"tmux": "elliottbot:other"},
            "queue5": {"tmux": "aiden:other"},
            "queue6": {"tmux": "scout:other"},
            "queue7": {"tmux": "dead:consumer"},
            "queue8": {"tmux": "dead:other"},
        }
        mock_relay.QUEUE_MAP = queue_map

        with patch.dict(
            "sys.modules", {"src.relay": MagicMock(), "src.relay.relay_consumer": mock_relay}
        ):
            passed, detail = p3.check4_consumer_dry_run()

            assert passed is True
            assert "2/" in detail or "elliottbot" in detail


class TestCheck5SystemdUnit:
    """Test check5_systemd_unit: verify relay-consumer.service file."""

    def test_service_file_valid(self):
        """Should pass when service file exists with all sections and ExecStart."""
        service_content = """[Unit]
Description=Relay Consumer Service
After=network.target

[Service]
Type=simple
ExecStart=/home/elliotbot/clawd/Agency_OS/venv/bin/python3 scripts/relay_consumer.py
Restart=always
User=elliotbot

[Install]
WantedBy=multi-user.target
"""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=service_content),
        ):
            passed, detail = p3.check5_systemd_unit()

            assert passed is True
            assert "valid" in detail or "ExecStart" in detail

    def test_service_file_not_found(self):
        """Should fail when service file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            passed, detail = p3.check5_systemd_unit()

            assert passed is False
            assert "not found" in detail

    def test_missing_unit_section(self):
        """Should fail when [Unit] section is missing."""
        service_content = """[Service]
ExecStart=/path/to/script
Restart=always

[Install]
WantedBy=multi-user.target
"""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=service_content),
        ):
            passed, detail = p3.check5_systemd_unit()

            assert passed is False
            assert "missing sections" in detail

    def test_missing_service_section(self):
        """Should fail when [Service] section is missing."""
        service_content = """[Unit]
Description=Test Service

[Install]
WantedBy=multi-user.target
"""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=service_content),
        ):
            passed, detail = p3.check5_systemd_unit()

            assert passed is False
            assert "missing sections" in detail

    def test_missing_install_section(self):
        """Should fail when [Install] section is missing."""
        service_content = """[Unit]
Description=Test Service

[Service]
ExecStart=/path/to/script
"""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=service_content),
        ):
            passed, detail = p3.check5_systemd_unit()

            assert passed is False
            assert "missing sections" in detail

    def test_exec_start_not_found(self):
        """Should fail when ExecStart is missing from [Service]."""
        service_content = """[Unit]
Description=Test Service

[Service]
Type=simple
Restart=always

[Install]
WantedBy=multi-user.target
"""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=service_content),
        ):
            passed, detail = p3.check5_systemd_unit()

            assert passed is False
            assert "ExecStart not found" in detail

    def test_exec_start_path_missing(self):
        """Should fail when ExecStart points to non-existent file."""
        # The script parses ExecStart and gets [1] index, so must have 2+ tokens
        service_content = """[Unit]
Description=Test Service

[Service]
ExecStart=/usr/bin/python3 /nonexistent/path/to/script
Restart=always

[Install]
WantedBy=multi-user.target
"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create infra/relay subdirectories
            infra_relay = Path(tmpdir) / "infra" / "relay"
            infra_relay.mkdir(parents=True)

            service_path = infra_relay / "relay-consumer.service"
            service_path.write_text(service_content)

            # Patch REPO_ROOT to point to tmpdir
            with patch.object(p3, "REPO_ROOT", Path(tmpdir)):
                passed, detail = p3.check5_systemd_unit()

                assert passed is False
                assert "missing" in detail or "ExecStart path" in detail


class TestLoadEnv:
    """Test _load_env helper function."""

    def test_load_env_file_exists(self):
        """Should load and parse env file correctly."""
        env_content = """KEY1=value1
KEY2="quoted value"
# This is a comment
KEY3='single quoted'
"""
        with (
            patch.object(Path, "read_text", return_value=env_content),
            patch("os.path.exists", return_value=True),
        ):
            # Save current env and restore after test
            saved_env = dict(os.environ)
            try:
                p3._load_env("/fake/path/.env")
                assert os.environ.get("KEY1") == "value1"
                assert os.environ.get("KEY2") == "quoted value"
                assert os.environ.get("KEY3") == "single quoted"
            finally:
                os.environ.clear()
                os.environ.update(saved_env)

    def test_load_env_file_not_exists(self):
        """Should gracefully handle missing env file."""
        with patch("os.path.exists", return_value=False):
            # Should not raise exception
            p3._load_env("/fake/path/.env")


class TestIntegration:
    """Integration tests for full check flow."""

    @patch("scripts.phase3_readiness_check._get_redis")
    @patch("subprocess.run")
    @patch.dict(os.environ, {"INBOX_HMAC_SECRET": "test-secret"})
    def test_all_checks_pass(self, mock_subprocess, mock_get_redis):
        """Should pass all checks when environment is ready."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Setup redis mocks
        mock_redis.exists.side_effect = [1] * 8
        mock_redis.llen.side_effect = [5, 3, 0, 1, 2, 4, 1, 2]
        mock_redis.type.return_value = "list"

        # Setup HMAC
        import hashlib
        import hmac as hmac_mod

        secret = "test-secret"
        payload = {
            "type": "readiness_check",
            "from": "phase3_checker",
            "brief": "test",
            "created_at": int(time.time()),
        }
        filtered = {k: v for k, v in payload.items() if k != "hmac"}
        canonical = json.dumps(filtered, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected_hmac = hmac_mod.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
        signed = {**payload, "hmac": expected_hmac}

        mock_redis.brpop.return_value = ("queue", json.dumps(signed))

        # Setup tmux
        mock_subprocess.return_value = MagicMock(returncode=0)

        mock_relay = MagicMock()
        queue_map = {f"q{i}": {"tmux": "elliottbot:c" if i < 4 else "aiden:c"} for i in range(8)}
        mock_relay.QUEUE_MAP = queue_map

        mock_security = MagicMock()
        mock_inbox_hmac = MagicMock()
        mock_inbox_hmac.sign = MagicMock(return_value=signed)

        service_content = """[Unit]
Description=Test

[Service]
ExecStart=/usr/bin/python3 /home/elliotbot/clawd/Agency_OS/scripts/relay_consumer.py

[Install]
WantedBy=multi-user.target
"""
        with (
            patch.dict(
                "sys.modules",
                {
                    "src.relay": MagicMock(),
                    "src.relay.relay_consumer": mock_relay,
                    "src.security": mock_security,
                    "src.security.inbox_hmac": mock_inbox_hmac,
                },
            ),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=service_content),
        ):
            # Check1
            p1 = p3.check1_queue_keys()
            assert p1[0] is True

            # Check2
            p2 = p3.check2_dual_write(p1[2])
            assert p2[0] is True

            # Check3
            p3_result = p3.check3_hmac_roundtrip()
            assert p3_result[0] is True

            # Check4
            p4 = p3.check4_consumer_dry_run()
            assert p4[0] is True

            # Check5
            p5 = p3.check5_systemd_unit()
            assert p5[0] is True
