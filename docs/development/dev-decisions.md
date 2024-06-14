# Architecture

## Task State

- For task state reported via the `/compute/output/{task_id}` endpoint I originally implemented a full replica of Celery's `AsyncTask.status` in the `TaskStatus` enum. With time this seemed unnecessary especially since there is no API for retrying or revoking (cancelling) a task. The endpoint is currently simplified to just:
  - `TaskStatus.PENDING` if a result is not ready.
  - `TaskStatus.SUCCESS` if successful.
  - `TaskStatus.Failure` if unsuccessful.
  - `TaskStatus.Started` is not supported because this isn't available on a `GroupResult` object and I wanted a simple endpoint that treats single calculations and groups of calculations with the same code and the benefit of a `STARTED` state seemed trivial.
