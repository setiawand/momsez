#!/usr/bin/env python3
"""
Backend launcher within monorepo structure.
Keeps existing backend code in repository root `src/` while providing
an entrypoint under `apps/backend/src/`.
"""

import os
import sys
from pathlib import Path


def main():
    # Ensure repository root `src/` is importable
    this_file = Path(__file__).resolve()
    repo_root = this_file.parents[3]  # apps/backend/src -> apps/backend -> apps -> repo
    backend_src = repo_root / 'src'
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))

    # Optionally set working directory to repo root so relative paths (configs/, output/) work
    try:
        os.chdir(repo_root)
    except Exception:
        pass

    # Import the existing FastAPI app and serve via uvicorn
    from api_server import app  # type: ignore
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == '__main__':
    main()

