"""Tests for cli module."""

from pathlib import Path
from unittest.mock import patch

from server_audit.cli import SSH_PASSWORD_PROMPT, main


class TestAskPass:
    """Tests for the -k/--ask-pass option."""

    @patch("server_audit.cli.run_audit_to_json", return_value=[])
    @patch("server_audit.cli.getpass.getpass", return_value="secret")
    def test_ask_pass_prompts_and_answers_ansible(
        self, mock_getpass, mock_run, sample_inventory: Path, tmp_path: Path
    ):
        """-k asks once and passes the password to Ansible's SSH password prompt."""
        exit_code = main(["-i", str(sample_inventory), "-o", str(tmp_path / "out"), "-k"])

        assert exit_code == 0
        mock_getpass.assert_called_once()
        kwargs = mock_run.call_args.kwargs
        assert kwargs["cmdline"] == "-k"
        assert kwargs["passwords"] == {SSH_PASSWORD_PROMPT: "secret"}

    @patch("server_audit.cli.run_audit_to_json", return_value=[])
    @patch("server_audit.cli.getpass.getpass")
    def test_without_ask_pass_nothing_is_asked(
        self, mock_getpass, mock_run, sample_inventory: Path, tmp_path: Path
    ):
        """Without -k there is no prompt and no password reaches Ansible."""
        exit_code = main(["-i", str(sample_inventory), "-o", str(tmp_path / "out")])

        assert exit_code == 0
        mock_getpass.assert_not_called()
        kwargs = mock_run.call_args.kwargs
        assert kwargs["cmdline"] is None
        assert kwargs["passwords"] is None

    def test_prompt_pattern_matches_ansible_prompt(self):
        """The pattern answers the prompt ansible -k prints."""
        import re

        assert re.search(SSH_PASSWORD_PROMPT, "SSH password: ")
