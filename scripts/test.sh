set -xe

# Start docker redis, rabbitmq, and psi4 celery worker containers
docker-compose --env-file .env -f docker/docker-compose.local.yaml up -d bigchem-worker

# Run tests
pytest --cov-report html:htmlcov --cov

# Stop docker containers
docker-compose -f docker/docker-compose.local.yaml down --remove-orphans
