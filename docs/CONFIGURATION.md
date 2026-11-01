# InkLoop Configuration Reference

InkLoop centralizes configuration in `backend/app/config.py` and loads settings from environment variables or an optional project-root `.env` file via `python-dotenv`.

---

## Environment Variables

| Variable | Purpose | Default | Required |
| :--- | :--- | :--- | :--- |
| `MODEL_API_KEY` | Bearer token for authenticating calls to the Meta Model API. | `None` | **Yes** (for live generation; optional in offline mode) |
| `META_BASE_URL` | Base endpoint URL for the Meta Model API. | `https://api.meta.ai/v1` | No |
| `MUSE_IMAGE_MODEL` | Specialist Meta model for character sheets and comic panel image synthesis. | `muse-image-1.0` | No |
| `MUSE_SPARK_MODEL` | Meta reasoning model for script breakdown, panel planning, and visual judging. | `muse-spark-1.3` | No |
| `SAM_MODEL` | Meta Segment Anything Model for subject detection and speech-bubble obstacle avoidance. | `sam-3.1` | No |
| `GLOBAL_SPEND_CAP_USD` | Hard budget limit in USD. Requests stop when total spent reaches this ceiling. | `25.0` | No |
| `MAX_RETRIES_PER_PANEL` | Maximum retry attempts per panel when visual verification fails. | `2` | No |
| `MAX_CONCURRENT_REQUESTS`| Maximum parallel API requests to prevent rate limit spikes. | `2` | No |
| `HOST` | Bind host IP address for the FastAPI backend and unified server. | `127.0.0.1` | No |
| `PORT` | Bind port number for the unified server. | `8000` | No |
| `DATA_DIR` | Filesystem path for storing project data, databases, and rendered artifacts. | `./data` | No |

---

## Legacy Variable Support

For backward compatibility, if `MODEL_API_KEY` is not found, the configuration loader checks `META_API_KEY` before falling back to `None`.

---

## Secret Hygiene Invariant

InkLoop enforces strict secret protection:
- The API key is loaded into memory only.
- Diagnostic endpoints (`GET /api/v1/config/diagnostics`) output `[SET - REDACTED]` or `[NOT SET]`.
- API error responses and logs never serialize credentials or tokens.
