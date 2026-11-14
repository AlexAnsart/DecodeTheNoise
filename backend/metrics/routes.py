"""The measured reliability of every detector the product shows."""

from fastapi import APIRouter, Request

from backend.metrics.schema import DetectorMetrics, MetricsResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def get_metrics(request: Request) -> dict[str, DetectorMetrics]:
    return request.app.state.metrics


@router.get("")
def metrics(request: Request) -> MetricsResponse:
    return MetricsResponse(detectors=list(get_metrics(request).values()))
