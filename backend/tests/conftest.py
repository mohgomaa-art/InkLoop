"""
Global Pytest Configuration for InkLoop Test Suites.
Enforces offline deterministic execution with $0.00 spend across automated test runs.
"""
import os


# Apply this before test modules import app.config or construct provider
# adapters. Merely setting INKLOOP_OFFLINE_MODE in a fixture is too late for
# import-time singletons, and image adapters do not use the model client's
# offline planner switch. Tests that exercise provider boundaries must provide
# a fake client/transport and explicit monkeypatched credentials themselves.
os.environ["INKLOOP_OFFLINE_MODE"] = "1"
os.environ["MODEL_API_KEY"] = ""
os.environ["META_API_KEY"] = ""
