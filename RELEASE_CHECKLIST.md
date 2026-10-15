# Release readiness checklist

This repository is public, but a public repository is not the same as a safe publicly hosted scanner.

## Required before a stable release

- [ ] Review tracked files and repository history for credentials and private data.
- [ ] Review direct and transitive dependency licenses (including indirect dependencies; unused direct deobfuscator was removed).
- [x] Select and add an MIT LICENSE for original RES Studio source code; third-party licenses remain separate.
- [x] Pin DNS resolution to validated public IP addresses in the static scanner, including redirects (Requests 2.32+ regression test).
- [x] Implement network-disconnected Docker Chromium worker (`--network none`) with parent-side validated fetch broker; Docker end-to-end CI passed at commit 813b7e22.
- [ ] Add regression tests for DNS rebinding, redirects and browser network access.
- [ ] Validate Docker build and document missing optional engines (release candidate CI gate passed at commit 813b7e22).
- [ ] Run all CI workflows on the exact release commit (dependency and license inventory checks included).
- [ ] Tag a pre-release before declaring a stable v1.0.0.

## Current safe-use boundary

Run locally on 127.0.0.1; do not expose the API to the public internet. Only inspect targets you own or have authorization to inspect. See SECURITY.md.

## Open-source licensing

The project's original code is now licensed under [MIT](LICENSE). Third-party dependencies and website resources retain their own rights; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The automated inventory is not a substitute for reviewing transitive license obligations before bundled distribution.

## Release-candidate implementation notes

- Deep scan background jobs store collected resources in SQLite and expose progress, pagination and cooperative cancellation. Jobs are not durable across process restarts; the SQLite data may remain but the in-memory task registry does not.
- Deep scan enforces a total wall-clock deadline between network requests, not a hard interrupt during a request.
- The user interface exposes deep scanning and cancellation; browser network isolation is available only through the opt-in Docker worker on a host with Docker installed.
- The optional direct `deobfuscator` dependency was removed from `package.json` because it was not imported by the engine. This does **not** establish compatibility of all remaining transitive licenses.
- The release-candidate CI workflow checks Python regression tests, Docker build, isolated Chromium smoke test, compose configuration and container smoke tests. A passing run does not replace a manual security audit or production load testing.
- **Do not merge or tag v1.0.0** until all remaining unchecked release blockers are resolved.
