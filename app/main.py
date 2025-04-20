from fastapi import FastAPI
from app.routes.summarization import router as summarization_router
from app.core.config import settings



app = FastAPI(
    title="FiXiT Summarizer API",
    description="API for summarizing text asynchronously using AI",
    version="1.0.0"
)

# Include routers
app.include_router(summarization_router, prefix="/api/v1", tags=["Summarization"])

@app.get("/", tags=["Health Check"])
async def read_root():
    return {"message": "FiXiT Summarizer API is running!"}
