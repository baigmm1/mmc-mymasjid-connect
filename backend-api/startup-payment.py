import uvicorn

if __name__ == "__main__":    
    uvicorn.run("src.main:app",
      host="127.0.0.1",
      port=8500,
      workers=2,
      timeout_keep_alive=120,
      access_log=True,
      log_level="info"
    )