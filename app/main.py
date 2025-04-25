from app.services.database import close_db, connect_db, get_client
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
from pymongo import MongoClient

from app.config import settings
from app.routers import observations
from app.routers.observation_spots import router as spots_router

app = FastAPI(
    title=settings.APP_NAME,
    description="빛공해 데이터 기반 별 관측 장소 추천 및 밤하늘 사진 분석 API",
    title=settings.APP_NAME,
    description="빛공해 데이터 기반 별 관측 장소 추천 및 밤하늘 사진 분석 API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "서버 내부 오류가 발생했습니다.", "detail": str(exc)}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )

app.include_router(observations.router)
app.include_router(spots_router)
#app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/upload", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="upload")



@app.get("/")
async def root():
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("MongoDB 연결 성공!")
    except Exception as e:
        print(f"MongoDB 연결 실패: {e}")
    finally:
        if 'client' in locals() and client:
            client.close()
    return {"message": f"{settings.APP_NAME}"}
