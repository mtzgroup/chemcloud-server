set -xe

# Start docker redis, rabbitmq, and psi4 celery worker containers
docker-compose up -d bigchem-worker

# Run tests
pytest --cov-report html:htmlcov --cov

# Stop docker containers
docker-compose down --remove-orphans
