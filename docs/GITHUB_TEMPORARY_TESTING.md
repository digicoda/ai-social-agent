# Temporary GitHub testing

The `Temporary GitHub Test` workflow provides a disposable Docker environment for validating the application on a GitHub-hosted runner.

## What it does

1. Creates a temporary `.env` with randomly generated test-only credentials.
2. Builds the API and worker containers with Docker Compose.
3. Checks `/health` and protected `/ready`.
4. Logs into `/dashboard` and verifies an authenticated protected API request.
5. Verifies the worker container is running.
6. Optionally keeps the stack alive for a short period for workflow-level inspection.
7. Collects Compose logs as a short-lived workflow artifact.
8. Destroys the containers and volumes at the end of the job.

Run it from **Actions → Temporary GitHub Test → Run workflow**.

## Important limitation

This is a CI/test environment, not a hosted development server. GitHub-hosted runners are fresh machines for workflow jobs and are decommissioned after the job finishes. The workflow therefore cannot provide a permanent public dashboard URL or persistent SQLite database.

For interactive development, the next step is to run the same Docker Compose stack on the local PC. For production, move the container stack to a persistent host and keep GitHub Actions as CI/CD.
