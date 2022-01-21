# Architecture

## Core Decisions and Justifications

### Dockerize TeraChem Separately from Celery Worker

Running TeraChem in server mode so that it is callable from the celery worker image could be accomplished one of two ways:

1. Run TeraChem in the background of the celery worker container
2. Run TeraChem in a separate container and network it so that it is accessible by the celery worker

Option #2 has been selected given the following justifications:

Pros:

- TeraChem crashes a lot. When it crashes, server mode dies. If we are running TeraChem in the background of the worker container we need an additional process (such as `systemd` or `supervisord`) to monitor TeraChem and restart it after crashing. Various other approaches are described [here](https://docs.docker.com/config/containers/multi-service_container/). Breaking the Docker rule of "one container one process" divorces us from all the benefits of having docker monitor the status of the container and restart it when the main process dies. Instead, we have to add the additional complexity of our own process monitors in each container.
- I can maintain TeraChem repos/images separately from the celery worker codes. Each has a very different lifecycle and build/runtime requirements. Keeping GPU/CPU codes separately seems wise.
- Easier to run non-GPU accelerated workers given CPU-only celery workers.
- Smaller worker images.
- Not packaging TeraChem into worker images where it may not be used on various machines.
- TeraChem runtime requirements are quite unique (CUDA, GPUs, old libraries). I don't want to marry these requirements to the worker containers themselves which may benefit from dramatically different runtime requirements.
- All open source software can live in a single image (celery worker + other QC packages) separate from TeraChem which may require licenses.
- The TeraChem server mode client assumes a server anywhere in the world--opening the possibility of running TeraChem farms separate from my workers is interesting.
- Can scale CPU and GPU workloads separately and with more flexibility.
- Cleaner separation of concerns--one container to receive and execute tasks, one container to make available and execute TeraChem workloads.

Cons:

- Shared data access between the celery worker and TeraChem container becomes slightly more complicated. I can no longer assume access to the same filesystem. However, sharing data between containers has many well documented solutions. One such solution is sharing a docker volume which may write to a local scratch directory or a network file system if greater persistence is required.
- 2x the number of docker containers running to power the backend.

### XStream Worker Setup

- There is currently (Feb 22, 2021) no supported format for gpu specifications in the docker-compose 3 spec. As a result, there is no equivalent feature to k8's experimental GPU scheduler (https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/deploying-nvidia-gpu-device-plugin). Therefore, each TeraChem instance must be uniquely declared with hardcoded references to the GPUs it will consume using NVIDA_VISIBLE_DEVICES.
- Due to this constraint, there is little advantage to having a shared template between the dev and prod environments. Each is simply declared using hard-coded parameters.
- The $LSTOR directory on XStream is used for local scratch work (http://xstream.stanford.edu/docs/storage/). This is where docker creates volumes. We have 480GB per node of scratch space available on $LSTOR. We probably want to monitor this space from time-to-time and make sure it isn't filled up.
- If we ever want to use network storage to have greater persistence for scratch files see https://docs.docker.com/storage/volumes/#start-a-service-with-volumes as a reference and look into the "cloud-stor" NFS Stefan previously used for TCC on XStream.
- Since we have to hard-code the GPUs that each TeraChem instance will consume we must also hard-code the nodes they run on so that we don't get two TeraChem instances on a single node trying to consume the same GPUs.
- When a TeraChem server starts up it creates a root directory like `server_2021-01-28-17.14.46` in its `scratch` directory where it writes data. This path is created based on the server start time. Since it is very possible that two servers will startup at the same time on a cluster there is a possibility for collision. The current TC server will crash if a directory already exists with its desired timestamp. Since docker will restart servers upon failure this problem is "solved" in that each wave of TeraChem startups will have collisions, the second server to startup will see this directory and crash, restart, and thereby generate a new timestamp for its scratch output.
