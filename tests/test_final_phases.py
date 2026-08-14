import sqlite3
import subprocess
import threading
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from shai.cli import t as app
from shai.core.download_llama_cpp import fetch_llama_cpp
from shai.core.telemetry import init_db, log_execution
from shai.core.orchestrator import AgentOrchestrator
from shai.ai.engine import run_static_analysis, build_sandbox_command

runner = CliRunner()

@patch("shai.core.download_llama_cpp.httpx.get")
@patch("platform.machine")
@patch("platform.system")
def test_dynamic_binary_download_architecture(mock_system, mock_machine, mock_get):
    response_json = MagicMock()
    response_json.status_code = 200
    response_json.json.return_value = {
        "assets": [
            {"name": "llama-ubuntu-x64.tar.gz", "browser_download_url": "http://fake.com/ubuntu-x64"},
            {"name": "llama-ubuntu-aarch64.tar.gz", "browser_download_url": "http://fake.com/ubuntu-aarch64"}
        ]
    }
    response_bin = MagicMock()
    response_bin.status_code = 200
    response_bin.content = b"fake_zip_content"
    
    mock_get.side_effect = [response_json, response_bin, response_json, response_bin]
    
    mock_system.return_value = "Linux"
    mock_machine.return_value = "x86_64"
    fetch_llama_cpp() 
    called_url = mock_get.call_args_list[1][0][0] 
    assert "ubuntu-x64" in called_url, f"Failed to route Linux x64 architecture. URL used: {called_url}"
    
    mock_system.return_value = "Linux" 
    mock_machine.return_value = "aarch64"
    fetch_llama_cpp()
    
    called_url_arm = mock_get.call_args_list[3][0][0]
    assert "aarch64" in called_url_arm, f"Failed to route ARM architecture. URL used: {called_url_arm}"

def test_telemetry_cyclic_retention(monkeypatch, tmp_path):
    temp_db = tmp_path / "test_feedback.db"
    monkeypatch.setattr("shai.core.telemetry.DB_FILE", temp_db)
    
    original_start = threading.Thread.start
    def sync_start(self):
        self._target(*self._args, **self._kwargs)
    monkeypatch.setattr(threading.Thread, "start", sync_start)

    init_db()
    for i in range(505):
        log_execution(f"prompt_{i}", "ls", "test", "Linux", 0)
        
    con = sqlite3.connect(str(temp_db))
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM executions;")
    count = cur.fetchone()[0]
    con.close()
    
    assert count <= 500, f"Privacy policy violation: Database retained {count} records, exceeding the 500 limit."

def test_privacy_manifest_transparency():
    result = runner.invoke(app, ["privacy"])
    assert result.exit_code == 0
    output = result.stdout.lower()
    assert "privacy" in output, "The privacy manifest is missing the word 'Privacy'."
    assert "local" in output, "The privacy manifest must state that data remains 'local'."
    assert "clean" in output, "The privacy manifest must instruct the user about the 'clean' command for data deletion."

@patch.object(AgentOrchestrator, "fix_command")
@patch("shai.core.orchestrator.subprocess.run")
def test_agent_auto_healing_loop(mock_subprocess_run, mock_fix_command):
    orchestrator = AgentOrchestrator(sys_context={"os": "Linux"}, max_retries=3)
    error_mock = subprocess.CalledProcessError(returncode=1, cmd="ls /root", stderr="Permission denied")
    success_mock = MagicMock(stdout="root_files\n")
    mock_subprocess_run.side_effect = [error_mock, success_mock]
    mock_fix_command.return_value = "ls -la /root"
    
    success = orchestrator.execute_with_healing("List root", "ls /root")
    
    assert success is True, "The Auto-Healing loop failed to recover from the error."
    assert mock_subprocess_run.call_count == 2, "subprocess.run should have been called exactly twice (1 failure + 1 healing attempt)."
    mock_fix_command.assert_called_once()

@patch("shai.ai.engine.subprocess.run")
def test_static_analysis_shellcheck(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="SC2086: Double quote to prevent globbing.")
    
    is_safe = run_static_analysis("echo $1")
    assert is_safe is False, "Static analysis failed to block syntactically vulnerable bash code."

def test_sandbox_docker_isolation():
    dangerous_payload = "rm -rf /"
    sandboxed_cmd_list = build_sandbox_command(dangerous_payload)
    assert sandboxed_cmd_list[0] == "docker"
    assert sandboxed_cmd_list[1] == "run"
    assert "ubuntu" in sandboxed_cmd_list, "The sandbox is missing the isolated OS image."
    assert dangerous_payload in sandboxed_cmd_list, "The original command was lost during sandbox wrapping."