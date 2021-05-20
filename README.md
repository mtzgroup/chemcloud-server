# TeraChem Cloud

Perform quantum calculations in the cloud.

## Development

### Install packages

```sh
pipenv install --dev
```

### Install pre-commit hooks

```sh
pipenv run pre-commit install # installs hooks for commit stage
pipenv run pre-commit install --hook-type pre-push # install hooks for push stage
```

### Run local TeraChem Cloud for dev

Run webserver, redis backend, rabbitmq broker, and Psi4-powered non-GPU accelerated worker instance. This command will build images for the web server and for the celery worker. It will mount the local code into the webserver so that it hot-reloads any changes made to the codebase. The worker can actively pickup tasks and run them.

```sh
pipenv run start
```

Go to http://localhost:8000/docs.

To shutdown the application:

```sh
pipenv run stop
```

For more granularity you can use docker to run various components of the service. If you prefer to run a non-dockerized version of the web app and/or the celery worker those commands can be found below. Useful commands to get started running sub-components of the application:

```sh
docker-compose -f docker/docker-compose.base.yaml -f docker/docker-compose.local.yaml up -d --build [service_of_interest]
```

Run non-dockerized local celery worker

```sh
pipenv run celery -A terachem_cloud.workers.tasks worker --loglevel=INFO
```

Run non-dockerized web server

```sh
pipenv run uvicorn terachem_cloud.main:app --reload
```

### Development on Fire (or any machine with GPUs)
Developing on a machine with GPUs means you can run `TeraChem` in server mode inside the docker worker. For development purposes, it's easiest to startup the `docker-compose` stack sans worker and then run the worker with `docker run` directly since `docker-compose` lacks good GPU support.

```sh
docker-compose -f docker/docker-compose.base.yaml -f docker/docker-compose.local.yaml up -d --build web-server mq redis

docker build -t tcc_celery_worker -f docker/celeryworker.dockerfile . && docker run -d --rm -v /data/coltonbh/license.key:/terachem/license.key -v /data/coltonbh:/scratch --net=host --gpus 2 -e TERACHEM_PBS_HOST='127.0.0.1' -e TERACHEM_PBS_PORT='11111'  --name tcc_worker tcc_celery_worker

# To stop worker
docker stop tcc_worker
```

### Manage environment and Auth0 for local development

Settings are managed in `terachem_cloud/config` and the `Settings` object will automatically look for environment variables found in both the environment and a `.env` file. If you need authentication to work for local development add the following variables to a `.env` file in the root directory with their corresponding values. These values are not required for tests to run correctly, though authentication-required endpoints will not work if hand-testing since a mocked auth system for local development has not been created.

```
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
AUTH0_API_AUDIENCE=
```

## Testing

You may need 3GB of memory allocated to Docker in order for the tests to run correctly. [Psi4](https://psicode.org), the quantum chemistry package used for running tests, requests memory resources that may exceed what Docker can provide if restricted to only 2GB of memory (the default setting). Insufficient memory will result in failing tests. Click `Docker -> Preferences -> Resources` to allocate more memory to your local docker engine.

```sh
pipenv run tests
```

A test summary will be output to `/htmlcov`. Open `/htmlcov/index.html` to get a visual representation of code coverage.

## Deployment

- Full CI/CD is handled via [CircleCi](https://circleci.com). See `.circleci/config.yml` for details.
- NOTE: If you add celery tasks you'll need to rebuild and push the `mtzgroup/terachem-cloud-worker:testing` image that the CI/CD pipeline uses for tests.

### Web Services

- In the directory on the server from which the `docker-compose.web.yaml` file will deploy, create the following files and populate with their correct secrets:
  - server.env
    - `BASE_URL=https://yourdomain.com`
    - `CELERY_BROKER_CONNECTION_STRING=amqp://${USERNAME}:${PASSWORD}@mq:5672` # pragma: allowlist secret
      - Note that the host should correspond to the service name for the `rabbitmq` instance found in the `docker-compose.web.yaml` file since we want the web server to connect locally rather than over the open internet. Also, note we are connecting to the port on which `rabbitmq` is running _insecurely_ on the stack. Traefik is providing TLS termination for external services that must connect _securely_ to `rabbit`.
    - `CELERY_BACKEND_CONNECTION_STRING=redis://:${PASSWORD}@redis:6379/0`
      - See note above for `rabbitmq`. Same logic applies.
    - `AUTH0_DOMAIN=xxx`
    - `AUTH0_CLIENT_ID=xxx`
    - `AUTH0_CLIENT_SECRET=xxx` # pragma: allowlist secret
    - `AUTH0_API_AUDIENCE=xxx`
  - rabbit.env
    - `RABBITMQ_DEFAULT_USER=your_default_user`
    - `RABBITMQ_DEFAULT_PASS=your_default_password`
  - redis.conf
    - `requirepass place_your_password_here`

### Workers

- In the directory on the server from which the `docker-compose.worker.yaml` file will deploy, create the following files and populate with their correct secrets:
  - `CELERY_BROKER_CONNECTION_STRING=amqps://${USERNAME}:${PASSWORD}@rmq.dev.mtzlab.com:5671`
    - Note the amqpS protocol. Since we are connecting over the open internet we require TLS. Also note the use of the `5671` *secure* port for `amqps` connections. This is the port on which `traefik` is listening for `amqps` connections.
  - `CELERY_BACKEND_CONNECTION_STRING=rediss://:${PASSWORD}@redis.dev.mtzlab.com:6379/0?ssl_cert_reqs=CERT_NONE`
    - Same logic for the `rabbitmq` connection string applies here. Note that we do not verify the SSL certificate. This is because `traefik` is dynamically generating and renewing SSL certificates so we do not have a "permanent" certificate that we can place on the client and use for verification. Very low risk of man-in-the-middle attacks here.
