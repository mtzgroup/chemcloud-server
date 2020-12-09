# Start docker redis, rabbitmq, and psi4 celery worker containers
docker-compose -f docker-compose.base.yaml -f docker-compose.local.yaml up -d --build mq redis worker

# Run tests
pytest --cov-report html:htmlcov --cov

# Stop docker containers
docker-compose -f docker-compose.base.yaml -f docker-compose.local.yaml down --remove-orphans
