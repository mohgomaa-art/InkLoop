"""
InkLoop Unified API Server & REST Adapter.
Connects the frontend production interface to all backend services, engines,
registries, and governance subsystems without duplicate logic.
"""
from app.api.server import create_app, app

__all__ = ["create_app", "app"]
