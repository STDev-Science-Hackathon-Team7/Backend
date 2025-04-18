from fastapi import FastAPI, HTTPException, Request, logger
from fastapi.responses import JSONResponse

app = FastAPI(
    title="별 볼일 있는 지도 API",
    description="빛공해 데이터 기반 밤하늘 사진 분석 및 별 관측 장소 추천 서비스",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"전역 예외 발생: {str(exc)}")
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

@app.get("/")
async def root():
    return {"message": "Counting Stars API"}

