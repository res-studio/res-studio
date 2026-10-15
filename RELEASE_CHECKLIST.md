# Release readiness checklist

This repository is public, but a public repository is not the same as a safe publicly hosted scanner.

## Required before a stable release

- [ ] Review tracked files and repository history for credentials and private data.
- [ ] Review direct and transitive dependency licenses (including the GPL-licensed deobfuscator).
- [ ] Select and add an appropriate project LICENSE; do not assume MIT covers third-party dependencies.
- [ ] Pin DNS resolution to validated public IP addresses in the static scanner, including redirects.
- [ ] Enforce network egress restrictions for Chromium with an isolated worker/container.
- [ ] Add regression tests for DNS rebinding, redirects and browser network access.
- [ ] Validate Docker build and document missing optional engines.
- [ ] Run all CI workflows on the exact release commit.
- [ ] Tag a pre-release before declaring a stable v1.0.0.

## Current safe-use boundary

Run locally on 127.0.0.1; do not expose the API to the public internet. Only inspect targets you own or have authorization to inspect. See SECURITY.md.

## Open-source licensing

The project's own license has **not yet been selected**. The README's older references to MIT are historical and not evidence that a LICENSE file exists. Review third-party license obligations before distribution decisions.
