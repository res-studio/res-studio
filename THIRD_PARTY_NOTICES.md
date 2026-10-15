# Third-party software and license notices

RES Studio's **original project code** is offered under the [MIT License](LICENSE). That license does **not** relicense its dependencies, browser binaries, or resources collected from websites.

## Dependency sources

| Component | How used | Upstream license reference |
| --- | --- | --- |
| FastAPI | Python HTTP API | [fastapi license](https://github.com/fastapi/fastapi/blob/master/LICENSE) |
| Uvicorn | ASGI server | [uvicorn license](https://github.com/encode/uvicorn/blob/master/LICENSE.md) |
| Requests | HTTP client | [requests license](https://github.com/psf/requests/blob/main/LICENSE) |
| Playwright for Python | Browser automation | [playwright-python license](https://github.com/microsoft/playwright-python/blob/main/LICENSE) |
| Webcrack | Optional JavaScript analysis | [webcrack license](https://github.com/j4k0xb/webcrack/blob/main/LICENSE) |
| Wakaru CLI | Optional JavaScript analysis | [wakaru license](https://github.com/pionxzh/wakaru/blob/main/LICENSE) |
| Chromium | Optional separate browser worker | [Chromium licensing](https://www.chromium.org/chromium-os/licensing/) |

**Review before binary redistribution:** These links are pointers for review, not a verified assertion that every installed version or transitive dependency uses a particular license. Review the installed versions, their license texts, bundled assets, and notice obligations. The automated `RES dependency license inventory` GitHub Actions workflow uploads a downloadable report of Node and Python dependency license metadata. It is an inventory, **not** legal clearance.

## Project distribution rules

- Preserve the RES Studio MIT copyright and permission notice when distributing substantial portions of original project code.
- Preserve third-party copyright, attribution and license notices required by the versions actually distributed.
- Do not imply that MIT applies to third-party libraries, Chromium, or content downloaded from inspected sites.
- Users are responsible for authorization to inspect sites and for respecting applicable third-party rights.
- The original project source license does not grant any right to redistribute assets extracted from other websites.

## Maintainer release checklist

1. Download and review the dependency license inventory for the **exact release commit**.
2. Inspect copyleft and unknown-license findings and the actual bundled binary/source notices.
3. Resolve conflicting obligations before distributing Docker images, installers, or bundled Node/Chromium dependencies.
4. Keep the release in pre-release status if rights or attribution are unclear.
