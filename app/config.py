from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "별 볼일 있는 지도"
    API_V1_STR: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    MONGO_URI: str = "mongodb://localhost:27017/"
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME")

    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  
    ALLOWED_EXTENSIONS: list = ["jpg", "jpeg", "png"]
    
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    
    CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "*"
    ]
    
    DEFAULT_RADIUS: float = 10.0  
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)