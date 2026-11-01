"""
InkLoop Production API Server.
Assembles all specialist engine routers, enforces CORS boundaries,
handles errors deterministically, and mounts safe preview pathways.
"""
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_ROOT
from app.api.routers import (
    health,
    projects,
    generation,
    verification,
    assets,
    catalogue,
    execution,
    evaluation,
    canvas,
    agent,
    text,
    planning,
    editor,
    creative,
)

def create_app() -> FastAPI:
    application = FastAPI(
        title="InkLoop API",
        description="Unified REST API for InkLoop manga/manhwa/comics production system",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS configuration: Allow local Vite dev server and standard frontend origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Global Exception Handlers
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "ERR_6003_ENGINE_CRASH",
                "message": str(exc),
                "path": str(request.url.path),
            }
        )

    # Mount API routers under /api/v1
    application.include_router(health.router, prefix="/api/v1")
    application.include_router(projects.router, prefix="/api/v1")
    application.include_router(generation.router, prefix="/api/v1")
    application.include_router(verification.router, prefix="/api/v1")
    application.include_router(assets.router, prefix="/api/v1")
    application.include_router(catalogue.router, prefix="/api/v1")
    application.include_router(execution.router, prefix="/api/v1")
    application.include_router(evaluation.router, prefix="/api/v1")
    application.include_router(canvas.router, prefix="/api/v1")
    application.include_router(agent.router, prefix="/api/v1")
    application.include_router(text.router, prefix="/api/v1")
    application.include_router(planning.router, prefix="/api/v1")
    application.include_router(editor.router, prefix="/api/v1")
    application.include_router(creative.router, prefix="/api/v1")
    application.include_router(creative.universe_router, prefix="/api/v1")

    # Mount static preview directory for runs/m0_visual/reference safely
    ref_dir = PROJECT_ROOT / "runs" / "m0_visual" / "reference"
    if ref_dir.exists():
        application.mount("/static/reference", StaticFiles(directory=str(ref_dir)), name="reference")

    # Mount frontend production build if dist directory exists
    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    if frontend_dist.exists():
        from fastapi.responses import FileResponse
        dist_assets = frontend_dist / "assets"

        @application.get("/assets/{asset_file:path}")
        async def serve_dist_asset(asset_file: str):
            target = dist_assets / asset_file
            if target.is_file():
                return FileResponse(target)
            # Graceful fallback for stale build hashes from cached browser sessions
            if asset_file.endswith(".css"):
                css_files = list(dist_assets.glob("*.css"))
                if css_files:
                    return FileResponse(css_files[0], media_type="text/css")
            if asset_file.endswith(".js"):
                js_files = list(dist_assets.glob("*.js"))
                if js_files:
                    return FileResponse(js_files[0], media_type="application/javascript")
            return JSONResponse(status_code=404, content={"message": "Asset not found"})

        @application.get("/{full_path:path}")
        async def serve_spa_frontend(full_path: str):
            if full_path.startswith("api") or full_path.startswith("static"):
                return JSONResponse(status_code=404, content={"message": "Not found"})
            target_file = frontend_dist / full_path
            if target_file.is_file():
                if target_file.name == "index.html":
                    return FileResponse(
                        target_file,
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
                    )
                headers = {}
                media_type = None
                if target_file.suffix.lower() == ".webp":
                    media_type = "image/webp"
                if "quick-style-previews" in full_path:
                    headers["Cache-Control"] = "no-cache, must-revalidate"
                return FileResponse(target_file, media_type=media_type, headers=headers)
            # Stale chunk fallback at root
            if full_path.endswith(".css"):
                css_files = list(dist_assets.glob("*.css"))
                if css_files:
                    return FileResponse(css_files[0], media_type="text/css")
            if full_path.endswith(".js"):
                js_files = list(dist_assets.glob("*.js"))
                if js_files:
                    return FileResponse(
                        js_files[0],
                        media_type="application/javascript",
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
                    )
            return FileResponse(
                frontend_dist / "index.html",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )

    return application

app = create_app()
