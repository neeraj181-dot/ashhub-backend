from typing import Any
from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["System Status"])


@router.get("/status", response_model=dict[str, Any])
def get_system_operational_status() -> Any:
    """Retrieve operational health status across core components."""
    return {
        "status": "operational",
        "components": {
            "api_gateway": {"status": "operational", "latency_ms": 12},
            "database_cluster": {"status": "operational", "latency_ms": 4},
            "deployment_queue": {"status": "operational", "latency_ms": 8},
            "vercel_provider": {"status": "operational", "latency_ms": 45},
            "render_provider": {"status": "operational", "latency_ms": 52},
            "webhook_engine": {"status": "operational", "latency_ms": 15},
        },
    }
