# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Test assertions to check that results are deleted from celery backend after retrieval by client.

### Changed

- Added flags `--without-heartbeat --without-mingle --without-gossip` to celery workers to reduce network overhead chattiness.
- Delete celery results from backend upon retrieval by client. This will prevent Redis from becoming a memory hog at times of high computational load.

## [0.3.1] - 2021-03-10

### Added

- Changelog
- Updated `tcpb` package to `>=0.7.1` to enable molden file creation using `imd_orbital_type="whole_c"` keyword.

## [0.3.0] - 2021-01-26

### Added

- Added TeraChem Protocol Buffer server to available compute engines.
- XStream deployment for both dev and prod now require GPUs to power Terachem. Deployment config for dev/prod was split into `docker-compose.xstream.dev.yaml` and `docker-compose.xstream.prod.yaml`.
- TeraChem license.key docker secret to swarm on XStream
- `architecture.md` to `/docs/development` to document core architectural decisions.
- Links on user dashboard to `tccloud` python client, `/logout`, and a brief description of how to change password.
- Links to `users/dashboard` on the main documentation page.
- Forgotten `__init__.py` to `terachem_cloud` package. Added `__version__` to file. This causes `mypy` checks to fail as they were previously not inspecting this package fully due to missing `__init__.py`.
- `TaskStatus` enum to hold task status values.

### Changed

- `/compute/result/{task_id}` can return either `AtomicResult` or `FailedOperation` objects.
- CircleCi build pipelines to only include a single build step for web and workers instead of a split pipeline for dev/prod
- Can approve CircleCi build and deploy steps upfront without having to wait for tests to pass. Build/deploy will still only occur if tests pass.
- XStream stacks for dev/prod no longer derive from the same template file.
- Changed `CeleryAtomicResult` to `TaskResult` and change `atomic_result` attribute to just `result` to note that `result` may now be an `AtomicResult` or a `FailedOperation` (a result could either of these data types).

### Removed

## [0.2.1] - 2021-01-21

### Removed

- Removed `docker_layer_caching` from CircleCi build process

## [0.2.0] - 2021-01-21

### Added

- refresh_flow to `/oauth/token` endpoint

## [0.1.0] - 2020-12-18

### Added

- Three endpoints all available on `/api/v1`:
  1. `/oauth/token` to get JWTs,
  2. `/compute` to submit AtomicInput compute request,
  3. `/compute/result/{task_id}` to request a result delivered as an AtomicResult object.
- Auth provided by Auth0.

[unreleased]: https://github.com/mtzgroup/terachem-cloud/compare/0.3.1...HEAD
[0.3.1]: https://github.com/mtzgroup/terachem-cloud/releases/tag/0.3.1
[0.3.0]: https://github.com/mtzgroup/terachem-cloud/releases/tag/0.3.0
[0.2.1]: https://github.com/mtzgroup/terachem-cloud/releases/tag/0.2.1
[0.2.0]: https://github.com/mtzgroup/terachem-cloud/releases/tag/0.2.0
[0.1.0]: https://github.com/mtzgroup/terachem-cloud/releases/tag/0.1.0
