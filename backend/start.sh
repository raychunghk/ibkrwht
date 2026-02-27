#!/usr/bin/env bash
# Start the FastAPI backend on port 3900
cd "$(dirname "$0")"
uvicorn main:app --host 0.0.0.0 --port 3900 --reload
