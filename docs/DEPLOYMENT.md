# Deployment Runbook

Operational reference for running Spoken Tutorial Generator in production.
Everything needed to deploy, verify, roll back, and recover lives either in
this repository or in the server's `.env` — there is deliberately no third
place. (The pre-rewrite deployment ran from a compose invocation recorded
nowhere; treat any urge to run an undocumented command on the server as a bug
in this document and fix the document.)

## Topology

```
GitHub Actions ──SSH──> gateway: beta.spoken-tutorial.org
                              │  (proxy hop only)
                              ▼
                        VM: narmada.spoken-tutorial.org
                          ├── slide-generator   (this project)
                          ├── spoken-social     (other tenant)
                          └── nurturehub        (other tenant)

Browser ── https://creation.edupyramids.org ──> host nginx (TLS, Let's Encrypt)
                                                    │
                                                    ▼
                                          127.0.0.1:8080  (frontend container)
```

- **Shared VM.** narmada runs two other projects. This project claims exactly
  one loopback port (`127.0.0.1:8080`) and namespaced volumes; be considerate
  with disk/CPU and communicate deploy windows if a change is disruptive.
- **Network exposure.** Only `127.0.0.1:8080` is published. PostgreSQL, Redis,
  Prometheus and Grafana are reachable solely on the internal Compose network.
  TLS terminates at the **host** nginx, which forwards everything to 8080; the
  frontend container's nginx owns application routing (`/api/`, `/static/`,
  `/output/`, `/grafana/`, SPA fallback).
- **SSH path** (two hops, key-based, no passwords): gateway user `bhavi` on
  beta, then user `shagnik` on narmada. The `shagnik` user is in the `docker`
  group, so no sudo is needed for any procedure below. CI uses its own
  dedicated key pair for the second hop — individually revocable without
  affecting human access.

## What lives on the server

The project directory on narmada contains **only**:

| File/dir | Source of truth | Notes |
|---|---|---|
| `compose.yaml` | this repo (scp'd by every deploy) | never edit on the server |
| `deploy/` | this repo (scp'd by every deploy) | Prometheus config + Grafana provisioning |
| `.env` | **the server itself — hand-managed** | all secrets; exists nowhere else. **Back it up before touching it.** Also records the deployed `IMAGE_TAG`. |

No source code, no language runtimes, no build tools. If a procedure seems to
require anything else on the server, the procedure is wrong.

## Normal deploy

Merge (or push) to `main`. That is the entire procedure.

`.github/workflows/build.yml` then:

1. Builds `backend`, `worker`, `frontend` images in a parallel matrix
   (linux/amd64 — the VM's architecture; never build production images on an
   Apple Silicon laptop), pushes to GHCR as `sha-<7char>` + `latest`.
2. Deploy job (only if **all three** builds succeed): scp `compose.yaml` +
   `deploy/` to the VM, set `IMAGE_TAG=sha-<commit>` in `.env`,
   `docker compose pull`, `docker compose up -d --remove-orphans`.
3. Restarts Grafana unconditionally (datasource provisioning is read only at
   startup — see Gotchas), as a non-fatal step.
4. **Health gate:** polls backend (HTTP `/health` — a live DB round-trip) and
   whisper-worker (Celery broker ping) for up to 4 minutes. If either ends
   unhealthy, the run **fails** and prints the last 50 log lines of each
   service — read those before SSHing anywhere.

Required repository secrets: `GATEWAY_HOST`, `GATEWAY_USER`, `GATEWAY_SSH_KEY`,
`VM_HOST`, `VM_USER`, `SSH_PRIVATE_KEY`, `PROJECT_PATH`.

## Rollback

Seconds, no rebuild — every merge's images stay in GHCR under their immutable
`sha-` tag, and `.env` records what is currently deployed:

```bash
# on the VM, in the project directory
grep IMAGE_TAG .env                 # confirm what is running now
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=sha-<previous>/' .env
docker compose up -d
```

Find previous tags with `git log --oneline` locally (the tag is the commit
sha) or in the GHCR package pages.

## Verification & monitoring

- **Dashboards:** `https://creation.edupyramids.org/grafana/` — the
  "App Overview" dashboard covers request rate/latency (self-monitoring
  endpoints excluded), 5xx rate (health-check 503s deliberately included:
  they signal database outages), per-user activity, job runtimes, and
  thread-stall stages.
- **On the VM:** `docker compose ps` (everything `healthy`/`running`),
  `docker compose logs --tail 50 <service>`.
- **After UI-facing changes, load the page in a browser.** Four rounds of
  green API checks once coexisted with a completely blank dashboard; the
  browser console found the cause in one step. "The API returns data" is not
  evidence that "the page works".

## Grafana provisioning gotchas

All Grafana state is provisioned from `deploy/grafana/` in git — a wiped
`grafana_data` volume fully self-heals (tested deliberately). Four traps,
each of which produces a **blank dashboard while every backend check passes**:

1. The Postgres datasource's `database` must live under `jsonData`, not the
   legacy top-level key — the backend honours both, the frontend only reads
   `jsonData`.
2. SQL panel targets need `rawQuery: true` and `editorMode: "code"`, or the
   frontend silently never issues the query.
3. Use the canonical plugin id `grafana-postgresql-datasource`, not the legacy
   alias `postgres`, in panel `datasource.type`.
4. Datasource provisioning is read **only at Grafana startup** (dashboards
   re-read every 30 s) — which is why the deploy restarts Grafana.
5. Never install plugins by hand into the data volume: a hand-installed
   image-renderer plugin once crash-looped Grafana every ~63 s for a month
   (it outlived every rebuild because it lived in the volume).

Grafana reads PostgreSQL through the dedicated `grafana_ro` role
(SELECT-only). If you add tables that dashboards should see, grant SELECT to
`grafana_ro` in a migration.

## Disaster recovery notes

- **`.env` is the only unversioned artifact.** Losing it means re-issuing
  every API key and OAuth credential. Keep an offline backup; back it up
  before every manual edit.
- Postgres data lives in the `postgres_data` volume; there is currently **no
  automated database backup** (see Known follow-ups).
- A wiped `grafana_data` volume self-heals from provisioning. A wiped
  `prometheus_data` volume loses metric history but recovers cleanly.
- Worker deploys never kill in-flight transcriptions: `stop_grace_period` is
  300 s, and Celery `acks_late` + `reject_on_worker_lost` re-queue jobs whose
  worker dies anyway. The stale-job reaper fails anything stuck `running`
  past `TIMED_SCRIPT_JOB_TIMEOUT_SECONDS`.

## Known follow-ups

Tracked here so they stay visible; each is deliberate debt, not an oversight:

1. **Production hardening flag.** `ENVIRONMENT=production` (disables public
   `/api/docs`, tightens CORS, enforces strong-JWT validation) is configured
   in code but its rollout is pending. It must be set **together** with a
   real `JWT_SECRET_KEY` (`openssl rand -hex 32`) in the VM's `.env` — the
   app intentionally refuses to boot in production mode with a weak secret.
   Do both in one change window.
2. **Alerting.** The dashboard exposes stuck-job and service-down conditions,
   but nothing pages anyone — add a Grafana contact point (Slack/e-mail).
3. **Database backups.** No automated `pg_dump` schedule yet.
4. **Container-level resource monitoring** (cAdvisor / postgres / redis
   exporters) — deliberately out of scope so far.
5. **Log rotation** for chatty services (Whisper progress lines).
6. **Coverage measurement in CI.**
