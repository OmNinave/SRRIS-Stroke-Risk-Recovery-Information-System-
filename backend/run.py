import uvicorn
import os

def main():
    # reload=True is for development only — disabled in production via env
    dev_mode = os.environ.get("SRRIS_DEV", "false").lower() == "true"
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8080,
        reload=dev_mode,
        reload_dirs=["app"] if dev_mode else None
    )

if __name__ == "__main__":
    main()