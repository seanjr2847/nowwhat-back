import httpx
from google.auth.transport import requests
from google.oauth2 import id_token
from typing import Dict, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class GoogleAuthService:
    """구글 OAuth 토큰 검증 서비스"""
    
    @staticmethod
    async def verify_google_token(token: str) -> Optional[Dict[str, any]]:
        """
        구글 ID 토큰을 검증하고 사용자 정보를 반환합니다.
        
        Args:
            token: 구글에서 발급받은 ID 토큰
            
        Returns:
            사용자 정보 또는 None (검증 실패시)
        """
        try:
            # Google Client ID 확인
            if not settings.GOOGLE_CLIENT_ID:
                logger.error("GOOGLE_CLIENT_ID가 설정되지 않았습니다")
                return None
            
            # 방법 1: google.oauth2.id_token 사용 (더 안전)
            request = requests.Request()
            id_info = id_token.verify_oauth2_token(
                token, 
                request, 
                audience=settings.GOOGLE_CLIENT_ID  # 클라이언트 ID로 토큰 검증
            )
            
            # 토큰 발급자 확인
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.warning("Invalid token issuer")
                return None
            
            # 클라이언트 ID 재확인
            if id_info['aud'] != settings.GOOGLE_CLIENT_ID:
                logger.warning("Token audience does not match client ID")
                return None
            
            return {
                'google_id': id_info['sub'],
                'email': id_info['email'],
                'name': id_info.get('name', ''),
                'profile_image': id_info.get('picture', ''),
                'email_verified': id_info.get('email_verified', False)
            }
            
        except ValueError as e:
            logger.error(f"Google token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            return None
    
    @staticmethod
    async def verify_google_token_alternative(token: str) -> Optional[Dict[str, any]]:
        """
        구글 토큰을 Google API를 통해 직접 검증합니다. (대안 방법)
        """
        try:
            async with httpx.AsyncClient() as client:
                # ID 토큰 정보 확인
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
                )
                
                if response.status_code != 200:
                    logger.warning(f"Google tokeninfo API returned status: {response.status_code}")
                    return None
                
                token_info = response.json()
                
                # 클라이언트 ID 확인
                if settings.GOOGLE_CLIENT_ID and token_info.get('aud') != settings.GOOGLE_CLIENT_ID:
                    logger.warning("Token audience does not match client ID")
                    return None
                
                return {
                    'google_id': token_info['sub'],
                    'email': token_info['email'],
                    'name': token_info.get('name', ''),
                    'profile_image': token_info.get('picture', ''),
                    'email_verified': token_info.get('email_verified', 'true').lower() == 'true'
                }
                
        except Exception as e:
            logger.error(f"Alternative token verification failed: {e}")
            return None

# 서비스 인스턴스 생성
google_auth_service = GoogleAuthService() 