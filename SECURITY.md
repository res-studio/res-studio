# Security policy

RES Studio is designed for **local, authorized analysis**, not as a public multi-tenant scanning service.

## Supported deployment

- Bind the API to `127.0.0.1` only. Do not expose port 8765 on a public interface.
- Analyze only sites you own or are authorized to inspect.
- Run the tool as a non-root user with limited permissions; do not provide cloud credentials to the process.
- Treat downloaded JavaScript, HTML and CSS as untrusted data.
- Update Python, Node, Chromium and dependencies regularly.

## Known limitations

The HTTP scanner validates DNS before connecting but does not pin the connection to the validated IP. DNS rebinding/TOCTOU remains a risk. Chromium navigation is filtered by Playwright routes, not isolated by a network firewall; browser subrequests and redirects require stronger controls. Dynamic scanning is **disabled by default**; setting `RES_ENABLE_UNISOLATED_BROWSER=1` opts into this known risk for local testing only. Neither path should be considered safe for unrestricted public deployment.

## Reporting

Do not publish a working exploit in a public issue. Contact the repository owner privately using GitHub's private vulnerability reporting feature if enabled. Otherwise request a private contact channel without disclosing exploit details.

Security fixes require targeted regression tests and GitHub Actions verification before release.
