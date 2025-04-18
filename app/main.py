from fastapi import FastAPI

app = FastAPI(
    title="별 볼일 있는 지도 API",
    description="빛공해 데이터 기반 밤하늘 사진 분석 및 별 관측 장소 추천 서비스",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

@app.get("/")
async def root():
    return {"message": "Counting Stars API"}