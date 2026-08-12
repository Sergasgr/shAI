from pydantic import BaseModel

class TelemetryPayload(BaseModel):
    prompt: str
    command: str
    exit_code: int
    os_context: str
    llm_latency: float
    tokens_per_second: float