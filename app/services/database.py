from pymongo import MongoClient
from pymongo.database import Database
import os
import logging
from fastapi import Depends  

logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "counting_stars")

client: MongoClient = None

def connect_db():
    global client
    try:
        logger.info(f"MongoDB 연결 시도: {MONGO_URI}")
        client = MongoClient(MONGO_URI)
        client.admin.command('ping') 
        logger.info(f"MongoDB 연결 성공: {MONGO_URI}")
    except Exception as e:
        logger.error(f"MongoDB 연결 실패: {e}")
        raise

def close_db():
    global client
    if client:
        client.close()
        logger.info("MongoDB 연결 종료")

def get_client() -> MongoClient:
    if client is None:
        connect_db()
    return client

def get_database(client: MongoClient = Depends(get_client)) -> Database:
    return client[MONGO_DB_NAME]