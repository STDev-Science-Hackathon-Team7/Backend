from datetime import datetime, timedelta
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Query
from app.config import settings
import os
import shutil
import uuid
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.star_counter import star_counter  
from pymongo import MongoClient

router = APIRouter(
    prefix="/api",
    tags=["별 관측 API"],
    responses={404: {"description": "Not found"}},
)

client = MongoClient("mongodb://localhost:27017/")
db = client["counting_stars"]
observations_collection = db["observations"]  

@router.post("/upload", summary="사용자 입력 API")
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
        image_url = f"https://counting-stars.info/upload/{unique_filename}"

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
            "image_url": image_url,
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
        raise HTTPException(status_code=500, detail=f"별 개수 분석 오류: {str(e)}")

# JSON 직렬화를 위한 ObjectId 처리 
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# 응답 모델 정의
class ObservationModel(BaseModel):
    id: str = Field(default_factory=str, alias="_id")
    image_analysis: dict
    user_input: dict
    latitude: float
    longitude: float
    image_url: Optional[str] = None
    uploaded_at: datetime
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }

# 응답 리스트 모델
class ObservationsListModel(BaseModel):
    observations: List[ObservationModel]
    total: int
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }

@router.get("/observations", response_model=ObservationsListModel, summary="모든 관측 데이터 조회 API")
async def get_all_observations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    min_stars: Optional[int] = Query(None, ge=0),
    max_stars: Optional[int] = Query(None, ge=0),
    category: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    distance: Optional[float] = Query(None, ge=0),  # km 단위
    days: Optional[int] = Query(None, ge=1)
):
    """
    모든 관측 데이터를 조회하는 API

    - **skip**: 건너뛸 결과 수 (페이지네이션용)
    - **limit**: 반환할 최대 결과 수
    - **min_stars**: 최소 별 개수 필터
    - **max_stars**: 최대 별 개수 필터
    - **category**: 별 품질 카테고리 필터 (레벨1~4)
    - **lat**: 중심 위도 (거리 기반 검색 시)
    - **lon**: 중심 경도 (거리 기반 검색 시)
    - **distance**: 검색 반경 (km)
    - **days**: 지정된 일수 이내의 데이터만 조회
    """
    try:
        query = {}
    
        if min_stars is not None or max_stars is not None:
            query["image_analysis.star_count"] = {}
            if min_stars is not None:
                query["image_analysis.star_count"]["$gte"] = min_stars
            if max_stars is not None:
                query["image_analysis.star_count"]["$lte"] = max_stars
        
        if category:
            query["image_analysis.star_category"] = category
        
        if days:
            date_threshold = datetime.now() - timedelta(days=days)
            query["uploaded_at"] = {"$gte": date_threshold}
        
        total = observations_collection.count_documents(query)
        cursor = observations_collection.find(query).sort("uploaded_at", -1).skip(skip).limit(limit)
        
        observations = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            observations.append(doc)
        
        if lat is not None and lon is not None and distance is not None:
            from math import radians, cos, sin, asin, sqrt
            
            def haversine(lat1, lon1, lat2, lon2):
                """
                두 지점 간 거리 계산 (km)
                """
                lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                r = 6371 
                return c * r
            
            filtered_observations = []
            for obs in observations:
                obs_lat = obs["latitude"]
                obs_lon = obs["longitude"]
                dist = haversine(lat, lon, obs_lat, obs_lon)
                obs["distance"] = round(dist, 2)
                if dist <= distance:
                    filtered_observations.append(obs)
            
            observations = filtered_observations
            total = len(filtered_observations)
        
        return {"observations": observations, "total": total}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 조회 중 오류 발생: {str(e)}")

@router.get("/observations/{observation_id}", response_model=ObservationModel, summary="특정 위치의 관측 데이터 조회 API")
async def get_observation_by_id(observation_id: str):
    """
    특정 ID로 단일 관측 데이터를 조회하는 API
    """
    try:
        try:
            obj_id = ObjectId(observation_id)
        except Exception:
            raise HTTPException(status_code=400, detail="유효하지 않은 ID 형식입니다")
    
        observation = observations_collection.find_one({"_id": obj_id})
        
        if observation:
            observation["_id"] = str(observation["_id"])
            return observation
        else:
            raise HTTPException(status_code=404, detail="해당 관측 데이터를 찾을 수 없습니다")
    
    except HTTPException:
        raise  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 조회 중 오류 발생: {str(e)}")

# 이미지 분석 API - 별 개수만 분석하고 임시 저장
@router.post("/analyze-image", summary="밤하늘 이미지 분석")
async def analyze_image(
    image: UploadFile = File(...),
):
    """
    밤하늘 사진을 분석하여 별 개수와 관측 품질을 판단합니다.
    분석 결과를 확인 후 최종 업로드 여부를 결정할 수 있습니다.
    """
    file_extension = os.path.splitext(image.filename)[1]
    if file_extension.lower() not in ['.jpg', '.jpeg', '.png']:
        raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다. JPG 또는 PNG 이미지만 업로드 가능합니다.")

    # 임시 파일명 생성 (24시간 후 자동 삭제되는 임시 파일로 가정)
    temp_id = uuid.uuid4()
    unique_filename = f"temp_{temp_id}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    try:
        # 이미지 분석 수행
        analysis_result = star_counter.count_stars(file_path)
        
        # 분석 결과와 임시 파일 정보 반환
        return {
            "temp_id": str(temp_id),
            "filename": unique_filename,
            "image_analysis": {
                "star_count": analysis_result.get("star_count", 0),
                "star_category": analysis_result.get("star_category"),
                "ui_message": analysis_result.get("ui_message"),
            }
        }
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"별 개수 분석 오류: {str(e)}")

# 최종 업로드 API - 분석 결과를 확인한 후 최종 저장
@router.post("/confirm-upload", summary="관측 데이터 최종 업로드")
async def confirm_upload(
    temp_id: str = Form(..., description="임시 분석 ID"),
    latitude: float = Form(..., description="위도"),
    longitude: float = Form(..., description="경도"),
    title: str = Form(..., description="게시글 제목"),
    content: str = Form(..., description="게시글 내용"),
    manual_star_count_range: str = Form(..., description="사용자 직접 입력 별 개수 범위"),
):
    """
    분석한 이미지의 최종 업로드를 확정합니다.
    """
    # 임시 파일 확인
    temp_filename = f"temp_{temp_id}"
    found_files = [f for f in os.listdir(settings.UPLOAD_DIR) if f.startswith(temp_filename)]
    
    if not found_files:
        raise HTTPException(status_code=404, detail="임시 파일을 찾을 수 없습니다. 다시 업로드해주세요.")
    
    temp_file_path = os.path.join(settings.UPLOAD_DIR, found_files[0])
    
    try:
        # 별 개수 분석 결과 다시 가져오기
        analysis_result = star_counter.count_stars(temp_file_path)
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
        
        # 최종 파일명 생성 및 임시 파일 이동
        unique_filename = f"{uuid.uuid4()}{os.path.splitext(found_files[0])[1]}"
        final_file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        image_url = f"https://counting-stars.info/upload/{temp_filename}"
        
        # 임시 파일을 최종 파일로 이동
        os.rename(temp_file_path, final_file_path)
        
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
            "image_url": image_url,
            "filename": unique_filename,
            "uploaded_at": datetime.now()
        }
        
        inserted_result = observations_collection.insert_one(observation_data)
        inserted_id = str(inserted_result.inserted_id)
        
        final_result = observation_data
        final_result["_id"] = inserted_id
        return final_result
        
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"데이터 저장 오류: {str(e)}")