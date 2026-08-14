import sys
from pathlib import Path
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from typer.testing import CliRunner
from controller import app
from shai.cli import t
from shai.ai.security_detector import SecurityEngine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

runner = CliRunner()
client = TestClient(app)

def test_telemetry_api_key_auth():
    payload = {
        "prompt": "ls", "command": "ls", "exit_code": 0, 
        "os_context": "Linux", "llm_latency": 1.0, "tokens_per_second": 10.0
    }
    response_unauth = client.post("/api/v1/telemetry", json=payload)
    assert response_unauth.status_code in (403, 422), "Vulnerability: Telemetry endpoint accepted unauthenticated request."
    
    response_wrong = client.post("/api/v1/telemetry", json=payload, headers={"X-API-Key": "fake-key"})
    assert response_wrong.status_code == 403, "Vulnerability: Telemetry endpoint accepted invalid API Key."

def test_agent_mutual_exclusion():
    result = runner.invoke(t, ["ask", "update system", "--agent", "--bash"])
    
    assert result.exit_code == 1, "CLI allowed mutually exclusive flags to run together."
    assert "mutually exclusive" in result.stdout.lower(), "CLI did not print the correct warning message for flag collision."

@patch("shai.ai.security_detector.AutoModelForSequenceClassification.from_pretrained")
def test_security_engine_oom_handling(mock_from_pretrained): 
    SecurityEngine.instance = None
    
    mock_from_pretrained.side_effect = MemoryError("CUDA out of memory")
    
    engine = SecurityEngine()

    with pytest.raises(SystemExit) as exc_info:
        engine.load()
        
    assert exc_info.value.code == 1, "Security Engine did not exit cleanly upon Out Of Memory error."