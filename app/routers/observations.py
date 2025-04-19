from datetime import datetime
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.config import settings
import os
import shutil
import uuid
from app.services.star_counter import star_counter
from pymongo import MongoClient

router = APIRouter(
    prefix="/api",
    tags=["observations"],
    responses={404: {"description": "Not found"}},
)

# MongoDB 클라이언트 생성 및 연결 
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]
observations_collection = db["observations"]  

@router.post("/upload")
async def upload(
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: UploadFile = File(...),
    title: str = Form(...),
    content: str = Form(...),
    manual_star_count_range: str = Form(...),
):
    """
    밤하늘 사진 업로드 및 별 개수 분석 API (MongoDB 저장)
    """
    print(f"위도 {latitude}, 경도 {longitude} 확인")
    print(f"글 제목: {title}, 글 내용: {content}")
    print(f"사용자 직접 입력 별 개수 범위: {manual_star_count_range}")

    file_extension = os.path.splitext(image.filename)[1]
    if file_extension.lower() not in ['.jpg', '.jpeg', '.png']:
        raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다. JPG 또는 PNG 이미지만 업로드 가능합니다.")

    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        print("파일이 저장되었습니다")

    try:
        analysis_result = star_counter.count_stars(file_path)
        star_count_from_analysis = analysis_result.get("star_count", 0)
        star_category_from_analysis = analysis_result.get("star_category")
        ui_message_from_analysis = analysis_result.get("ui_message")

        # 사용자 직접 입력 별 개수 범위 처리
        manual_star_count = None
        if manual_star_count_range == "0":
            manual_star_count = 0
        elif manual_star_count_range == "1~4":
            manual_star_count = 2
        elif manual_star_count_range == "5~8":
            manual_star_count = 6
        elif manual_star_count_range == "9+":
            manual_star_count = 9

        observation_data = {
            "image_analysis": {
                "star_count": star_count_from_analysis,
                "star_category": star_category_from_analysis,
                "ui_message": ui_message_from_analysis,
            },
            "user_input": {
                "title": title,
                "content": content,
                "manual_star_count_range": manual_star_count_range,
                "manual_star_count": manual_star_count,
            },
            "latitude": latitude,
            "longitude": longitude,
            "filename": unique_filename,
            "uploaded_at": datetime.now()  
        }

        # MongoDB에 데이터 삽입
        inserted_result = observations_collection.insert_one(observation_data)
        inserted_id = str(inserted_result.inserted_id)
        print(f"MongoDB에 데이터 저장 완료. ObjectId: {inserted_id}")

        # 저장된 데이터와 ObjectId를 포함한 응답 반환 
        final_result = observation_data
        final_result["_id"] = inserted_id
        return final_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"별 개수 분석 및 MongoDB 저장 오류: {str(e)}")

# 앱 종료 시 MongoDB 연결 닫기 
# @app.on_event("shutdown")
# def shutdown_event():
#     client.close()
#     print("MongoDB 연결 종료")