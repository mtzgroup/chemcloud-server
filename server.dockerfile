# Dockerfile for TeraChem Cloud Web Server
FROM python:3.9-slim
# https://github.com/awslabs/amazon-sagemaker-examples/issues/319
ENV PYTHONUNBUFFERED=1
LABEL maintainer="Colton Hicks <colton@coltonhicks.com>"

# Install system packages
# Need gcc and python3-dev for python psutil package
# https://github.com/giampaolo/psutil/blob/master/INSTALL.rst
RUN apt-get update && apt-get install -y gcc python3-dev && pip install pipenv

# Install application
WORKDIR /code/
COPY Pipfile Pipfile.lock ./
# Install to system python, no need for pipenv virtual env
RUN pipenv install --system --deploy
COPY terachem_cloud/ ./terachem_cloud

EXPOSE 8000

CMD ["sh", "-c", "uvicorn --host 0.0.0.0 --port 8000 terachem_cloud.main:app"]
