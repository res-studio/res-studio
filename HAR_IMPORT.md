# Offline HAR import

RES Studio can import public HTML, CSS and JavaScript response bodies from a HAR capture when direct scanning returns an HTTP error. This is an **offline** import: the API never replays HAR requests.

## Usage

1. Open a site you are authorized to inspect in Chrome/Brave.
2. Open Developer Tools > Network, enable Preserve log, and reload the page.
3. Export the Network log as HAR **with content**. Be careful: HAR files can include authentication cookies, authorization headers, tokens, personal information and private URLs. Never upload a HAR to a third-party service.
4. On your local RES Studio instance, run:

```bash
curl -X POST -H 'Content-Type: application/json' --data-binary @capture.har http://127.0.0.1:8000/api/import-har
```

If RES_API_KEY is configured, add the x-api-key header. The response includes a token for the existing asset endpoints and ZIP export workflow.

Only response bodies with HTML, CSS or JavaScript MIME types and successful HTTP statuses are imported. The importer discards request headers, cookies, authorization details, and request bodies rather than storing them. Sensitive information **inside response bodies** is not automatically removed. Use only captures you are authorized to process and avoid private data.

Limits: 16 MB HAR input, 1000 entries inspected, 35 imported assets, 2 MB per asset, 12 MB total. Entries without saved response content are skipped. This does not circumvent server restrictions or reconstruct inaccessible backend source.
