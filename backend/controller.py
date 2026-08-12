from fastapi import FastAPI, Response, Depends
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uvicorn
from schemas import TelemetryPayload
from metrics import EXECUTION_COUNTER, LATENCY_HISTOGRAM, TOKENS_HISTOGRAM
from security import get_api_key

app = FastAPI(title="shAI Telemetry API")

@app.post("/api/v1/telemetry")
def receive_telemetry(data: TelemetryPayload, api_key: str = Depends(get_api_key)):
    status = "success" if data.exit_code == 0 else "failure"
    EXECUTION_COUNTER.labels(status=status).inc()

    if data.llm_latency > 0:
        LATENCY_HISTOGRAM.observe(data.llm_latency)
    if data.tokens_per_second > 0:
        TOKENS_HISTOGRAM.observe(data.tokens_per_second)
        
    return {"status": "ok", "message": "Telemetry correctly ingested"}

@app.get("/metrics")
def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")