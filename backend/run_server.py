"""Server launch script with optimized reload exclusions.

Excludes virtual environments and cache directories from watching to prevent
redundant Uvicorn reload loops.
"""

import sys
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        reload_excludes=["venv/*", "*.pyc", "__pycache__/*", "*.log", ".git/*"],
    )

