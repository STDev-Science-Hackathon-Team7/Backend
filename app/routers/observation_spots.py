from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
from datetime import datetime
from pymongo import MongoClient, GEOSPHERE
from bson import ObjectId
import math

client = MongoClient("mongodb://localhost:27017/")
db = client["counting_stars"]
spots_collection = db["observation_spots"]

# mongodb 지리적 인덱싱 설정 
try:
    spots_collection.create_index([("location", GEOSPHERE)])
except Exception:
    pass

router = APIRouter(
    prefix="/api",
    tags=["관측 명소 추천 API"],
    responses={404: {"description": "찾을 수 없음"}},
)

@router.get("/observation-spots", summary="관측 명소 목록")
async def get_observation_spots(
    skip: int = Query(0, ge=0, description="건너뛸 결과 수"),
    limit: int = Query(50, ge=1, le=100, description="반환할 최대 결과 수"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="최소 별 관측 품질 점수"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="최대 별 관측 품질 점수"),
    category: Optional[str] = Query(None, description="별 관측 품질 카테고리(최상급, 좋음, 보통, 나쁨)"),
    bortle_scale: Optional[int] = Query(None, ge=1, le=9, description="최대 Bortle 등급(낮을수록 더 좋음)"),
    min_elevation: Optional[int] = Query(None, ge=0, description="최소 해발 고도(미터)"),
    search: Optional[str] = Query(None, description="장소 이름 검색어")
):
    """
    별 관측 명소 목록 조회
    
    다양한 필터 옵션으로 별 관측에 적합한 장소 목록을 조회합니다.
    """
    try:
        query = {}      # 검색 필터 구성
    
        if min_score is not None or max_score is not None:
            query["sky_quality.score"] = {}
            if min_score is not None:
                query["sky_quality.score"]["$gte"] = min_score
            if max_score is not None:
                query["sky_quality.score"]["$lte"] = max_score
        
        if category:
            query["sky_quality.category"] = category
        
        if bortle_scale is not None:
            query["sky_quality.bortle_scale"] = {"$lte": bortle_scale}
        
        if min_elevation is not None:
            query["sky_quality.elevation"] = {"$gte": min_elevation}
        
        if search:
            query["name"] = {"$regex": search, "$options": "i"}
        
        cursor = spots_collection.find(query).sort("sky_quality.score", -1).skip(skip).limit(limit)
        
        spots = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "created_at" in doc and isinstance(doc["created_at"], datetime):
                doc["created_at"] = doc["created_at"].isoformat()
            spots.append(doc)
        
        total_count = spots_collection.count_documents(query)
        
        return {
            "spots": spots,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "filters_applied": {
                "min_score": min_score,
                "max_score": max_score,
                "category": category,
                "bortle_scale": bortle_scale,
                "min_elevation": min_elevation,
                "search": search
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"관측 명소 데이터 조회 중 오류 발생: {str(e)}")
    
@router.get("/observation-spots/nearby", summary="주변 관측 명소")
async def get_nearby_observation_spots(
    lat: float = Query(..., description="현재 위치 위도"),
    lon: float = Query(..., description="현재 위치 경도"),
    radius: float = Query(50.0, ge=0.1, le=500.0, description="검색 반경 (km)"),
    limit: int = Query(10, ge=1, le=50, description="반환할 최대 결과 수"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="최소 별 관측 품질 점수")
):
    """
    주변 관측 명소 조회
    
    현재 위치 주변의 별 관측 명소를 거리순으로 정렬하여 조회합니다.
    """
    try:
        # GeoJSON 형태로 위치 정보가 저장되어 있을때 MongoDB의 공간 쿼리 사용
        # 모든 명소 데이터 조회
        spots = list(spots_collection.find({}))
        
        nearby_spots = []       # 거리 계산 + 필터링 
        for spot in spots:
            spot_lat = spot["location"]["latitude"]
            spot_lon = spot["location"]["longitude"]
            
            # Haversine 공식으로 두 지점 간 거리 계산
            lat1, lon1, lat2, lon2 = map(math.radians, [lat, lon, spot_lat, spot_lon])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = 6371 * c 
            
            # 반경 내에 있고 최소 점수 조건을 충족하는지 확인
            if distance <= radius and (min_score is None or spot["sky_quality"]["score"] >= min_score):
                spot["distance"] = round(distance, 2)
                spot["_id"] = str(spot["_id"])
                if "created_at" in spot and isinstance(spot["created_at"], datetime):
                    spot["created_at"] = spot["created_at"].isoformat()
                nearby_spots.append(spot)
        
        nearby_spots.sort(key=lambda x: x["distance"])  # 거리 순 정렬 
        nearby_spots = nearby_spots[:limit]
        
        return {
            "spots": nearby_spots,
            "total": len(nearby_spots),
            "location": {"latitude": lat, "longitude": lon, "radius_km": radius}
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주변 관측 명소 조회 중 오류 발생: {str(e)}")

@router.get("/observation-spots/best", summary="추천 관측 명소")
async def get_best_observation_spots(
    limit: int = Query(5, ge=1, le=20, description="반환할 명소 수"),
    category: Optional[str] = Query(None, description="별 관측 품질 카테고리"),
    bortle_max: int = Query(4, ge=1, le=9, description="최대 Bortle 등급 (낮을수록 좋음)")
):
    """
    추천 별 관측 명소
    
    가장 별 관측 조건이 좋은 장소들을 추천합니다.
    """
    try:
        query = {}

        query["sky_quality.bortle_scale"] = {"$lte": bortle_max}
        
        if category:
            query["sky_quality.category"] = category
        
        cursor = spots_collection.find(query).sort("sky_quality.score", -1).limit(limit)  # 별 관측 품질 점수 기준으로 정렬하여 조회
        
        best_spots = []
        for spot in cursor:
            spot["_id"] = str(spot["_id"])
            if "created_at" in spot and isinstance(spot["created_at"], datetime):
                spot["created_at"] = spot["created_at"].isoformat()
            best_spots.append(spot)
        
        return {
            "spots": best_spots,
            "total": len(best_spots),
            "criteria": {
                "bortle_max": bortle_max,
                "category": category
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 관측 명소 조회 중 오류 발생: {str(e)}")

@router.get("/observation-spots/categories", summary="카테고리별 명소 수")
async def get_observation_spots_by_category():
    """
    카테고리별 관측 명소 통계
    
    별 관측 품질 카테고리별 명소 개수와 통계를 제공합니다.
    """
    try:    # 집계 파이프라인 구성
        pipeline = [
            {
                "$group": {
                    "_id": "$sky_quality.category",
                    "count": {"$sum": 1},
                    "avg_score": {"$avg": "$sky_quality.score"},
                    "avg_bortle": {"$avg": "$sky_quality.bortle_scale"},
                    "avg_sqm": {"$avg": "$sky_quality.sqm"},
                    "min_score": {"$min": "$sky_quality.score"},
                    "max_score": {"$max": "$sky_quality.score"}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        result = list(spots_collection.aggregate(pipeline))
    
        categories = []
        for item in result:
            categories.append({
                "category": item["_id"],
                "count": item["count"],
                "avg_score": round(item["avg_score"], 1),
                "avg_bortle": round(item["avg_bortle"], 1),
                "avg_sqm": round(item["avg_sqm"], 2),
                "score_range": {
                    "min": round(item["min_score"], 1),
                    "max": round(item["max_score"], 1)
                }
            })
        
        total_count = spots_collection.count_documents({})
        avg_score = spots_collection.aggregate([
            {"$group": {"_id": None, "avg": {"$avg": "$sky_quality.score"}}}
        ])
        avg_score_value = round(list(avg_score)[0]["avg"], 1) if list(avg_score) else None
        
        return {
            "categories": categories,
            "total_spots": total_count,
            "avg_overall_score": avg_score_value
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리별 통계 조회 중 오류 발생: {str(e)}")

@router.get("/observation-spots/{spot_id}", summary="관측 명소 상세")
async def get_observation_spot_by_id(
    spot_id: str = Path(..., description="관측 명소 ID")
):
    """
    관측 명소 상세 정보
    
    특정 ID의 별 관측 명소 상세 정보를 조회합니다.
    """
    try:
        if not ObjectId.is_valid(spot_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 ID 형식입니다")
        
        spot = spots_collection.find_one({"_id": ObjectId(spot_id)})
        
        if not spot:
            raise HTTPException(status_code=404, detail="해당 ID의 관측 명소를 찾을 수 없습니다")
        
        spot["_id"] = str(spot["_id"])

        if "created_at" in spot and isinstance(spot["created_at"], datetime):
            spot["created_at"] = spot["created_at"].isoformat()
        
        return spot
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"관측 명소 상세 정보 조회 중 오류 발생: {str(e)}")

