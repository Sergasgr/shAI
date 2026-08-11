import httpx
import platform
import tarfile
import os
import io
from pathlib import Path

def fetch_llama_cpp() -> tuple[bool, str]:
    if platform.system().lower() != "linux":
        return False, "Automated download is strictly supported on Linux environments."

    machine = platform.machine().lower()
    arch = "x64" if machine in ["x86_64", "amd64"] else ("aarch64" if machine in ["aarch64", "arm64"] else None)
    
    if not arch:
        return False, f"Unsupported architecture: {machine}"

    api_url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
    
    try:
        resp = httpx.get(api_url, timeout=10.0)
        resp.raise_for_status()
        
        download_url = next(
            (asset["browser_download_url"] for asset in resp.json().get("assets", []) 
             if "ubuntu" in asset["name"].lower() and arch in asset["name"].lower() and asset["name"].endswith(".tar.gz")), 
            None
        )
        
        if not download_url:
            return False, "Compatible precompiled binary not found for your system architecture."
        
        asset_resp = httpx.get(download_url, follow_redirects=True, timeout=60.0)
        asset_resp.raise_for_status()

        target_dir = Path(__file__).parent / "llama_cpp_bin"
        target_dir.mkdir(exist_ok=True)

        with tarfile.open(fileobj=io.BytesIO(asset_resp.content), mode="r:gz") as tar:
            tar.extractall(path=target_dir)

        for file in target_dir.iterdir():
            if file.is_file():
                os.chmod(file, 0o755)

        return True, str(target_dir)

    except Exception as e:
        return False, f"Network or extraction error: {e}"

if __name__ == "__main__":
    success, msg = fetch_llama_cpp()
    if success:
        print(f"✓ Binaries successfully installed at: {msg}")
    else:
        print(f"✗ Failed to download binaries: {msg}")