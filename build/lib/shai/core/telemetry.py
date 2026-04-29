import sqlite3
import os

db_dir = os.path.expanduser("~/shai/data/")
db_path = os.path.join(db_dir, "feedback.db")
os.makedirs(db_dir, exist_ok=True)

def init_db():
    con = sqlite3.connect(db_path)
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

def log_execution(prompt:str, command:str, explanation:str, os_context:str, exit_code:int):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO executions (prompt, command, explanation, os_context, exit_code) VALUES (?, ?, ?, ?, ?)", 
        (prompt, command, explanation, os_context, exit_code)
    )
    con.commit()
    con.close()