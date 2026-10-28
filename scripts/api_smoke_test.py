import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Resolve project root relative to script location
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

DOTENV_PATH = PROJECT_ROOT / ".env"
if DOTENV_PATH.exists():
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    load_dotenv()

from app.config import InkLoopConfig

def run_smoke_test():
    runs_dir = PROJECT_ROOT / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    catalog_output = runs_dir / "m0_model_catalog.json"
    text_output = runs_dir / "m0_text_smoke_test.json"

    config = InkLoopConfig.load()
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=================================================================")
    print("INKLOOP M0: AUTHENTICATION REPAIR & LIVE API SMOKE TEST")
    print("=================================================================")
    print(f"[*] Target Endpoint: {config.meta_base_url}")
    print(f"[*] Project root .env present: {DOTENV_PATH.exists()}")
    print(f"[*] MODEL_API_KEY status: {config.mask_key()}")

    # Check if key is available
    if not config.has_credentials:
        print("\n[!] STOPPED: Missing credentials.")
        if not DOTENV_PATH.exists():
            print(f"[!] Action required: Create a '.env' file at '{DOTENV_PATH}'.")
        else:
            print("[!] Action required: Define 'MODEL_API_KEY=your_key_here' in '.env'.")
        print("[!] In accordance with Hackathon Integrity Rules, stopping before authenticated requests.")

        catalog_data = {
            "timestamp": now_iso,
            "endpoint": config.meta_base_url,
            "authentication_succeeded": False,
            "http_status": None,
            "models": [],
            "request_id": None,
            "error": "Missing credentials: .env is missing or MODEL_API_KEY is empty."
        }
        with open(catalog_output, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)
        print(f"[+] Sanitized status saved to: {catalog_output}")
        return

    # Step 3: Authenticated Request to GET /v1/models
    print("\n[*] Step 3: Verifying key safely via GET /v1/models...")
    headers = {
        "Authorization": f"Bearer {config.model_api_key}",
        "Content-Type": "application/json"
    }

    try:
        resp = httpx.get(f"{config.meta_base_url}/models", headers=headers, timeout=15.0)
        request_id = resp.headers.get("x-request-id")
        http_status = resp.status_code

        print(f"[*] Response HTTP Status: {http_status}")
        if request_id:
            print(f"[*] Request ID: {request_id}")

        if http_status == 200:
            data = resp.json()
            model_items = data.get("data", [])
            model_ids = [m.get("id") for m in model_items if isinstance(m, dict) and "id" in m]
            if not model_ids and isinstance(data, list):
                model_ids = [m.get("id") for m in data if isinstance(m, dict) and "id" in m]

            catalog_data = {
                "timestamp": now_iso,
                "endpoint": config.meta_base_url,
                "authentication_succeeded": True,
                "http_status": http_status,
                "models": model_ids,
                "request_id": request_id,
                "error": None
            }
            with open(catalog_output, "w", encoding="utf-8") as f:
                json.dump(catalog_data, f, indent=2)
            print(f"[+] Authentication succeeded. {len(model_ids)} models available.")
            print(f"[+] Model catalog saved to: {catalog_output}")

            # Step 4: One minimal text-generation request
            print("\n[*] Step 4: Checking for 'muse-spark-1.3' and testing one minimal text request...")
            target_model = "muse-spark-1.3"
            if target_model not in model_ids:
                print(f"[!] Target model '{target_model}' not found in catalog: {model_ids}")
                text_data = {
                    "timestamp": now_iso,
                    "target_model": target_model,
                    "model_available": False,
                    "available_alternatives": model_ids,
                    "response_status": None,
                    "request_id": None,
                    "output_received": None,
                    "reported_usage": None,
                    "error": f"Model '{target_model}' not listed in returned catalog."
                }
                with open(text_output, "w", encoding="utf-8") as f:
                    json.dump(text_data, f, indent=2)
                return

            payload = {
                "model": target_model,
                "reasoning": {"effort": "low"},
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Return exactly INKLOOP_API_OK and nothing else."
                            }
                        ]
                    }
                ],
                "max_output_tokens": 512
            }

            resp_text = httpx.post(f"{config.meta_base_url}/responses", headers=headers, json=payload, timeout=25.0)
            text_request_id = resp_text.headers.get("x-request-id")
            text_status = resp_text.status_code

            print(f"[*] Text Request HTTP Status: {text_status}")
            if text_request_id:
                print(f"[*] Text Request ID: {text_request_id}")

            output_text = None
            reported_usage = None
            error_msg = None

            if text_status == 200:
                text_json = resp_text.json()
                reported_usage = text_json.get("usage")
                # Parse output items in Responses API format
                outputs = text_json.get("output", [])
                for item in outputs:
                    if isinstance(item, dict) and item.get("type") == "message":
                        contents = item.get("content", [])
                        for c in contents:
                            if isinstance(c, dict) and c.get("type") == "output_text":
                                output_text = c.get("text", "").strip()
                if not output_text:
                    output_text = str(outputs)[:200]
                print(f"[+] Output text received: '{output_text}'")
                print(f"[+] Reported usage: {reported_usage}")
            else:
                try:
                    err_json = resp_text.json()
                    error_msg = err_json.get("error", {}).get("message") or str(err_json)
                except Exception:
                    error_msg = resp_text.text[:200]
                print(f"[!] Text request failed with status {text_status}: {error_msg}")

            text_data = {
                "timestamp": now_iso,
                "target_model": target_model,
                "model_available": True,
                "response_status": text_status,
                "request_id": text_request_id,
                "output_received": output_text,
                "reported_usage": reported_usage,
                "error": error_msg
            }
            with open(text_output, "w", encoding="utf-8") as f:
                json.dump(text_data, f, indent=2)
            print(f"[+] Text smoke test result saved to: {text_output}")

        else:
            try:
                err_data = resp.json().get("error", {})
                error_code = err_data.get("code", "unknown_error")
                error_message = err_data.get("message", "Authentication rejected by server.")
            except Exception:
                error_code = f"HTTP_{http_status}"
                error_message = resp.text[:200]

            catalog_data = {
                "timestamp": now_iso,
                "endpoint": config.meta_base_url,
                "authentication_succeeded": False,
                "http_status": http_status,
                "models": [],
                "request_id": request_id,
                "error": {
                    "code": error_code,
                    "message": error_message
                }
            }
            with open(catalog_output, "w", encoding="utf-8") as f:
                json.dump(catalog_data, f, indent=2)
            print(f"[!] Authentication FAILED ({http_status}): {error_code} - {error_message}")

    except Exception as e:
        error_str = f"Network or connection error: {type(e).__name__}"
        catalog_data = {
            "timestamp": now_iso,
            "endpoint": config.meta_base_url,
            "authentication_succeeded": False,
            "http_status": None,
            "models": [],
            "request_id": None,
            "error": error_str
        }
        with open(catalog_output, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)
        print(f"[!] Request failed: {error_str}")

if __name__ == "__main__":
    run_smoke_test()
