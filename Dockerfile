# Dockerfile for ChemCloud Web Server
FROM python:3.13-slim
# https://github.com/awslabs/amazon-sagemaker-examples/issues/319
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    UV_PROJECT_ENVIRONMENT=/usr/local
LABEL maintainer="Colton Hicks <colton@coltonhicks.com>"

# Install system packages
RUN apt-get update && \
    python -m pip install --upgrade pip uv

# Install application
WORKDIR /opt/
COPY pyproject.toml uv.lock README.md ./
COPY static ./static
COPY chemcloud_server/ ./chemcloud_server
RUN uv sync --frozen --no-dev

EXPOSE 8000

# https://docs.gunicorn.org/en/stable/design.html#how-many-workers
# Timeout to 60s for larger results that require more time to collect from redis
CMD ["sh", "-c", "gunicorn chemcloud_server.main:app -w 2 -k uvicorn.workers.UvicornWorker --keep-alive 650 --timeout 60 -b 0.0.0.0:8000 --access-logfile -"]
