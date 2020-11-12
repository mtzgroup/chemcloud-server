# Dockerfile for TeraChem Cloud Worker
# NOTE: This is running python3.7. There is no python3.9 code in tasks.py file so it works for now, but FYI
# may need to upgrdae at some point it issues develop.
FROM continuumio/miniconda3:4.8.2
# https://github.com/awslabs/amazon-sagemaker-examples/issues/319
ENV PYTHONUNBUFFERED=1
LABEL maintainer="Colton Hicks <colton@coltonhicks.com>"

# Install system packages
# Need gcc and python3-dev for python psutil package
# https://github.com/giampaolo/psutil/blob/master/INSTALL.rst
RUN conda install psi4 -c psi4 && apt-get update && apt-get install -y gcc python3-dev && pip install pipenv

# Install application
WORKDIR /code/
COPY Pipfile Pipfile.lock ./
# Install to system python, no need for pipenv virtual env
RUN pipenv install --system --deploy
COPY terachem_cloud/tasks.py ./terachem_cloud/tasks.py

EXPOSE 8000

CMD ["sh", "-c", "celery -A terachem_cloud.tasks worker --loglevel=INFO"]
