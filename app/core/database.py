# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
   PROJECT_NAME: str = "My API"
   VERSION: str = "1.0.0"
   API_V1_STR: str = "/api/v1"
   
   # 데이터베이스 URL (전체 연결 문자열)
   DATABASE_URL: str = "postgresql://neondb_owner:npg_0PAEIUGMxJq6@ep-orange-hall-ad5vlgl8-pooler.c-2.us-east-1.aws.neon.tech/neondb"
   
   # 보안
   SECRET_KEY: str = "your-secret-key-here"
   ALGORITHM: str = "HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
   
   class Config:
       env_file = ".env"

settings = Settings()