#!/usr/bin/env python3
"""Start the sonarsniffer FastAPI app (dev mode with uvicorn)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Ensure local package import works
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("SONARS_PORT", "8081"))
    host = os.environ.get("SONARS_HOST", "127.0.0.1")
    print(f"Starting SonarSniffer web API at http://{host}:{port}")
    uvicorn.run("sonarsniffer.web:app", host=host, port=port, log_level="info")
