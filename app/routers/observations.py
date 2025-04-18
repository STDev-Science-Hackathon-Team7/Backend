import os
import shutil
import uuid
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.config import settings

router = APIRouter(
    prefix="/api",
    tags=["observations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/upload")
async def upload(
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: UploadFile = File(...)
):
    """
    밤하늘 사진 업로드 및 별 개수 분석 API
    """
    print(f"위도 {latitude}, 경도 {longitude} 확인")
    # 파일 확장자 확인
    file_extension = os.path.splitext(image.filename)[1]
    if file_extension.lower() not in ['.jpg', '.jpeg', '.png']:
        raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다. JPG 또는 PNG 이미지만 업로드 가능합니다.")
        
    # 고유 파일명 생성 및 저장
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
    # 파일 저장
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        print("파일이 저장되었습니다")
        
       
        