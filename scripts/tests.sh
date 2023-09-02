#!/bin/sh

set -xe

# Start docker redis, rabbitmq, and psi4 celery worker containers
docker compose up -d --build bigchem-worker

# Run tests and capture the exit status
poetry run pytest --cov-report=term-missing --cov-report html:htmlcov --cov-config=pyproject.toml --cov=chemcloud_server --cov=tests . || TEST_EXIT_CODE=$?

# Stop docker containers
docker compose down --remove-orphans

# Exit with the pytest status (will be 0 if pytest was successful, and some other value otherwise)
exit ${TEST_EXIT_CODE:-0}
