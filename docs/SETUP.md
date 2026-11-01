# InkLoop Installation & Setup Guide

This guide covers setup and execution of InkLoop across Windows, macOS, and Linux.

---

## 1. Prerequisites

Versions verified in the InkLoop development and test suite:
- **Python**: `3.11` or higher (verified on Python `3.12.10`).
- **Node.js**: `18.0.0` or higher (verified on Node `v24.21.0`, npm `11.19.0`).
- **Operating System**: Windows 10/11, macOS 12+, or Ubuntu 22.04+ / Debian 12+.

---

## 2. Quick Setup Steps

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/InkLoop.git
cd InkLoop
```

### Step 2: Install Python Dependencies
Create and activate a virtual environment, then install requirements:

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 3: Install Frontend Dependencies
```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 3. Configuring Your Meta API Key

1. Obtain a Meta Model API key from: **[https://dev.meta.ai](https://dev.meta.ai)**
2. Copy the template to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` and set your key:
   ```env
   MODEL_API_KEY=your_actual_key_here
   ```
*(Note: InkLoop can run without a key in offline simulation mode for local layout testing).*

---

## 4. Starting the Studio

### On Windows
Run the launcher script:
```cmd
run.bat
```
Or with PowerShell:
```powershell
.\run.ps1
```

### On Linux / macOS
Make the launcher executable and run it:
```bash
chmod +x run.sh run_dev.sh
./run.sh
```

### Direct CLI Launch
You can also launch the unified server directly:
```bash
python scripts/run_server.py --host 127.0.0.1 --port 8000
```

The server hosts:
- **Studio Interface**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **REST API Documentation**: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

---

## 5. Running the Test Suite

Run the full pytest suite to verify local engine integrity:
```bash
pytest backend/tests -v
```
All 827 tests run offline with mock harness isolation.
