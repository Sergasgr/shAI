from fastapi import FastAPI, Response
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import uvicorn

class TelemetryPayload(BaseModel):
    prompt: str
    command: str
    exit_code: int
    os_context: str
    llm_latency: float
    tokens_per_second: float

app = FastAPI(title="shAI Telemetry API")

EXECUTION_COUNTER = Counter(
    "shai_command_executions_total",
    "Total number of command executions",
    ["status"]
)
LATENCY_HISTOGRAM = Histogram(
    "llm_latency_seconds",
    "Latency of LLM in seconds"
)
TOKENS_HISTOGRAM = Histogram(
    "llm_tokens_per_second",
    "LLM generation speed in tokens per second"
)

@app.post("/api/v1/telemetry")
async def receive_telemetry(data: TelemetryPayload):
    status = "success" if data.exit_code == 0 else "failure"
    EXECUTION_COUNTER.labels(status=status).inc()

    if data.llm_latency > 0:
        LATENCY_HISTOGRAM.observe(data.llm_latency)
    if data.tokens_per_second > 0:
        TOKENS_HISTOGRAM.observe(data.tokens_per_second)
        
    return {"status": "ok", "message": "Telemetry correctly ingested"} #await

@app.get("/metrics")
async def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST) #await

if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")