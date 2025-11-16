#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend" 
export NEO4J_URI=${NEO4J_URI:-bolt://localhost:7687}
export NEO4J_USER=${NEO4J_USER:-neo4j}
export NEO4J_PASS=${NEO4J_PASS:-intellidevice123}
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000