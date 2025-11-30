from routes.dashboard import router as dashboard_router
from fastapi import FastAPI
import uvicorn
import os

app = FastAPI(
    title="SiteAble API",
    description="API for SiteAble accessibility scanning service",
    version="1.0.0"
)
app.include_router(dashboard_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the SiteAble API"}

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("API_HOST", "0.0.0.0"), port=int(os.getenv("API_PORT", 8000)))