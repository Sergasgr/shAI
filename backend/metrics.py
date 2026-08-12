from prometheus_client import Counter, Histogram

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