# TeraChem Cloud

Perform quantum calculations in the cloud.

## Development

Install packages

```sh
pipenv install --dev
```

Install pre-commit hooks

```sh
pipenv run pre-commit install
```

You can run local development entirely through docker. This will build images for the web server and for the celery worker. It will mount the local code into the webserver so that it hot-reloads any changes made to the codebase. The worker can actively pickup tasks and run them. If you prefer to run a non-dockerized version of the web app and/or the celery worker simply comment out the `web-server` and `worker` services in the `docker-compose.local.yaml` file.

```sh
docker-compose -f docker-compose.base.yaml -f docker-compose.local.yaml up -d --build
```

Run local celery worker

```sh
pipenv run celery -A terachem_cloud.tasks worker --loglevel=INFO
```

Run the web server

```sh
pipenv run uvicorn terachem_cloud.main:app --reload
```

## Deployment

- Place the `docker-compose.base.yaml` and `docker-compose.dev/prod.yaml` on the server of interest.
- Fill in required environment variables in docker-compose templates or make them available in the environment.
- Place a `redis.dev/prod.conf` in the same directory with a `requirepass mysupersecretpassword` directive.
- run `docker stack deploy --with-registry-auth -c stacks/tcc/docker-compose.base.yaml -c stacks/tcc/docker-compose.dev.yaml tcc`
- DO NOT FORGET TO INCLUDE `--with-registry-auth` IF ONE OR MORE OF THE IMAGES IN THE STACK ARE IN A PRIVATE REPO!!!
  - You may need to run `docker login` first.
