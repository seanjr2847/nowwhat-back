"""검색 기능을 위한 Gemini 프롬프트와 응답 형식"""
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
    """체크리스트 아이템 기반 웹 검색용 프롬프트 생성 (responseSchema 전용)"""
    current_year = datetime.now().year
    return f"""Search for practical information about "{checklist_item}" and provide helpful details.

Please find:
- Practical tips for implementing "{checklist_item}"
- Useful websites, tools, or platforms related to this task
- Contact information for relevant services or organizations (if applicable)
- Cost estimates or pricing information (if applicable)
- Location or place information for offline activities (if applicable)

Search context: {user_country or '한국'} market, {current_year} information, {user_language or '한국어'} language priority.

Focus on actionable, specific information that helps users complete this checklist item effectively."""