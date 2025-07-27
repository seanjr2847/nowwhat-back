import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def detect_country_from_ip(ip_address: str) -> Optional[str]:
    """IP 주소를 기반으로 국가 감지"""
    try:
        # localhost나 개발 환경의 경우 기본값 반환
        if ip_address in ["127.0.0.1", "localhost", "::1"] or ip_address.startswith("192.168."):
            return "KR"  # 개발 환경에서는 한국으로 기본 설정
            
        # ipapi.co 서비스 사용 (무료, API 키 불필요)
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"https://ipapi.co/{ip_address}/country_code/")
            
            if response.status_code == 200:
                country_code = response.text.strip()
                if len(country_code) == 2:  # 유효한 국가 코드인지 확인
                    logger.info(f"Detected country {country_code} for IP {ip_address}")
                    return country_code
                    
        # 대체 서비스: ip-api.com (무료)
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://ip-api.com/json/{ip_address}?fields=countryCode")
            
            if response.status_code == 200:
                data = response.json()
                country_code = data.get("countryCode")
                if country_code:
                    logger.info(f"Detected country {country_code} for IP {ip_address} (fallback)")
                    return country_code
                    
    except Exception as e:
        logger.warning(f"Failed to detect country for IP {ip_address}: {str(e)}")
        
    # 실패시 기본값 반환
    return "KR"

def get_client_ip(request) -> str:
    """클라이언트 IP 주소 추출"""
    # X-Forwarded-For 헤더 확인 (프록시/로드밸런서 환경)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 첫 번째 IP가 실제 클라이언트 IP
        return forwarded_for.split(",")[0].strip()
    
    # X-Real-IP 헤더 확인
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 직접 연결된 클라이언트 IP
    return request.client.host if request.client else "127.0.0.1" 