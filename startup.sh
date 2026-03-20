#!/bin/bash
pip install -r /home/site/wwwroot/backend/requirements.txt
cd /home/site/wwwroot/backend
uvicorn main:app --host 0.0.0.0 --port 8000
