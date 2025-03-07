# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

## [0.15.2] - 2025-03-07

### Added

- logfire for monitoring logs.

## [0.15.1] - 2025-03-05

### Changed

- Updated from BigChem `0.10.0 -> 0.10.7` to use the latest exceptions in qcop `0.10.1`. This aims to eliminate the possibility of `.program_output = None` when capturing exceptions raised in BigChem.

## [0.15.0] - 2025-02-25

### Added

- Endpoint for deleting results.

### Changed

- The server no longer deletes results automatically after returning them to end users. It was possible that the server would return the data to the reverse proxy (i.e., the request was fully successful from the server's standpoint) and then a network issue between the client and the reverse proxy would result in incomplete data transmission (this could also happen without a reverse proxy in place; the application writes its response to the OS socket and will consider the transmission successful). When the client would re-request the data, a `410` would be raised because the server had already deleted the data. Data is now only deleted upon confirmation from the client (via a delete request) that the data has been completely received.
- Updated dependency packages.

## [0.14.6] - 2025-02-19

### Added

- Link to `chemcloud` client user documentation to `/docs` webpage.

## [0.14.5] - 2025-02-14

### Fixed

- Random `410` errors caused (presumably) by using a `BackgroundTask` in the `/compute` endpoint to set the `task_id` in celery's backend. I suspect that when users query `/compute/output/{task_id}` right after submitting a big batch it's possible the `BackgroundTask` hasn't set the `task_id` in celery's backend yet and so the spurious `410` is returned due to a race condition.

## [0.14.4] - 2025-02-08

### Fixed

- Removed type aliasing of `ProgramOutput` generic types that was required for earlier versions of `pydantic` but was now causing `SinglePointResults` objects (or `ProgramInput` objects) to get consumed as `Files` (or `FileInput`) objects since that type was listed first and could consume the `SinglePointResults` data.

## [0.14.3] - 2025-02-08

### Changed

- Removed `black` and `isort` in favor of `ruff`.
- Upgraded to Python 3.13 for docker container.
- Moved code quality checks from CircleCI to GitHub actions.
- Fixed a few `httpx` calls to use the new API (`content=` vs `data=` for text/bytes data).

## [0.14.2] - 2024-09-12

### Changed

- Upgraded BigChem 0.9.0 -> 0.10.0.
- Upgraded `poetry.lock` package dependencies.

### Added

- `crest` to `SupportedPrograms`.

## [0.14.1] - 2024-08-07

### Changed

- Updated to [qcio ^0.11.7](https://github.com/coltonbh/qcop/blob/master/CHANGELOG.md#080---2024-07-19) which removes `NoResult` and moves `.files` from `ProgramOutput` to `ProgramOutput.results`.

## [0.14.0] - 2024-07-12

### Changed

- Updated qcio (0.10.1 -> 0.10.2). `Structure.ids` -> `Structure.identifiers`
- Updated qcop (0.7.1 -> 0.7.3)
- Updated bigchem (0.8.0 -> 0.8.1)

## [0.13.0] - 2024-07-10

### Changed

- 🚨 Updated to `BigChem 0.8.0` which uses new `qcio` `Structure` in place of `Molecule`.

## [0.12.0] - 2024-06-14

### Changed

- Updated to `BigChem 0.7.2` which uses latest Generics structures from `qcio`. Not a breaking change since the json representation of these objects is all the same as before; however, will bump major version since this feels like a shift to core data structures.
- 🚨 Renamed top-level argument to `/compute` `collect_wavefunction` to `collect_wfn` to match `qcop` nomenclature.
- Updated a number of dependencies and subpackages to latest versions. (`poetry lock`)
- Modernized typing syntax by removing `Dict`, `List`, `Union` declaration in favor of `dict`, `list`, `|`.
- Renamed `TaskState` -> `TaskStatus`
- Renamed `Output` to `ProgramOutputWrapper`.
  - 🚨 Renamed attributes from `state` -> `status` and `result` -> `program_output`.

## [0.11.6] - 2024-03-16

### Changed

- Updated `bigchem` to `0.6.5` which incorporates `qcop 0.5.0` which raises exceptions by default and therefore changed the `compute` signature in BigChem by removing the `raise_exc=True` default argument.
- Updated `black` from `23.x.x -> 24.x.x'.

## [0.11.5] - 2024-01-12

### Fixed

- Updated `bigchem` to `0.6.4` which incorporates `qcop` update that properly captures `geometric` exceptions.

## [0.11.4] - 2023-09-22

### Added

- Added test for `propagate_wfn` passed to program adapters that do not support it. An updated in `qcop` and `bigchem` resolved this issue resulting in a `ProgramFailure` object being correctly added to the exception so it can be returned in the `/compute/output/{task_id}` endpoint.

### Changed

- Updated dashboard styling to be more modern.

## [0.11.3] - 2023-09-20

### Changed

- Updated BigChem from `0.5.x` -> `0.6.x` to account for renaming of `DualProgramArgs` to `SubProgramArgs` in `qcio` package.

## [0.11.2] - 2023-09-19

### Fixed

- Fixed bug with `/v1/` -> `/v2/` change in API prefix and Auth0 callbacks.

### Changed

- Changed exception handing in `/compute/output/` endpoint to use celery result.traceback rather than traceback.format_exc() to capture the full traceback of the error.

## [0.11.1] - 2023-09-16

### Fixed

- Fixed `/compute/output/{task_id}` endpoint to properly return `*Output` or `ProgramFailure` objects for each calculation in a list of inputs.

### Removed

- Removed distinction between `Result` and `ResultGroup` and created a single output object for the `/compute/output/{task_id}` endpoint, `Output`.

## [0.11.0] - 2023-09-08

### Added

- Typos to pre-commit.
- `pydantic-settings` packages as part of pydantic `v1` -> `v2` upgrade.
- Added `x-max_batch_inputs` to OpenAPI schema so clients can query the max number of inputs they can send in a list.

### Changed

- Removed `QCElemental` models in favor of `qcio`.
- Upgraded from pydantic `v1` -> `v2`.
- Updated BigChem to latest version `0.5.x` and running jobs on the premise that exceptions will be raised by failed tasks.
- Api prefix updated from `/api/v1/` -> `/api/v2/`
- `/compute/results/` updated to `/compute/output/` to more closely match `qcop` nomenclature of "inputs" and "outputs."
- Now returning the celery state directly as the `result.status` value. Need to decide how to handle status and result returning in the future (I think it can be significantly simplified), but for now this setup works.
- Always install the latest version of `poetry` in the docker image.
- Build BigChem in `/opt`.

### Removed

- `mypy.ini` and `setup.cfg` and moved all configuration to `pyproject.toml`.
- `flake8` in favor of `ruff`.
- `compute-procedure` endpoint as it's not longer needed with `qcio`.
- Dropped `git`, `python3-dev`, and `gcc` from main docker image since `psutil` is no longer required (was required by `qcengine`)

## [0.10.1] - 2023-02-20

### Changed

- Running BigChem containers from `mtzgroup` rather than `coltonbh`

## [0.10.0] - 2023-02-20

### Changed

- Changed `pipenv` for `poetry`
- Updated python `3.9` -> `3.11`
- Updated tests to only depend upon `httpx` and removed `requests` library
- Updated BigChem to `0.4.0` and installing from PyPi now

## [0.9.1] - 2022-12-27

### Changed

- Updated BigChem to `0.3.0` released on PyPi instead of building from GitHub.
- Updated a bunch of packages in `Pipfile.lock`
- Updated dependencies for `isort` and added explicit `Optional[]` typing for `mypy`

## [0.9.0] - 2022-07-19

### Changed

- Changed projects name from `QCCloud` to `ChemCloud`
- Updated `bigqc` to `bigchem`

## [0.8.1] - 2022-07-15

### Changed

- Changed distributed algorithms from being called `qcc` algorithms to `bigqc` algorithms to correctly identify where they are coming from.

## [0.8.0] - 2022-07-14

### Changed

- Updated project name from TeraChem Cloud to Quantum Chemistry Cloud

## [0.7.2] - 2022-07-11

### Changed

- Pass only strings for default values to `compute_tcc` function that executes distributed algorithms. Passing `Enum` values caused celery to try and deserialize objects containing references to the `terachem_cloud` package where the `Enums` were defined.

## [0.7.1] - 2022-07-12

### Changed

- Update to BigQCv0.1.3

## [0.7.0] - 2022-06-14

### Changed

- Refactored all backend workers and middleware to a separate out the BigQC project. This project now comprises just a web layer on top of the BigQC engine. This change resulted in the need to change a few environment variables to reflect the change to BigQC. `CELERY_BROKER_CONNECTION_STRING` -> `BIGQC_BROKER_URL` and `CELERY_BACKEND_CONNECTION_STRING` -> `BIGQC_BACKEND_URL`.
- Changed dependencies to reflect the refactor.

## [0.6.2] - 2022-06-02

### Changed

- Removed web server memory constraints at docker level. Large results were crashing server because of 500MB limit. When (300MB+) results were pulled into memory server would require >500MB memory and would be terminated by process manager.
- Increased gunicorn worker timeout from 30s -> 60s to accommodate larger results.
- Set results to expire in 3 days instead of default 1 day in backend store.

## [0.6.1] - 2022-04-25

### Added

- Patched `geomeTRIC` to enable `transition=True` for json inputs used in `QCEngine`

## [0.6.0] - 2022-04-02

### Changed

- `/compute/result` changed to `GET` request with signature `/compute/result/{task_id}`
- Removed much unnecessary internal code around managing Task state due to saving task structure to the DB so that
  clients only have to supply a single task ID regardless if the task is a batch or single calculation.

## [0.5.1] - 2022-03-27

### Added

- Base64 encode bytes input values submitted to terachem_fe by client

## [0.5.0] - 2022-03-26

### Added

- 🚨BREAKING CHANGE🚨: Support for `native_files` protocol that enables end users to retrieves files generated by a QC package during computation. E.g., can retrieve `c0` files from a TeraChem computation. Only a breaking change if end user has an old version of `qcelemental` that does not support the `native_files` protocol and output field.
- Users can upload `c0` files to seed a TeraChem computation with a wave function.
- TeraChem Frontend containers to XStream deployment to access files created by TeraChem job.

### Changed

- 🚨BREAKING CHANGE🚨: Supported Engine for TeraChem changed from `terachem_pbs` -> `terachem_fe`
- 🚨BREAKING CHANGE🚨: `tcc_kwargs` -> `tcc:keywords`
- Pegged versions of psi4, rdkit, and xtb-python. Updated qcelemental to work with psi4v1.5. Updated python packages without pegged versions.
- Updated app to run python3.9.
- Updated CircleCI python3.7->3.9.
- Updated XStream TeraChem workers to new image.

## [0.4.2] - 2021-06-11

### Added

- "tcc" compute engine
- Parallel hessian and parallel frequency analysis methods to tcc engine

### Changed

- Changed celery serializer from `json` to `pickle`. This allows chained methods to receive python data types directly, rather than serialized representations. Since users do not have direct access to the celery layer and can only submit json serialized (and validated) objects via the API I do not feel there are security risks.

## [0.4.1] - 2021-06-07

### Added

- Private queues for compute

## [0.4.0] - 2021-06-04

### Added

- Batch compute capabilities to `/compute` and `/compute-procedure`

### Changed

- 🚨BREAKING CHANGE🚨: Updated `/compute*` endpoints to return `Task` objects including `GroupTask` objects that may contain subtasks instead of returning a single `str` of the `task_id`
- 🚨BREAKING CHANGE🚨: Updated `/result` endpoint to accept `Task` objects instead of just a `str` of `task_id`. This included updating the endpoint to be a `POST` instead of `GET` endpoint.

## [0.3.5] - 2021-05-26

### Added

- `xtb` to compute engines
- Added `cached-property` package since `kombu` didn't install it by default as a dependency into the linux docker container.

### Changed

- Updated `tcpb>=0.8.0`
- Updated `celery` version

## [0.3.4] - 2021-05-21

### Added

- `geomeTRIC` optimizer
- `rdkit` engine (adds force fields which can be used for single point computations or in optimizers)

### Changed

- Run compute tests on hydrogen instead of water for faster results

## [0.3.3] - 2021-05-19

### Added

- `compute_procedure` task for doing geometry optimizations using `pyberny`
- VSCode settings file added to repo.

### Changed

- Combined two commands from the CI/CD pipeline used against XStream to get fewer auth errors
- Updated `mypy` definitions on `Settings` object to pass `mypy` checks while still allowing tests to run on CircleCi without needing Auth0 configuration. I.e., the web application can be run without needing Auth0 config (for testing purposes).
- pre-commit `mypy` now loads from GitHub repo instead of local `mypy` install.

## [0.3.2] - 2021-04-06

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
- Links on user dashboard to `qccloud` python client, `/logout`, and a brief description of how to change password.
- Links to `users/dashboard` on the main documentation page.
- Forgotten `__init__.py` to `terachem_cloud` package. Added `__version__` to file. This causes `mypy` checks to fail as they were previously not inspecting this package fully due to missing `__init__.py`.
- `TaskStatus` enum to hold task status values.

### Changed

- `/compute/result/{task_id}` can return either `AtomicResult` or `FailedOperation` objects.
- CircleCi build pipelines to only include a single build step for web and workers instead of a split pipeline for dev/prod
- Can approve CircleCi build and deploy steps upfront without having to wait for tests to pass. Build/deploy will still only occur if tests pass.
- XStream stacks for dev/prod no longer derive from the same template file.
- Changed `CeleryAtomicResult` to `TaskResult` and change `atomic_result` attribute to just `result` to note that `result` may now be an `AtomicResult` or a `FailedOperation` (a result could either of these data types).

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

[unreleased]: https://github.com/mtzgroup/chemcloud-server/compare/0.15.2...HEAD
[0.15.2]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.15.2
[0.15.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.15.1
[0.15.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.15.0
[0.14.6]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.14.6
[0.14.5]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.14.5
[0.14.4]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.14.4
[0.14.3]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.14.3
[0.14.2]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.14.2
[0.14.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.14.1
[0.14.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.14.0
[0.13.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.13.0
[0.12.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.12.0
[0.11.6]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.11.6
[0.11.5]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.11.5
[0.11.4]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.11.4
[0.11.3]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.11.3
[0.11.2]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.11.2
[0.11.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.11.1
[0.11.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.11.0
[0.10.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.10.1
[0.10.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.10.0
[0.9.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.9.1
[0.9.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.9.0
[0.8.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.8.1
[0.8.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.8.0
[0.7.2]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.7.2
[0.7.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.7.1
[0.7.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.7.0
[0.6.2]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.6.2
[0.6.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.6.1
[0.6.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.6.0
[0.5.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.5.1
[0.5.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.5.0
[0.4.2]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.4.2
[0.4.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.4.1
[0.4.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.4.0
[0.3.5]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.3.5
[0.3.4]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.3.4
[0.3.3]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.3.3
[0.3.2]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.3.2
[0.3.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.3.1
[0.3.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.3.0
[0.2.1]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.2.1
[0.2.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.2.0
[0.1.0]: https://github.com/mtzgroup/chemcloud-server/releases/tag/0.1.0
