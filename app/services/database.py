from pymongo import MongoClient, GEOSPHERE
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Dict, Any

from app.config import settings

class MongoDB:
    client: MongoClient = None
    db: Database = None
    
    locations: Collection = None
    user_observations: Collection = None
    
    @classmethod
    def connect(cls):
        """MongoDB 연결 및 컬렉션 설정"""
        cls.client = MongoClient(settings.MONGO_URI)
        cls.db = cls.client[settings.MONGO_DB_NAME]
        
        cls.locations = cls.db["locations"]
        cls.user_observations = cls.db["user_observations"]
        
        cls.create_indexes()
        
        print(f"MongoDB에 연결되었습니다: {settings.MONGO_URI}")
        return cls.db
    
    @classmethod
    def create_indexes(cls):
        """필요한 인덱스 생성"""
        if "location_2dsphere" not in cls.locations.index_information():
            cls.locations.create_index([("location", GEOSPHERE)])
            print("위치 컬렉션 지오인덱스 생성 완료")
        
        if "star_observation_score_-1" not in cls.locations.index_information():
            cls.locations.create_index([("star_observation_score", -1)])
            print("별 관측 점수 인덱스 생성 완료")
        
        if "location_2dsphere" not in cls.user_observations.index_information():
            cls.user_observations.create_index([("location", GEOSPHERE)])
            print("사용자 관측 컬렉션 지오인덱스 생성 완료")
        
        if "user_id_1" not in cls.user_observations.index_information():
            cls.user_observations.create_index([("user_id", 1)])
            print("사용자 ID 인덱스 생성 완료")
    
    @classmethod
    def close(cls):
        """MongoDB 연결 종료"""
        if cls.client:
            cls.client.close()
            print("MongoDB 연결이 종료되었습니다.")

def get_database() -> Database:
    """현재 데이터베이스 인스턴스 반환"""
    if MongoDB.db is None:
        MongoDB.connect()
    return MongoDB.db

def get_collection(collection_name: str) -> Collection:
    """지정된 컬렉션 반환"""
    if MongoDB.db is None:
        MongoDB.connect()
    return MongoDB.db[collection_name]

def object_id_to_str(data: Dict[str, Any]) -> Dict[str, Any]:
    """MongoDB ObjectId를 문자열로 변환"""
    if data and "_id" in data:
        data["_id"] = str(data["_id"])
    return data