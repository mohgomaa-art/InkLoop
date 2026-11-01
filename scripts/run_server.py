"""
Convenience entry point to launch the InkLoop Unified API Server and Frontend.
Usage:
    python scripts/run_server.py [--host 127.0.0.1] [--port 8000] [--reload]
"""
import sys
from pathlib import Path
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import InkLoopConfig

if __name__ == "__main__":
    import argparse
    config = InkLoopConfig.load()

    parser = argparse.ArgumentParser(description="Run InkLoop Unified API & Frontend Server")
    parser.add_argument("--host", default=config.host, help=f"Bind host (default: {config.host})")
    parser.add_argument("--port", type=int, default=config.port, help=f"Bind port (default: {config.port})")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload on code change")
    args = parser.parse_args()

    print("=" * 72)
    print("                     INKLOOP PRODUCTION STUDIO")
    print("         Research-Driven Manga, Manhwa and Comics Production")
    print("=" * 72)

    if not config.has_credentials:
        print("\n[!] FIRST-RUN NOTICE: MODEL_API_KEY is not configured.")
        print("    To enable live Meta AI model generation and judgment:")
        print("    1. Obtain a Meta Model API key at: https://dev.meta.ai")
        print("    2. Set MODEL_API_KEY in your .env file or environment.")
        print("    InkLoop will start and operate in local offline/simulation mode.\n")
    else:
        print(f"\n[*] Meta Model API configured: {config.mask_key()}")
        print(f"[*] Base URL: {config.meta_base_url}\n")

    print(f"[*] Studio Interface: http://{args.host}:{args.port}/")
    print(f"[*] API Documentation: http://{args.host}:{args.port}/api/docs")
    print(f"[*] Data Directory:    {config.data_dir}\n")

    uvicorn.run("app.api.server:app", host=args.host, port=args.port, reload=args.reload)
