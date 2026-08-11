import pytest
from unittest.mock import patch, MagicMock
import typer
import httpx
from shai.ai.ollama_client import get_command, check_llm, send_ollama_request

@patch("shai.ai.ollama_client.httpx.get")
def test_check_llm_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    assert check_llm() is True

@patch("shai.ai.ollama_client.httpx.get")
def test_check_llm_failure(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response
    
    assert check_llm() is False

@patch("shai.ai.ollama_client.httpx.post")
def test_network_failure_handling(mock_post):
    mock_post.side_effect = httpx.ConnectError("Connection refused")
    with pytest.raises(typer.Exit) as exc_info:
        send_ollama_request("http://localhost:11434/api/chat", {"test": "data"})  
        
    assert exc_info.value.exit_code == 1

@patch("shai.ai.ollama_client.send_ollama_request")
@patch("shai.ai.ollama_client.search_knowledge")
def test_get_command_metrics(mock_search, mock_post):
    mock_search.return_value = "" 
    mock_post.return_value = {
        "message": {"content": "```bash\nls -la\n```"},
        "total_duration": 1500000000,
        "eval_duration": 1000000000, 
        "eval_count": 50              
    }
    context = {"os": "Linux", "shell": "bash", "language": "en"}
    command, latency, tps = get_command("list files", context)
    
    assert command == "ls -la"
    assert latency == 1.5
    assert tps == 50.0