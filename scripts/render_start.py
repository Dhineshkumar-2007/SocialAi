#!/usr/bin/env python3
"""Render startup: skips expensive AI warmup on free tier to avoid gunicorn timeout."""
import os

# If AI_ENABLED is true but no GPU/RAM available (free Render), disable warmup
# but keep endpoint alive. Set SOCALAI_SKIP_WARMUP=1 via env.
os.environ.setdefault("SOCIALAI_SKIP_WARMUP", "1")

from app import app  # noqa: F401
