#!/bin/sh
export GOOGLE_APPLICATION_CREDENTIALS=sync-test.json
python src/main.py --json-log-dir=./temp-log-dir/ --project=arxiv-development 
