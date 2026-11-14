# The API image: runtime dependencies only. The pipeline group (datasets, training) stays out;
# the layout library is a runtime dependency, since a workspace is laid out on the server.
# Official images come from Google's mirror of Docker Hub, which rate-limits the shared runners.
FROM mirror.gcr.io/library/python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY backend ./backend
# Shared with the offline jobs: clustering, zone words and names, the buffer packing.
COPY pipelines ./pipelines
# The probe pack and the evaluation reports behind it: weights and measures, no text.
COPY probes ./probes
COPY reports ./reports

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
