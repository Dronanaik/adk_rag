#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install required system dependencies if needed (e.g. for PyMuPDF or others)
# apt-get update && apt-get install -y ...

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
