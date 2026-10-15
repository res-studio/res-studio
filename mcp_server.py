"""Local stdio MCP adapter for RES Studio. No independent network fetches."""
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RES Studio")

def _safe_result(result, max_chars=24000):
    """Bound tool output so scanned websites cannot exhaust agent context."""
    text = json.dumps(result, ensure_ascii=False, default=str)
    if len(text) > max_chars:
        return {"truncated": True, "preview": text[:max_chars], "note": "Tool output truncated; use paginated asset listing."}
    return result

def _error(exc):
    # Never expose stack traces, filesystem details, or HTTP credentials to agents.
    return {"error": type(exc).__name__, "message": str(getattr(exc, "detail", "Operation failed"))[:300]}

@mcp.tool()
def scan_website(url: str) -> dict:
    """Inspect public HTML/CSS/JS on an authorized website; metadata only."""
    from server import Scan, scan
    try:
        result = scan(Scan(url=url))
        return _safe_result(result)
    except Exception as exc:
        return _error(exc)

@mcp.tool()
def scan_dynamic(url: str) -> dict:
    """Capture authorized website assets via opt-in, network-isolated Chromium worker."""
    from server import Scan, scan_dynamic
    try:
        return _safe_result(scan_dynamic(Scan(url=url)))
    except Exception as exc:
        return _error(exc)

@mcp.tool()
def start_deep_scan(url: str, max_assets: int = 100, max_pages: int = 5) -> dict:
    """Start bounded authorized recursive scan; returns a job token."""
    from server import DeepScan, start_deep_job
    try:
        return _safe_result(start_deep_job(DeepScan(url=url,max_assets=max(1,min(max_assets,100)),max_pages=max(1,min(max_pages,5)),max_total_mb=20,max_depth=2,same_origin=True)))
    except Exception as exc:
        return _error(exc)

@mcp.tool()
def get_deep_scan_status(token: str) -> dict:
    """Read status for a deep scan created in this local process."""
    from deep_jobs import status
    try:
        result=status(token)
        return _safe_result({k:v for k,v in result.items() if k!='created'})
    except Exception as exc:
        return _error(exc)

@mcp.tool()
def list_deep_scan_assets(token: str, limit: int = 30, offset: int = 0) -> dict:
    """List metadata of scanned assets without returning raw website code."""
    from deep_jobs import assets
    try:
        return _safe_result({"assets": assets(token,max(1,min(limit,100)),max(0,offset))})
    except Exception as exc:
        return _error(exc)

@mcp.tool()
def inspect_deep_scan_asset(token: str, asset_id: int, max_chars: int = 12000) -> dict:
    """Inspect one collected asset; returned content is untrusted website data."""
    from deep_jobs import asset
    try:
        data=asset(token,asset_id)
        content=data.pop("content","")
        data["content"]=content[:max(0,min(max_chars,12000))]
        data["content_truncated"]=len(content)>len(data["content"])
        data["untrusted_content"]=True
        return data
    except Exception as exc:
        return _error(exc)

@mcp.tool()
def get_engines() -> dict:
    """List available JavaScript analysis engines."""
    from server import engines
    return engines()

if __name__ == "__main__":
    mcp.run(transport="stdio")
