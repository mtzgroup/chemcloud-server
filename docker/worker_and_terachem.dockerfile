# Dockerfile for TeraChem Cloud Worker with TeraChem baked into the image
# Given that we are running TeraChem in server mode on TCC there are many
# reasons to package it separately from the open source packages. 
# See docker/development/architecture.md. Keeping this file for a bit until 
# I decide it is no longer necessary
FROM mtzgroup/terachem:1.9-2021.02-dev-arch-sm_37-sm_52-sm_61-sm_70

# https://github.com/awslabs/amazon-sagemaker-examples/issues/319
ENV PYTHONUNBUFFERED=1
LABEL maintainer="Colton Hicks <colton@coltonhicks.com>"

# Install System Packages 
# Need gcc and python3-dev for python psutil package; https://github.com/giampaolo/psutil/blob/master/INSTALL.rst
RUN yum update -y && \
    yum install -y \
    wget \
    python3-dev \
    gcc \
    git \
    && yum clean all

# Install Conda
# Modified from https://github.com/ContinuumIO/docker-images/blob/master/miniconda3/debian/Dockerfile
ENV PATH /opt/conda/bin:$PATH

# Leave these args here to better use the Docker build cache
ARG CONDA_VERSION=py37_4.8.2
ARG CONDA_MD5=87e77f097f6ebb5127c77662dfc3165e

RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-x86_64.sh -O miniconda.sh && \
    echo "${CONDA_MD5}  miniconda.sh" > miniconda.md5 && \
    if ! md5sum --status -c miniconda.md5; then exit 1; fi && \
    mkdir -p /opt && \
    sh miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh miniconda.md5 && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc && \
    find /opt/conda/ -follow -type f -name '*.a' -delete && \
    find /opt/conda/ -follow -type f -name '*.js.map' -delete && \
    /opt/conda/bin/conda clean -afy


# Install psi4 and pipenv
RUN conda install psi4 -c psi4 && pip install pipenv

# Install application
WORKDIR /code/
COPY Pipfile Pipfile.lock ./
# Install to system python, no need for pipenv virtual env; system python is Miniconda version now
RUN pipenv install --system --deploy
COPY terachem_cloud/workers/ terachem_cloud/workers/
COPY terachem_cloud/workers/worker-start.sh .
RUN chmod +x /code/worker-start.sh

CMD ["bash", "/code/worker-start.sh"]
