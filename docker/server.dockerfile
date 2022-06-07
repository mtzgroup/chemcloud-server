# Dockerfile for TeraChem Cloud Web Server
FROM python:3.9-slim
# https://github.com/awslabs/amazon-sagemaker-examples/issues/319
ENV PYTHONUNBUFFERED=1
LABEL maintainer="Colton Hicks <colton@coltonhicks.com>"

# Install system packages
# Need gcc and python3-dev for python psutil package
# https://github.com/giampaolo/psutil/blob/master/INSTALL.rst
RUN apt-get update && \
    apt-get install -y gcc git make python3-dev && \
    python -m pip install --upgrade pip && \
    pip install pipenv
    

# Install application
WORKDIR /code/
COPY Pipfile Pipfile.lock ./
# Install to system python, no need for pipenv virtual env
RUN pipenv install --system --deploy
COPY static ./static
COPY terachem_cloud/ ./terachem_cloud

EXPOSE 8000

# https://docs.gunicorn.org/en/stable/design.html#how-many-workers
# Timeout to 60s for larger results that require more time to collect from redis
CMD ["sh", "-c", "gunicorn terachem_cloud.main:app -w 2 -k uvicorn.workers.UvicornWorker --keep-alive 650 --timeout 60 -b 0.0.0.0:8000 --access-logfile -"]
