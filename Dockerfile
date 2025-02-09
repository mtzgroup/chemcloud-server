# Dockerfile for ChemCloud Web Server
FROM python:3.13-slim
# https://github.com/awslabs/amazon-sagemaker-examples/issues/319
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # Install to system python, no need for venv
    POETRY_VIRTUALENVS_CREATE=false
LABEL maintainer="Colton Hicks <colton@coltonhicks.com>"

# Install system packages
RUN apt-get update && \
    python -m pip install --upgrade pip poetry

# Install application
WORKDIR /opt/
COPY pyproject.toml poetry.lock README.md ./
COPY static ./static
COPY chemcloud_server/ ./chemcloud_server
# Install to system python, no need for pipenv virtual env
RUN poetry install --only main --no-interaction --no-ansi

EXPOSE 8000

# https://docs.gunicorn.org/en/stable/design.html#how-many-workers
# Timeout to 60s for larger results that require more time to collect from redis
CMD ["sh", "-c", "gunicorn chemcloud_server.main:app -w 2 -k uvicorn.workers.UvicornWorker --keep-alive 650 --timeout 60 -b 0.0.0.0:8000 --access-logfile -"]
