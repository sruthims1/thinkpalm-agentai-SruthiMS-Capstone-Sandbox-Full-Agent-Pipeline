@echo off 
cd /d "C:\Users\sruthi.m.DC\OneDrive - Thinkpalm Technologies Ltd\Documents\Agentic AI Batch 2\Marine QA Pilot\" 
set PYTHONPATH=C:\Users\sruthi.m.DC\OneDrive - Thinkpalm Technologies Ltd\Documents\Agentic AI Batch 2\Marine QA Pilot\src 
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload 
