import pytest
from pathlib import Path
import typer
from unittest.mock import patch, MagicMock
from shai.ai.engine import check_forbidden
from shai.core.env_detector import alias_configuration  
from shai.core.telemetry import init_db
from shai.core.rag_engine import get_vector_store

def test_xdg_base_directory_creation(monkeypatch, tmp_path):
    temp_dir = tmp_path / ".local" / "share" / "shai"
    db_file = temp_dir / "feedback.db"
    monkeypatch.setattr("shai.core.telemetry.DB_FILE", db_file)
    init_db()
    
    assert temp_dir.exists(), f"The XDG directory at {temp_dir} was not created."

@pytest.mark.parametrize("safe_cmd", [
    "ls -la",
    "echo 'rm -rf is dangerous'",
    "cat file.txt",
    "git status",
    "python3 script.py"
])
def test_check_forbidden_safe_commands(safe_cmd):
    assert check_forbidden(safe_cmd) is False, f"False positive: The safe command '{safe_cmd}' was blocked."

@pytest.mark.parametrize("dangerous_cmd", [
    "rm -rf /",
    "mkfs.ext4 /dev/sda1",
    "chmod 777 /etc",
    "dd if=/dev/zero of=/dev/sda",
    "fdisk /dev/sdb"
])
def test_check_forbidden_dangerous_commands(dangerous_cmd):
    assert check_forbidden(dangerous_cmd) is True, f"Security failure: The destructive command '{dangerous_cmd}' was not detected."

@pytest.mark.parametrize("shell_name, expected_suffix", [
    ("bash", ".bashrc"),
    ("zsh", ".zshrc"),
    ("fish", ".config/fish/config.fish")
])
def test_alias_configuration_valid_shells(shell_name, expected_suffix):
    path_result = alias_configuration(shell_name)
    assert isinstance(path_result, Path), "The function must return a pathlib Path object."
    assert path_result.as_posix().endswith(expected_suffix), f"The path for {shell_name} does not point to the expected file."

@pytest.mark.parametrize("invalid_shell", ["csh", "cmd", "powershell", "unknown"])
def test_alias_configuration_invalid_shells(invalid_shell):
    with pytest.raises(typer.Exit) as exc_info:
        alias_configuration(invalid_shell)
    assert exc_info.value.exit_code == 1

def test_rag_singleton_pattern():
    with patch("shai.core.rag_engine.OllamaEmbeddings"), \
         patch("shai.core.rag_engine.Chroma") as mock_chroma:
        mock_chroma.side_effect = lambda *args, **kwargs: MagicMock()
        instance_1 = get_vector_store()
        instance_2 = get_vector_store()
        assert instance_1 is instance_2, "The Singleton pattern failed: multiple ChromaDB instances were created."
        import shai.core.rag_engine
        shai.core.rag_engine.vector_store_instance = None
        instance_3 = get_vector_store()
        assert instance_1 is not instance_3, "Cache invalidation failed: the in-memory instance was not replaced."