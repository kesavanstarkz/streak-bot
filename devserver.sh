#!/bin/sh
source .venv/bin/activate
# Use port 8080 if $PORT is not set
python -u -m flask --app main run --debug --port ${PORT:-8080}
