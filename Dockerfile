# CloudOps Harness application image (optional: dev can run directly on the host).
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY skills ./skills
COPY fixtures ./fixtures
COPY static ./static

RUN pip install --no-cache-dir .

EXPOSE 8090
CMD ["uvicorn", "cloudops_harness.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8090"]
