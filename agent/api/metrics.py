"""
Prometheus metrics API endpoint for Marvin Memory Service.
Serves metrics in Prometheus text exposition format.
"""

from fastapi import APIRouter
from starlette.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from ..memory import count_memories
from ..metrics import registry, marvin_memories_total

router = APIRouter(tags=["Metrics"])


@router.get("/metrics")
def metrics_endpoint():
    """
    Serve Prometheus metrics in text exposition format.
    
    Updates memory count gauge and returns all metrics.
    """
    # Update gauge right before scrape
    marvin_memories_total.set(count_memories())
    
    # Generate metrics in Prometheus text format
    data = generate_latest(registry)
    
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)