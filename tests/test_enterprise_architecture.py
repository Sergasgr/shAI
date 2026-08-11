import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from typer.testing import CliRunner
from shai.cli import t as app
from shai.core.telemetry import log_cloud_telemetry

runner = CliRunner()

@patch("shai.core.telemetry.httpx.post")
def test_cloud_telemetry_payload_structure(mock_post):
    prompt = "list files"
    command = "ls -la"
    os_context = "Linux"
    exit_code = 0
    llm_latency = 0.45
    tps = 45.2
    
    log_cloud_telemetry(prompt, command, os_context, exit_code, llm_latency, tps)
    
    assert mock_post.called, "Cloud telemetry POST request was not triggered."
    
    call_args, call_kwargs = mock_post.call_args
    payload = call_kwargs.get("json", {})
    
    assert payload.get("llm_latency") == llm_latency, "Latency metric missing from telemetry payload."
    assert payload.get("tokens_per_second") == tps, "TPS metric missing from telemetry payload."
    assert payload.get("exit_code") == exit_code, "Exit code missing from telemetry payload."

@patch("shai.cli.get_command")
@patch("shai.cli.check_cache")
def test_semantic_cache_hit_bypasses_llm(mock_check_cache, mock_get_command):
    mock_check_cache.return_value = "ls -la"
    result = runner.invoke(app, ["ask", "list files", "-y"])
    assert "ls -la" in result.stdout
    assert not mock_get_command.called, "Semantic Cache failed: the LLM was woken up despite a cache hit."

@patch("shai.core.rag_engine.EnsembleRetriever")
@patch("shai.core.rag_engine.get_vector_store")
@patch("shai.core.rag_engine.CHUNKS_FILE")
@patch("shai.core.rag_engine.pickle.load")
@patch("shai.core.rag_engine.BM25Retriever.from_documents")
def test_hybrid_search_initialization(mock_bm25, mock_pickle, mock_chunks_file, mock_get_store, mock_ensemble):
    mock_chunks_file.exists.return_value = True
    mock_get_store.return_value = MagicMock()
    mock_pickle.return_value = ["dummy_chunk"]
    from shai.core.rag_engine import search_knowledge 
    search_knowledge("test query")
    mock_ensemble.assert_called()
    kwargs = mock_ensemble.call_args.kwargs
    assert "retrievers" in kwargs, "Hybrid search must pass multiple retrievers to the Ensemble."
    assert "weights" in kwargs, "Hybrid search must balance retrievers with weights."
    
@patch("shai.core.dashboard.ShaiDashboard.run")
def test_dashboard_tui_invocation(mock_tui_run):
    result = runner.invoke(app, ["dashboard"])
    
    assert mock_tui_run.called, "The Textual TUI application was not invoked by the CLI."
    assert result.exit_code == 0

@patch("shai.cli.run_static_analysis")
def test_ci_review_github_action(mock_static_analysis):
    mock_static_analysis.return_value = False
    
    with runner.isolated_filesystem():
        with open("dummy_script.sh", "w") as f:
            f.write("echo 'Hello World'")
            
        result = runner.invoke(app, ["ci-review", "dummy_script.sh"])
        
        assert result.exit_code == 1, "CI Action failed to halt the pipeline when vulnerabilities were found."

def test_iac_terraform_manifest_presence():
    tf_file = Path("infrastructure/main.tf") 
    if Path("infrastructure").exists():
        assert tf_file.exists(), "Terraform manifest (main.tf) is missing for Ephemeral GPU deployment."