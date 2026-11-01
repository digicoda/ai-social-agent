# Security Policy

## Supported versions

Security fixes are currently handled on the default development branch. Formal supported-version guarantees will be published when release maintenance is established.

## Reporting a vulnerability

Please do not report exploitable vulnerabilities, exposed credentials, access tokens, private user data, or detailed attack instructions in a public issue.

Use GitHub's private vulnerability reporting feature for this repository if it is enabled. If private reporting is unavailable, contact the repository owner through a private GitHub communication channel and provide only the minimum information needed to begin a coordinated disclosure.

Please include:
- A concise description of the issue and its potential impact.
- Affected component or version/commit, if known.
- Reproduction steps or a minimal proof of concept, avoiding real user data.
- Any suggested mitigation, if available.

Do not test against systems, accounts, or data you do not own or have explicit permission to assess.

## Secret handling

Never commit API keys, OAuth tokens, passwords, session secrets, private keys, production database files, or real customer data. Revoke and rotate any credential that may have been exposed.
