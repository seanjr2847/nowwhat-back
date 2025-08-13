"""한국어 검색 기능을 위한 Gemini 프롬프트와 응답 형식"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel

# 응답 스키마 정의
class ContactInfo(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class LinkInfo(BaseModel):
    title: str
    url: str

class SearchResponse(BaseModel):
    tips: List[str]
    contacts: List[ContactInfo]
    links: List[LinkInfo]
    price: Optional[str] = None
    location: Optional[str] = None

def get_search_prompt(checklist_item: str, user_country: str = None, user_language: str = None) -> str:
    """체크리스트 아이템 기반 웹 검색용 한국어 프롬프트 생성 (responseSchema 전용)"""
    current_year = datetime.now().year
    
    return f""""{checklist_item}"에 대한 정보를 검색하고 정확히 3-5개의 별도 팁을 제공하세요.

요구사항:
- tips: 반드시 3-5개의 별도 문자열 배열, 각각 15-50단어만
- contacts: name/phone/email이 있는 연락처 객체 배열
- links: title/url이 있는 링크 객체 배열
- price: 발견되면 단일 가격 문자열
- location: 발견되면 단일 위치 문자열

각 팁은 반드시:
✓ 하나의 구체적인 실행 가능한 단계
✓ 최대 50단어
✓ 마크다운 없음, 불릿 포인트 없음
✓ 완전한 문장

상황: {user_country or '한국'}, {current_year}년, 한국어

중요: 정확히 3-5개의 별도 팁을 반환하세요. 하나의 긴 텍스트가 아닙니다."""