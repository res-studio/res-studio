# Security policy

RES Studio is designed for **local, authorized analysis**, not as a public multi-tenant scanning service.

## Supported deployment

- Bind the API to `127.0.0.1` only. Do not expose port 8765 on a public interface.
- Analyze only sites you own or are authorized to inspect.
- Run the tool as a non-root user with limited permissions; do not provide cloud credentials to the process.
- Treat downloaded JavaScript, HTML and CSS as untrusted data.
- Update Python, Node, Chromium and dependencies regularly.

## Known limitations

The HTTP scanner validates public DNS answers and uses a pinned-IP connection adapter for Requests 2.32+. This has regression coverage, but is not a substitute for an operating-system egress firewall; review proxy, TLS, redirects, IPv6, and library upgrades before any public deployment. The dynamic API now requires an explicit isolated Docker worker. The worker runs with `--network none`, no added capabilities, a read-only filesystem, no-new-privileges, and CPU/memory/PID limits. It has no Docker socket mount. Browser HTTP requests are brokered over standard input/output by the parent, which validates URLs and fetches through the pinned-IP HTTP client. Set `RES_ENABLE_ISOLATED_CHROMIUM=1` only after building the worker image. Do not expose the API to untrusted remote users. This isolates Chromium network egress, not all browser escape vulnerabilities; keep Docker, the kernel and Chromium updated.

## Reporting

Do not publish a working exploit in a public issue. Contact the repository owner privately using GitHub's private vulnerability reporting feature if enabled. Otherwise request a private contact channel without disclosing exploit details.

Security fixes require targeted regression tests and GitHub Actions verification before release.

## Responsible use and disclaimer

RES Studio is a **software analysis and decompilation aid**, not a hosting service or the operator of any website being inspected. It helps users inspect accessible HTML, CSS, JavaScript and related assets; it does not grant permission to copy, republish, impersonate or commercially exploit third-party websites.

**You are responsible for the targets you inspect and how you use the results.** Only analyze websites and assets you own or are authorized to inspect. Respect applicable laws, contracts, intellectual-property rights, privacy and website terms. The RES Studio contributors do not endorse unauthorized reverse engineering, and, to the extent permitted by applicable law, disclaim responsibility for independent misuse of the tool or resulting websites. This notice does not eliminate liability that cannot legally be excluded.

The software is supplied **“AS IS”**, without warranties, as stated in the [MIT License](LICENSE).

