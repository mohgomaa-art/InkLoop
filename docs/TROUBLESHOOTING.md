# InkLoop Troubleshooting Guide

This guide documents issues encountered during environment setup, testing, and execution, along with their verified solutions.

---

## 1. API Key Not Configured / Live Generation Blocked

### Symptom
The server starts, but the interface shows `MODEL_API_KEY is not configured` and live generation requests fail.

### Root Cause
`MODEL_API_KEY` is not defined in the environment or `.env` file.

### Solution
1. Obtain an API key from **[https://dev.meta.ai](https://dev.meta.ai)**.
2. Copy `.env.example` to `.env` in the repository root.
3. Add your key:
   ```env
   MODEL_API_KEY=your_key_here
   ```
4. Restart the server. InkLoop will display `[*] Meta Model API configured: [SET - REDACTED]`.

---

## 2. Port Already in Use (Port 8000 or 5173)

### Symptom
`[ERROR] [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`

### Root Cause
Another instance of the server or a background development process is already bound to port 8000.

### Solution
Pass a different port via command-line arguments or environment variables:
```bash
python scripts/run_server.py --port 8080
```
Or set `PORT=8080` in your `.env` file.

---

## 3. Frontend Bundle Not Found

### Symptom
Opening `http://127.0.0.1:8000/` displays a 404 or backend API only.

### Root Cause
The production frontend distribution (`frontend/dist/index.html`) has not been compiled yet.

### Solution
Run the build command in the `frontend` directory:
```bash
cd frontend
npm install
npm run build
cd ..
```
The unified server will automatically detect and serve `frontend/dist/` on the root route.

---

## 4. Asset List Requires Project Scope (HTTP 422)

### Symptom
Calling `GET /api/v1/assets` returns `422 Unprocessable Content`.

### Root Cause
InkLoop enforces multi-tenant project isolation. Assets cannot be listed globally without project scoping.

### Solution
Provide the `project_id` query parameter with every request:
```bash
curl "http://127.0.0.1:8000/api/v1/assets?project_id=default_project"
```

---

## 5. Speech Bubble Placement Overlaps Character Faces

### Symptom
In complex panels, speech balloons cover character eyes or faces.

### Root Cause
In offline/unconfigured mode, face segmentation coordinates default to center bounds.

### Solution
With a configured `MODEL_API_KEY`, InkLoop automatically invokes `sam-3.1` to detect precise subject contours. The deterministic `placement_engine.py` assigns high cost penalties to character faces and routes bubbles into free gutters and panel margins.
