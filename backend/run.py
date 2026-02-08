"""
Startup script for the FastAPI backend with Windows event loop fix.

This script properly configures the async event loop for Windows before
starting uvicorn, which is required for psycopg3 async connections.
"""

import sys
import asyncio
import uvicorn

# Windows-specific fix for psycopg async compatibility
# Must be set BEFORE uvicorn creates its event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("[OK] Windows event loop policy set to SelectorEventLoop")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=7860,
        reload=True
    )
