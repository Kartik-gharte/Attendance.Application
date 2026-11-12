# Deployment

This document describes how to run the attendance service outside a
developer laptop, and the limits that apply.

The service is an experimental academic backend. It is not a production
attendance platform, and nothing in this document should be read as a
production readiness claim.

## Requirements

| Item | Requirement |
| --- | --- |
| Python | 3.11.16 (the version the CI workflow uses) |
| Operating system | Verified on macOS arm64. Linux and Windows are not verified. |
| Memory | See the measured baseline below. The biometric models add to it. |
| Disk | The database and the face embeddings, plus room for backups. |
| Camera | Required for the liveness flow. Not required for the API itself. |

The runtime dependencies are pinned in `requirements.txt` and the
development dependencies in `requirements-dev.txt`.

### Model assets

Two model assets are needed at run time. They are gitignored and must be
provisioned on each machine.

| Asset | Default location | Setting |
| --- | --- | --- |
| MediaPipe Face Landmarker | `models/mediapipe/face_landmarker.task` | `MEDIAPIPE_FACE_LANDMARKER_MODEL` |
| InsightFace `buffalo_l` | `~/.insightface/models/buffalo_l/` | `INSIGHTFACE_ROOT` |

Startup fails with an actionable error when the MediaPipe model is
missing. The InsightFace model is downloaded by the InsightFace package on
first use, which needs network access the first time.

See [SETUP.md](SETUP.md) for the provisioning steps.

## Starting the service

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The service reads its configuration from environment variables and from a
`.env` file in the project root. See [CONFIGURATION.md](CONFIGURATION.md).

### Worker count

**Run a single worker.**

```bash
python -m uvicorn app.main:app --workers 1
```

The liveness sessions live in an in-memory dictionary in the application
process. A session created by one worker is invisible to another worker, so
a liveness flow that starts on one worker and finishes on another fails
with "Invalid or expired liveness session".

This is a deliberate constraint for a single-process deployment, not a
bug to be worked around. Supporting multiple workers requires a shared
session store, which is future work. Until then, run one worker.

Horizontal scaling is out of scope for this project.

### TLS

The application does not terminate TLS. It expects a reverse proxy or a
service mesh in front of it that does.

This matters more than usual for this service, because the API carries
bearer tokens and camera frames. Both must be transported over TLS.

### File permissions

The service needs write access to:

- the directory that holds the database;
- the embedding directory, for the enrollment workflow;
- the backup directory, for the backup workflow.

It does not need write access anywhere else. The model directories only
need read access.

## Health checks

| Endpoint | Use | Failure means |
| --- | --- | --- |
| `GET /health/live` | Liveness probe | Restart the process |
| `GET /health/ready` | Readiness probe | Take the instance out of rotation |

Both are unauthenticated so a supervisor can reach them without
credentials. They expose only operational status. See
[API_REFERENCE.md](API_REFERENCE.md).

Point the liveness probe at `/health/live` and the readiness probe at
`/health/ready`. Do not point a restart policy at the readiness probe: a
database outage would then cause a restart loop instead of draining the
instance.

## Measured baseline

The numbers below were measured on a developer machine with the biometric
models stubbed out, so they exclude the cost of loading MediaPipe and
InsightFace. Reproduce them with:

```bash
python -m manual.benchmark
```

| Measurement | Value |
| --- | --- |
| Import time for `app.main` | 1.8 s |
| Resident memory after import | 136 MB |
| Startup without model assets | 0.06 s |
| Health request mean latency | 0.8 ms |
| Health request p95 latency | 1.2 ms |
| Throughput at 8 concurrent workers | 1630 requests/s |
| Maximum latency at 8 concurrent workers | 9 ms |

These numbers are a baseline, not a capacity guarantee. They say nothing
about the attendance verification path, which runs face detection and
embedding extraction and is far slower than the health endpoint. The
recognition path has not been benchmarked against real model assets and
real faces.

### Known limits

- SQLite calls are synchronous and run inside async routes. A slow write
  blocks the event loop for that worker.
- The service holds one process. There is no queue, no worker pool, and no
  backpressure beyond what the event loop provides.
- The liveness session dictionary is unbounded between requests, but
  sessions are removed on expiry and after use.

## Runbook

### Deploying

1. Provision the model assets.
2. Create the virtual environment and install the pinned dependencies.
3. Copy `.env.example` to `.env` and set the values.
4. Provision the accounts with `python -m app.auth.cli create-user`.
5. Apply the schema migrations with `python -m app.database.migrations upgrade`.
6. Take a backup with `python -m app.database.backup create`.
7. Start the service with a single worker.
8. Check that `/health/ready` returns `200`.

### Backups

Take a backup before every migration and before every release, and daily
while the service is in use.

```bash
python -m app.database.backup create
```

Keep at least one backup off the machine that runs the service, and test a
restore periodically. A backup that has never been restored is not a
backup. See [DATABASE.md](DATABASE.md).

### Upgrading

1. Take a backup.
2. Deploy the new version.
3. Check the startup logs for a migration failure.
4. If the schema version changed, run `python -m app.database.migrations upgrade`.
5. Check that `/health/ready` returns `200`.

Migrations are applied automatically during startup. The explicit upgrade
command exists so that the step is visible in the deployment procedure.

### Rolling back

The service has no automatic downgrade path. A migration that has been
applied cannot be reverted by deploying the previous version.

To roll back:

1. Stop the service.
2. Restore the database from the backup taken before the upgrade:
   `python -m app.database.backup restore --backup-path <backup> --overwrite`.
3. Deploy the previous version.
4. Check that `/health/ready` returns `200`.

The restore writes a safety copy of the current database next to it, so the
failed upgrade can still be inspected.

### Diagnosing a startup failure

| Symptom | Cause | Action |
| --- | --- | --- |
| `RuntimeError` naming `MEDIAPIPE_FACE_LANDMARKER_MODEL` | The MediaPipe model is missing or unreadable | Provision the model, check the setting |
| `MigrationError` naming a version | A migration failed and was rolled back | Read the error, fix the cause, restart. The database is unchanged. |
| The process starts but `/health/ready` returns `503` | The database or the models are not ready | Read the `checks` in the response |
| `AttributeError` on `services.liveness_service` | The service factory returned `None` | Check the startup configuration |

The startup logs are on stderr. See
[SECURITY_AND_PRIVACY.md](SECURITY_AND_PRIVACY.md) for what they contain.

### Diagnosing a liveness failure

`Invalid or expired liveness session` means one of:

- the session expired. The default validity is 30 seconds, configurable
  with `LIVENESS_VALIDITY_SECONDS`;
- the session was already used. A session is consumed by one attendance
  verification attempt;
- the request reached a different worker. This should not happen with a
  single worker;
- the service restarted, which clears the in-memory sessions.

## What this deployment does not provide

- No horizontal scaling or high availability.
- No rate limiting, account lockout, MFA, or SSO.
- No audit log. The application log is diagnostic output, not a tamper
  evident record.
- No automatic backup schedule.
- No metrics, tracing, or alerting.
- No measured accuracy for face recognition or presentation attack
  detection. See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
