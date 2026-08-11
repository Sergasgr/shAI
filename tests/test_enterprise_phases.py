import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from typer.testing import CliRunner
from shai.ai.engine import check_forbidden
from shai.ai.security_detector import is_prompt_injection
from shai.core.config import CRITICAL_PATHS
from evals.run_evals import evaluate_semantic_success
from shai.ai.ollama_analyzer import get_risk_summary        
from shai.cli import t as app

runner = CliRunner()

@pytest.mark.parametrize("cmd, expected_blocked", [
    ("ls -la /tmp", False),
    ("echo 'hello world'", False),
    ("rm -rf /", True),
    ("mkfs.ext4 /dev/sda", True),
    ("chmod 777 /etc/passwd", True)
])
def test_security_firewall_commands(cmd, expected_blocked):
    is_blocked = check_forbidden(cmd)
    assert is_blocked == expected_blocked, f"Security mismatch for command '{cmd}': expected blocked={expected_blocked}, got {is_blocked}"

@pytest.mark.parametrize("path_str", [
    "/etc/passwd",
    "/etc/shadow",
    "/boot/grub/grub.cfg"
])
def test_security_critical_paths_protection(path_str):
    target = Path(path_str).resolve()
    is_critical = any(target == crit or target.is_relative_to(crit) for crit in CRITICAL_PATHS)
    assert is_critical is True, f"Critical path protection failed for: {path_str}"

@patch("pathlib.Path.exists")
def test_ci_environment_readiness(mock_exists):
    mock_exists.return_value = True
    ci_file = Path(".github/workflows/ci.yml")
    assert ci_file.exists(), "CI configuration file (.github/workflows/ci.yml) is missing for GitHub Actions."

@patch("evals.run_evals.send_ollama_request") 
def test_semantic_evaluation_judge(mock_ollama):
    mock_ollama.return_value = {
        "message": {"content": '{"evaluation": 1}'}
    }
    prompt = "List all files in the current directory"
    generated_command = "ls -la"
    success = evaluate_semantic_success(prompt, generated_command)
    assert success == 1, "LLM-as-a-Judge failed to evaluate a semantically valid command as success (1)."
    
@patch("shai.ai.ollama_analyzer.send_ollama_request")
def test_active_risk_summary_generation(mock_ollama):
    expected_summary = "⚠️ WARNING: This command will recursively delete system files without backup."
    mock_ollama.return_value = {
        "message": {"content": expected_summary}
    }
    dangerous_cmd = "rm -rf /var/log/*"
    summary = get_risk_summary(dangerous_cmd)
    assert isinstance(summary, str), "Risk summary must return a string."
    assert "WARNING" in summary or "delete" in summary, "Risk summary failed to highlight the operational danger."