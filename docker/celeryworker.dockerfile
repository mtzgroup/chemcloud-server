# Dockerfile for TeraChem Cloud Worker
# Contains celery worker and all CPU-only QC Packages
FROM continuumio/miniconda3:4.10.3

# https://github.com/awslabs/amazon-sagemaker-examples/issues/319
ENV PYTHONUNBUFFERED=1
LABEL maintainer="Colton Hicks <colton@coltonhicks.com>"

# Install system packages
# Need gcc and python3-dev for python psutil package
# https://github.com/giampaolo/psutil/blob/master/INSTALL.rst
RUN conda install psi4 -c psi4 && \
    # for psi4
    conda install msgpack-python && \ 
    conda install -c conda-forge rdkit && \
    conda install -c conda-forge xtb-python && \
    apt-get update && \
    apt-get install -y gcc python3-dev && \
    pip install pipenv


# Install application
WORKDIR /code/
COPY Pipfile Pipfile.lock ./
# Install to system python, no need for pipenv virtual env
RUN pipenv install --system --deploy
COPY ./terachem_cloud/workers/ terachem_cloud/workers/
COPY ./terachem_cloud/models.py terachem_cloud/models.py


CMD ["sh", "-c", "celery -A terachem_cloud.workers.tasks worker --without-heartbeat --without-mingle --without-gossip --loglevel=INFO"]
