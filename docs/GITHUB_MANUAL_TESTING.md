# GitHub interactive manual testing

Phase 9 provides a temporary browser-accessible environment for manual QA before local or shared-hosting deployment.

## Start a test session

1. Open the repository's **Actions** tab.
2. Select **GitHub Interactive Manual Test**.
3. Click **Run workflow**.
4. Select 10, 20, or 30 minutes.
5. Open the running job summary.
6. Use the temporary **Dashboard** URL and generated test credentials shown in the summary.

GitHub supports manually triggered workflows through the `workflow_dispatch` event and the Actions UI. The environment is intentionally disposable rather than persistent.

## What to test

### Dashboard

- Login and logout.
- Overview loads correctly.
- System/readiness status is visible.
- Navigation between Research, Content Approval, Schedules, Publishing History, and System works.

### Research and AI pipeline

The temporary environment deliberately has no Gemini key or LinkedIn credentials. This means the browser-level infrastructure can be tested safely, but live Gemini/LinkedIn operations require credentials later.

When testing with credentials, use GitHub Actions secrets rather than committing keys to the repository.

### Scheduling and worker

The worker polls every 5 seconds in the manual environment so scheduled test work becomes observable quickly.

### Publishing

LinkedIn publishing is disabled in the default manual environment. Do not add production credentials to this workflow. A later controlled test can add GitHub Environment secrets for LinkedIn after the rest of the pipeline is verified.

## Temporary environment behavior

The API, worker, SQLite database, and media volume run only for the selected workflow duration. A Cloudflare Quick Tunnel provides a temporary HTTPS URL for browser testing; it is not a production hostname.

The workflow tears down the containers and volumes when the run ends. Short diagnostic logs are uploaded as a one-day artifact for troubleshooting.

## Important security rule

Treat the temporary URL and generated password as test credentials. Do not publish them in screenshots, issues, README files, or social posts. Do not use real customer data in this environment.
