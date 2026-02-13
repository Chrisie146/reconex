#!/usr/bin/env bash
# Install system dependencies for python-magic
apt-get update && apt-get install -y libmagic1 libmagic-dev

# Install Python dependencies
pip install -r requirements.txt