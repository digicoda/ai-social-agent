# Phase 4 Notes

Phase 4 currently implements direct LinkedIn text publishing behind a provider interface.

Publishing is intentionally explicit: the application never publishes a draft unless its database status is `approved`.

Credentials:
- `LINKEDIN_ACCESS_TOKEN`
- `LINKEDIN_AUTHOR_URN`
- `LINKEDIN_API_VERSION`

No credential values belong in source control.

The next expansion can add other providers behind `Publisher` without changing the approval workflow.