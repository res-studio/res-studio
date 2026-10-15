# Changelog

## [0.1.0-beta.1] - 2026-10-15

First public beta candidate of RES Studio, a local-first tool for authorized web asset inspection.

### Added
- Public HTML, CSS and JavaScript capture with bounded quick and deep scans.
- Optional DNS-pinned `curl_cffi` transport with automatic fallback on selected HTTP/connection errors.
- Offline HAR import and optional isolated Chromium workflow.
- JavaScript inspection, optional analysis engines, local MCP integration and exports.
- Regression, security, integration, dependency and live-storefront CI checks.

### Known limitations
- Sites may load additional resources dynamically that static capture cannot retrieve.
- Quick and deep scans have configured asset, file-size and total-byte limits; a truncated result is not a complete capture.
- A successful HTTP scan does not guarantee complete reconstruction of a website.
- Beta is intended for local, authorized use; the API must not be publicly exposed.
