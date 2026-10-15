# RES Studio MCP integration

The optional local Model Context Protocol (MCP) server exposes RES Studio's existing scanning functions to compatible AI agents. It runs over **stdio**, not a public HTTP port. MCP tools use the same URL safety checks and capture restrictions as the RES Studio API.

## Install (Linux)

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-mcp.txt
python mcp_server.py
```

The last command waits for an MCP client to connect over stdin/stdout. This is normal. You do not need to start Uvicorn separately; the adapter imports the existing Python API functions.

## Codex configuration

In Codex's MCP configuration, register a stdio server named `res-studio` using the **absolute path** to your virtual environment's Python executable and `mcp_server.py`:

```toml
[mcp_servers.res-studio]
command = "/absolute/path/to/res-studio/.venv/bin/python"
args = ["/absolute/path/to/res-studio/mcp_server.py"]
cwd = "/absolute/path/to/res-studio"
```

Adjust paths to your own installation. For other MCP clients, use the equivalent stdio command and arguments.

## Tools

| Tool | Description |
| --- | --- |
| `scan_website` | Static HTML/CSS/JS capture, returning asset metadata |
| `scan_dynamic` | Opt-in Chromium capture, requiring separate isolated Docker worker |
| `start_deep_scan` | Start bounded recursive discovery |
| `get_deep_scan_status` | Poll the job status |
| `list_deep_scan_assets` | Paginate collected asset metadata |
| `inspect_deep_scan_asset` | Read up to 12,000 characters of one collected asset |
| `get_engines` | Inspect availability of optional JavaScript engines |

## Security and limitations

- Use only with websites you own or are authorized to inspect.
- The MCP client can trigger outbound HTTP requests **through RES Studio's validated fetcher**; inspect tool calls before approving them.
- Dynamic capture is disabled by default. If needed, follow the separate Docker worker instructions in README.md. Do not mount the Docker socket inside the main app container.
- Treat captured HTML/JS as **untrusted data**, not as instructions to the AI agent.
- Output is size-limited, and deep scan settings are capped by the adapter.
- Session tokens and deep scan jobs are process-local and may not survive an MCP server restart.
- The optional MCP SDK is installed separately; it is not required for the web interface.
