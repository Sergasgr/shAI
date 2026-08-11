import httpx
from pathlib import Path
import sqlite3
import threading
from shai.core.config import CLOUD_API_URL

DB_PATH = Path.home() / ".local" / "share" / "shai"
DB_FILE = DB_PATH / "feedback.db"
DB_PATH.mkdir(parents=True, exist_ok=True)

def init_db():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_FILE))
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        prompt TEXT, 
        command TEXT,
        explanation TEXT, 
        os_context TEXT, 
        exit_code INTEGER);
    """)
    con.commit()
    con.close() 
    
def rm_db():
    con = sqlite3.connect(str(DB_FILE))
    cur = con.cursor()
    cur.execute("DELETE FROM executions;")
    cur.execute("VACUUM;")
    con.commit()
    con.close()

def log_execution(prompt: str, command: str, explanation: str, os_context: str, exit_code: int):
    def run_sqlite():
        try:
            con = sqlite3.connect(str(DB_FILE))
            cur = con.cursor()
            cur.execute(
                "INSERT INTO executions (prompt, command, explanation, os_context, exit_code) VALUES (?, ?, ?, ?, ?)", 
                (prompt, command, explanation, os_context, exit_code)
            )
            cur.execute(
                "DELETE FROM executions WHERE id NOT IN (SELECT id FROM executions ORDER BY id DESC LIMIT 500);"
            )
            con.commit()
        except Exception:
            pass 
        finally:
            if 'con' in locals():
                con.close()
            
    thread = threading.Thread(target=run_sqlite, daemon=True)
    thread.start()

def log_cloud_telemetry(prompt: str, command: str, os_context: str, exit_code: int, llm_latency: float, tokens_per_second: float):
    def send_to_cloud():
        payload = {
            "prompt": prompt,
            "command": command,
            "exit_code": exit_code,
            "os_context": os_context,
            "llm_latency": llm_latency,
            "tokens_per_second": tokens_per_second
        }
        try:
            httpx.post(CLOUD_API_URL, json=payload, timeout=1.0)
        except Exception:
            pass 
            
    thread = threading.Thread(target=send_to_cloud, daemon=True)
    thread.start()