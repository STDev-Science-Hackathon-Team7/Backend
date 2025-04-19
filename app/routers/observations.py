from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from app.config import settings
import os
import shutil
import uuid
from app.services.star_counter import star_counter  

router = APIRouter(
    prefix="/api",
    tags=["observations"],
    responses={404: {"description": "Not found"}},
)

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
    밤하늘 사진 업로드 및 별 개수 분석 API
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

        # 사용자 직접 입력 별 개수 범위 처리 - 로직 바꿔야할수도 있음
        manual_star_count = None
        if manual_star_count_range == "0":
            manual_star_count = 0
        elif manual_star_count_range == "1~4":
            manual_star_count = 2  
        elif manual_star_count_range == "5~8":
            manual_star_count = 6
        elif manual_star_count_range == "9+":
            manual_star_count = 9 

        final_result = {
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
            # "filename": unique_filename,
        }

        return final_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"별 개수 분석 오류: {str(e)}")
    

# 프론트엔드로 전송할 응답 형식 예시
# {
#   "image_analysis": {
#     "star_count": 125,
#     "star_category": "좋음",
#     "ui_message": "오늘 125개의 별이 관측되었어요. 많은 별자리를 볼 수 있는 좋은 관측 조건이에요."
#   },
#   "user_input": {
#     "title": "오늘 밤 하늘 관측",
#     "content": "집 근처 공원에서 찍은 밤하늘 사진입니다. 별이 꽤 많이 보이네요!",
#     "manual_star_count_range": "100~299",
#     "manual_star_count": 199
#   },
#   "latitude": 37.5665,
#   "longitude": 126.9780,
# }