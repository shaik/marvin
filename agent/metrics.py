"""
Prometheus metrics for Marvin Memory Service.
Provides HTTP request counting and memory statistics.
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Create isolated registry to avoid duplicate registration across test re-imports
registry = CollectorRegistry()

# Define metrics with isolated registry
http_requests_total = Counter(
    "http_requests_total", 
    "Total HTTP requests", 
    registry=registry
)

marvin_memories_total = Gauge(
    "marvin_memories_total", 
    "Total stored memories", 
    registry=registry
)


def register_http_metrics(app):
    """
    Register HTTP request counting middleware with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    @app.middleware("http")
    async def _count_requests(request, call_next):
        # Increment counter before processing request
        http_requests_total.inc()
        response = await call_next(request)
        return response