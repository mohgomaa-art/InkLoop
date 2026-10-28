import json
import sys
import os
from pathlib import Path
import httpx
from openai import OpenAI

# Ensure backend can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.config import InkLoopConfig

def run_smoke_test():
    config = InkLoopConfig.load()
    output_path = Path(__file__).parent.parent / "runs" / "m0_api_smoke_test.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "timestamp": "2026-10-29T02:30:00Z",
        "endpoint": config.meta_base_url,
        "credentials_configured": config.has_credentials,
        "masked_key": config.mask_key(),
        "status": "UNKNOWN",
        "details": {}
    }

    print(f"[*] Probing Meta Model API at: {config.meta_base_url}")
    print(f"[*] Credentials configured: {config.has_credentials} ({config.mask_key()})")

    if not config.has_credentials:
        print("[!] No META_API_KEY found in environment or .env file.")
        print("[*] Probing public endpoint response...")
        try:
            resp = httpx.get(f"{config.meta_base_url}/models", timeout=10)
            result["status"] = "BLOCKED"
            result["details"] = {
                "error": "Missing API Key",
                "http_status": resp.status_code,
                "response_body": resp.json() if resp.status_code in [400, 401, 403] else resp.text[:200],
                "x_request_id": resp.headers.get("x-request-id"),
                "x_route": resp.headers.get("x-route")
            }
            print(f"[!] HTTP {resp.status_code}: {result['details']['response_body']}")
        except Exception as e:
            result["status"] = "BLOCKED"
            result["details"] = {"error": f"Connection error: {str(e)}"}
            print(f"[!] Connection failed: {e}")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"[+] Smoke test report written to: {output_path}")
        return result

    # When credentials are provided:
    client = OpenAI(base_url=config.meta_base_url, api_key=config.meta_api_key)
    try:
        print("[*] Calling client.models.list()...")
        models = client.models.list()
        model_ids = [m.id for m in models.data]
        result["status"] = "VERIFIED"
        result["details"]["models"] = model_ids
        print(f"[+] Models available ({len(model_ids)}): {model_ids}")
    except Exception as e:
        result["status"] = "FAILED"
        result["details"]["model_list_error"] = str(e)
        print(f"[!] models.list() failed: {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result

if __name__ == "__main__":
    run_smoke_test()
