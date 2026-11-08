#!/usr/bin/env bash
# ==============================================================================
# ADK Agentic RAG + Knowledge Graph — Automated Project Setup (Linux / macOS)
# Usage:
#   ./setup.sh            # Set up Python .venv, install backend + frontend deps, create .env
#   ./setup.sh --with-docs # Also install MkDocs Material documentation dependencies
#   ./setup.sh --start    # Run setup and immediately start Backend (8000) + Frontend (5173)
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

WITH_DOCS=false
AUTO_START=false

for arg in "$@"; do
  case "$arg" in
    --with-docs)
      WITH_DOCS=true
      ;;
    --start)
      AUTO_START=true
      ;;
    -h|--help)
      echo "Usage: ./setup.sh [--with-docs] [--start]"
      echo "  --with-docs  Install MkDocs Material documentation packages"
      echo "  --start      Launch FastAPI backend (port 8000) and Vite UI (port 5173) after setup"
      exit 0
      ;;
  esac
done

echo "======================================================================"
echo "  ADK Agentic RAG + Knowledge Graph — Environment Setup (v2.3.3)"
echo "======================================================================"

# ------------------------------------------------------------------------------
# 1. Verify Prerequisites (Python 3.10+, Node.js 18+, npm)
# ------------------------------------------------------------------------------
echo ""
echo "[1/5] Checking system prerequisites..."

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "ERROR: Python 3.10+ is not installed. Please install Python 3.10 or newer."
  exit 1
fi

PY_VERSION="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "  ✓ Found Python $PY_VERSION ($PYTHON_BIN)"

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js (v18+) is not installed. Please install Node.js from https://nodejs.org/"
  exit 1
fi
echo "  ✓ Found Node.js $(node -v)"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is not installed. Please install npm."
  exit 1
fi
echo "  ✓ Found npm v$(npm -v)"

# ------------------------------------------------------------------------------
# 2. Create & Configure Python Virtual Environment (.venv)
# ------------------------------------------------------------------------------
echo ""
echo "[2/5] Setting up Python virtual environment (.venv)..."

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
  echo "  ✓ Created virtual environment at $ROOT_DIR/.venv"
else
  echo "  ✓ Existing virtual environment found at $ROOT_DIR/.venv"
fi

VENV_PY="$ROOT_DIR/.venv/bin/python"
VENV_PIP="$ROOT_DIR/.venv/bin/pip"

"$VENV_PY" -m pip install --upgrade pip

# ------------------------------------------------------------------------------
# 3. Install Backend Dependencies (requirements.txt + CPU PyTorch for Docling)
# ------------------------------------------------------------------------------
echo ""
echo "[3/5] Installing Python backend dependencies..."

# Install lightweight CPU torch/torchvision first on Linux so Docling does not pull multi-GB CUDA wheels
if [ "$(uname -s)" = "Linux" ]; then
  if ! "$VENV_PY" -c "import torch" >/dev/null 2>&1; then
    echo "  → Installing CPU PyTorch runtime for Docling layout/table extraction..."
    "$VENV_PIP" install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  fi
fi

"$VENV_PIP" install -r requirements.txt

if [ "$WITH_DOCS" = true ]; then
  echo "  → Installing MkDocs Material documentation dependencies..."
  "$VENV_PIP" install mkdocs mkdocs-material pymdown-extensions
fi

echo "  ✓ Backend Python packages installed."

# ------------------------------------------------------------------------------
# 4. Install React + Vite Frontend Dependencies
# ------------------------------------------------------------------------------
echo ""
echo "[4/5] Installing React + Vite frontend dependencies (frontend/)..."

npm --prefix frontend install
echo "  ✓ Frontend npm packages installed."

# ------------------------------------------------------------------------------
# 5. Initialize .env Configuration
# ------------------------------------------------------------------------------
echo ""
echo "[5/5] Checking environment configuration (.env)..."

if [ ! -f ".env" ]; then
  cp .env.example .env
  RAND_SECRET="$("$VENV_PY" -c 'import secrets; print(secrets.token_hex(32))')"
  if grep -q "JWT_SECRET_KEY=replace-with-a-long-random-secret-string" .env; then
    "$VENV_PY" -c "
p = '.env'
txt = open(p).read().replace('replace-with-a-long-random-secret-string', '$RAND_SECRET')
open(p, 'w').write(txt)
"
  fi
  echo "  ✓ Created .env from .env.example (with auto-generated JWT_SECRET_KEY)."
  echo "  ! IMPORTANT: Update GOOGLE_API_KEY, DATABASE_URL, and NEO4J_* in .env before running."
else
  echo "  ✓ Existing .env file found (preserved without overwriting)."
fi

echo ""
echo "======================================================================"
echo "  Setup Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Configure your credentials in .env (GOOGLE_API_KEY, DATABASE_URL, NEO4J_URI, NEO4J_PASSWORD)"
echo "  2. Start the FastAPI backend (Terminal 1):"
echo "       source .venv/bin/activate && uvicorn app.api:app --reload --port 8000"
echo "  3. Start the React + Vite frontend (Terminal 2):"
echo "       npm --prefix frontend run dev"
echo "  4. Open http://localhost:5173 in your browser."
echo ""

if [ "$AUTO_START" = true ]; then
  echo "Starting FastAPI backend (port 8000) and Vite frontend (port 5173)..."
  trap 'kill 0' INT TERM EXIT
  "$ROOT_DIR/.venv/bin/uvicorn" app.api:app --reload --port 8000 &
  npm --prefix frontend run dev &
  wait
fi
