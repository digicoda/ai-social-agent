# v1.0.0 Release Checklist

## Automated validation

- [ ] Python test workflow is green.
- [ ] Docker build workflow is green.
- [ ] Compose configuration validation is green.
- [ ] Docker container health smoke test is green.

## Configuration

- [ ] `GEMINI_API_KEY` is configured in the deployment environment.
- [ ] `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_AUTHOR_URN` are configured when LinkedIn publishing is enabled.
- [ ] `INTERNAL_API_KEY` is configured for production API protection.
- [ ] `DATABASE_URL` points to the intended persistent database.
- [ ] `WORKER_POLL_SECONDS` and retry settings are appropriate for the deployment.

## Deployment

- [ ] `/health` returns HTTP 200.
- [ ] `/ready` returns `ready` with the production API key.
- [ ] API and worker share the same persistent database volume or database service.
- [ ] API and worker share media storage when scheduled media publishing is used.
- [ ] Publishing credentials are not committed to the repository.
- [ ] At least one approved draft has been validated through the intended publishing path before enabling automation.

## Release

- [ ] Review the changelog for the release version.
- [ ] Confirm the final release commit/PR is the intended source.
- [ ] Create the GitHub release/tag only after CI and deployment checks are green.
