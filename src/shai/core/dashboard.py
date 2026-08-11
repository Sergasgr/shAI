import sqlite3
from textual.app import App, ComposeResult
from textual.widgets import TabbedContent, TabPane, DataTable, Button, Label, Footer, Header
from textual.containers import Vertical, Center
from shai.core.telemetry import DB_FILE 
from shai.core.rag_engine import rm_chromadb, DB_DIR

class ShaiDashboard(App):
    TITLE = "shAI Dashboard"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Theme")
    ]
    
    CSS = """
    Screen {
        layout: vertical;
    }
    #rag-container, #metrics-container {
        padding: 2 4;
        height: 100%;
        align: center middle;
    }
    .metric-label {
        text-align: center;
        padding: 1;
        text-style: bold;
    }
    #btn-clear-rag {
        margin-top: 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        
        with TabbedContent():
            with TabPane("History", id="tab-history"):
                yield DataTable(id="history-table")
                
            with TabPane("RAG Manager", id="tab-rag"):
                with Vertical(id="rag-container"):
                    yield Label("Loading status...", id="rag-status", classes="metric-label")
                    with Center():
                        yield Button("Clear RAG Memory", id="btn-clear-rag", variant="error")
                        
            with TabPane("Metrics", id="tab-metrics"):
                with Vertical(id="metrics-container"):
                    yield Label(id="metric-total", classes="metric-label")
                    yield Label(id="metric-success", classes="metric-label")
                    yield Label(id="metric-failed", classes="metric-label")
                    
        yield Footer()

    def on_mount(self) -> None:
        self.load_history()
        self.update_rag_status()
        self.load_metrics()

    def load_history(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        table.add_columns("ID", "Prompt", "Command", "Exit Code")
        
        if DB_FILE.exists(): 
            try:
                con = sqlite3.connect(str(DB_FILE)) 
                cur = con.cursor()
                cur.execute("SELECT id, prompt, command, exit_code FROM executions ORDER BY id DESC LIMIT 50")
                rows = cur.fetchall()
                
                for row in rows:
                    table.add_row(*[str(item) for item in row])
                    
            except Exception as e:
                table.add_row("Error", f"Failed to read DB: {e}", "", "")
            finally:
                con.close()
        else:
            table.add_row("-", "Database is empty or missing.", "-", "-")

    def update_rag_status(self) -> None:
        status_label = self.query_one("#rag-status", Label)
        
        if DB_DIR.exists() and any(DB_DIR.iterdir()):
            status_label.update("🧠 RAG Status: **Memory Active**")
        else:
            status_label.update("⚪ RAG Status: **Memory Empty**")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear-rag":
            try:
                rm_chromadb()
                self.update_rag_status()
                self.notify("The RAG vector memory has been successfully cleared.", title="Success")
            except Exception as e:
                self.notify(f"Could not clear database: {e}", title="Error", severity="error")

    def load_metrics(self) -> None:
        total_label = self.query_one("#metric-total", Label)
        success_label = self.query_one("#metric-success", Label)
        failed_label = self.query_one("#metric-failed", Label)
        
        if DB_FILE.exists(): 
            try:
                con = sqlite3.connect(str(DB_FILE))
                cur = con.cursor() 
                
                cur.execute("SELECT COUNT(*) FROM executions")
                total = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM executions WHERE exit_code = 0")
                success = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM executions WHERE exit_code != 0")
                failed = cur.fetchone()[0]
                
                total_label.update(f"📊 Total executed commands: **{total}**")
                success_label.update(f"✅ Successful commands: **{success}**")
                failed_label.update(f"❌ Failed commands: **{failed}**")
                
            except Exception as e:
                total_label.update(f"Error loading metrics: {e}")
                success_label.update("")
                failed_label.update("")
            finally:
                con.close() 
        else:
            total_label.update("No telemetry data available yet.")
            success_label.update("")
            failed_label.update("")

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

if __name__ == "__main__":
    app = ShaiDashboard()
    app.run()