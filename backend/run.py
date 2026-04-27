import uvicorn

def main():
    uvicorn.run(
        "app.main:app",   # your FastAPI app path
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    )

if __name__ == "__main__":
    main()