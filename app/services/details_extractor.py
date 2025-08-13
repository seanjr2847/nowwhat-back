"""
퍼플렉시티 검색 결과에서 체크리스트 아이템의 details 정보를 추출하는 서비스
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ItemDetails:
    """체크리스트 아이템의 상세 정보"""
    tips: Optional[List[str]] = None
    contacts: Optional[List[Dict[str, str]]] = None
    links: Optional[List[Dict[str, str]]] = None
    price: Optional[str] = None
    location: Optional[str] = None

class DetailsExtractor:
    """퍼플렉시티 검색 결과에서 details 정보 추출"""
    
    def __init__(self):
        # 연락처 패턴
        self.phone_patterns = [
            r'(\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4})',  # 한국 전화번호
            r'(\d{3}[-\s]?\d{4}[-\s]?\d{4})',      # 휴대폰
        ]
        
        # 이메일 패턴
        self.email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        
        # URL 패턴
        self.url_pattern = r'(https?://[^\s<>"{}|\\^`\[\]]+)'
        
        # 가격 패턴
        self.price_patterns = [
            r'(\d{1,3}(?:,\d{3})*원)',           # 10,000원
            r'(\d+만원)',                        # 5만원
            r'(\d+천원)',                        # 5천원
            r'(\$\d+(?:\.\d{2})?)',              # $10.00
            r'(월\s*\d+(?:,\d+)*원)',            # 월 50,000원
            r'(무료|공짜|Free)',                  # 무료
        ]
        
        # 위치/주소 패턴
        self.location_patterns = [
            r'([가-힣]+시\s+[가-힣]+구\s+[가-힣]+동)',     # 서울시 강남구 역삼동
            r'([가-힣]+시\s+[가-힣]+구)',                # 서울시 강남구
            r'([가-힣]+역\s+\d+번\s*출구)',              # 강남역 3번 출구
            r'([가-힣]+\s*센터|[가-힣]+\s*빌딩)',         # 강남센터, 롯데빌딩
        ]
    
    def extract_details_from_search_results(
        self, 
        search_results: List[Any], 
        item_text: str
    ) -> ItemDetails:
        """검색 결과에서 아이템에 맞는 details 추출 (JSON 우선, 정규식 폴백)"""
        
        if not search_results:
            return ItemDetails()
        
        # 성공한 검색 결과들 수집
        structured_data = []
        fallback_content = []
        all_sources = []
        
        for result in search_results:
            if hasattr(result, 'success') and result.success and result.content:
                try:
                    # JSON 파싱 시도
                    import json
                    data = json.loads(result.content)
                    structured_data.append(data)
                    logger.info(f"Successfully used structured JSON data for item: {item_text[:30]}...")
                except json.JSONDecodeError:
                    # JSON이 아니면 기존 방식으로 폴백
                    fallback_content.append(result.content)
                    if hasattr(result, 'sources') and result.sources:
                        all_sources.extend(result.sources)
        
        # JSON 구조화된 데이터가 있으면 우선 사용
        if structured_data:
            return self._merge_structured_data(structured_data)
        
        # JSON이 없으면 기존 정규식 방식으로 폴백
        if not fallback_content:
            return ItemDetails()
        
        combined_content = " ".join(fallback_content)
        
        # 기존 정규식 방식으로 추출
        details = ItemDetails(
            tips=self._extract_tips(combined_content, item_text),
            contacts=self._extract_contacts(combined_content),
            links=self._extract_links(combined_content, all_sources),
            price=self._extract_price(combined_content, item_text),
            location=self._extract_location(combined_content, item_text)
        )
        
        return details
    
    def _merge_structured_data(self, structured_data: List[dict]) -> ItemDetails:
        """여러 JSON 응답을 병합하여 ItemDetails 생성"""
        merged_tips = []
        merged_contacts = []
        merged_links = []
        price = None
        location = None
        
        for data in structured_data:
            # Tips 병합 with smart splitting
            if data.get("tips") and isinstance(data["tips"], list):
                for tip in data["tips"]:
                    if isinstance(tip, str):
                        # 긴 tip을 여러 개로 분리 (Gemini가 하나로 뭉쳐서 보낸 경우 처리)
                        processed_tips = self._split_long_tip(tip)
                        merged_tips.extend(processed_tips)
            
            # Contacts 병합
            if data.get("contacts") and isinstance(data["contacts"], list):
                merged_contacts.extend(data["contacts"])
            
            # Links 병합
            if data.get("links") and isinstance(data["links"], list):
                merged_links.extend(data["links"])
            
            # Price (첫 번째 유효한 값 사용)
            if not price and data.get("price") and data["price"] != "null":
                price = data["price"]
            
            # Location (첫 번째 유효한 값 사용)
            if not location and data.get("location") and data["location"] != "null":
                location = data["location"]
        
        # 중복 제거 및 품질 필터링
        unique_tips = self._filter_and_dedupe_tips(merged_tips) if merged_tips else None
        unique_contacts = merged_contacts[:2] if merged_contacts else None
        unique_links = merged_links[:3] if merged_links else None
        
        logger.info(f"Merged tips: {len(unique_tips) if unique_tips else 0} final tips")
        if unique_tips:
            for i, tip in enumerate(unique_tips):
                logger.debug(f"  Tip {i+1}: {tip[:60]}...")
        
        return ItemDetails(
            tips=unique_tips,
            contacts=unique_contacts,
            links=unique_links,
            price=price,
            location=location
        )
    
    def _extract_tips(self, content: str, item_text: str) -> Optional[List[str]]:
        """실용적인 팁 추출"""
        tip_patterns = [
            r'팁[:：]\s*([^.!?]+[.!?])',
            r'추천[:：]\s*([^.!?]+[.!?])',
            r'주의사항[:：]\s*([^.!?]+[.!?])',
            r'방법[:：]\s*([^.!?]+[.!?])',
        ]
        
        tips = []
        
        # 패턴 기반 추출
        for pattern in tip_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                clean_tip = match.strip()
                if len(clean_tip) > 10 and len(clean_tip) < 100:
                    tips.append(clean_tip)
        
        # 문장 단위에서 실용적 팁 찾기
        sentences = re.split(r'[.!?]\s+', content)
        practical_keywords = ['추천', '팁', '방법', '주의', '중요', '필수', '고려']
        
        for sentence in sentences:
            if any(keyword in sentence for keyword in practical_keywords):
                if 20 <= len(sentence) <= 120:
                    tips.append(sentence.strip())
        
        # 중복 제거 및 정렬
        unique_tips = list(dict.fromkeys(tips))
        return unique_tips[:3] if unique_tips else None
    
    def _extract_contacts(self, content: str) -> Optional[List[Dict[str, str]]]:
        """연락처 정보 추출"""
        contacts = []
        
        # 전화번호 추출
        phones = []
        for pattern in self.phone_patterns:
            phones.extend(re.findall(pattern, content))
        
        # 이메일 추출
        emails = re.findall(self.email_pattern, content)
        
        # 연락처와 이름 매칭 시도
        lines = content.split('\n')
        for line in lines:
            phone_match = None
            email_match = None
            
            for pattern in self.phone_patterns:
                phone_match = re.search(pattern, line)
                if phone_match:
                    break
            
            email_match = re.search(self.email_pattern, line)
            
            if phone_match or email_match:
                # 같은 줄에서 이름 찾기
                name_candidates = re.findall(r'([가-힣]{2,4})\s*(?:씨|님|센터|병원|학원)', line)
                name = name_candidates[0] if name_candidates else "담당자"
                
                contact = {"name": name}
                if phone_match:
                    contact["phone"] = phone_match.group(1)
                if email_match:
                    contact["email"] = email_match.group(1)
                
                contacts.append(contact)
        
        return contacts[:2] if contacts else None
    
    def _extract_links(self, content: str, sources: List[str]) -> Optional[List[Dict[str, str]]]:
        """유용한 링크 추출"""
        links = []
        
        # 소스에서 링크 추출
        for source in sources[:3]:  # 최대 3개
            if source.startswith('http'):
                # URL에서 제목 추정
                title = self._generate_link_title(source)
                links.append({"title": title, "url": source})
        
        # 본문에서 추가 링크 추출
        url_matches = re.findall(self.url_pattern, content)
        for url in url_matches[:2]:  # 추가로 최대 2개
            if not any(link["url"] == url for link in links):
                title = self._generate_link_title(url)
                links.append({"title": title, "url": url})
        
        return links if links else None
    
    def _generate_link_title(self, url: str) -> str:
        """URL에서 제목 생성"""
        # 도메인에서 서비스명 추출
        domain_map = {
            'naver.com': '네이버',
            'daum.net': '다음',
            'google.com': '구글',
            'youtube.com': '유튜브',
            'blog.': '블로그',
            'cafe.': '카페',
        }
        
        for domain, title in domain_map.items():
            if domain in url:
                return f"{title} 정보"
        
        # 일반적인 제목 생성
        if 'blog' in url or 'post' in url:
            return "관련 블로그"
        elif 'shop' in url or 'store' in url:
            return "온라인 쇼핑몰"
        else:
            return "참고 사이트"
    
    def _extract_price(self, content: str, item_text: str) -> Optional[str]:
        """가격 정보 추출"""
        prices = []
        
        for pattern in self.price_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            prices.extend(matches)
        
        if prices:
            # 가장 구체적인 가격 정보 선택
            price_priority = ['월', '원', '$', '만원', '천원', '무료']
            for priority in price_priority:
                for price in prices:
                    if priority in price:
                        return price
            
            return prices[0]  # 첫 번째 발견된 가격
        
        return None
    
    def _extract_location(self, content: str, item_text: str) -> Optional[str]:
        """위치/주소 정보 추출"""
        locations = []
        
        for pattern in self.location_patterns:
            matches = re.findall(pattern, content)
            locations.extend(matches)
        
        if locations:
            # 가장 구체적인 위치 정보 선택
            return max(locations, key=len)
        
        return None
    
    def to_dict(self, details: ItemDetails) -> Dict[str, Any]:
        """ItemDetails를 딕셔너리로 변환"""
        result = {}
        
        if details.tips:
            result['tips'] = details.tips
        if details.contacts:
            result['contacts'] = details.contacts
        if details.links:
            result['links'] = details.links
        if details.price:
            result['price'] = details.price
        if details.location:
            result['location'] = details.location
        
        # 빈 결과라도 딕셔너리를 반환 (None 대신)
        return result
    
    def _split_long_tip(self, tip: str) -> List[str]:
        """긴 tip을 여러 개의 짧은 tip으로 분할"""
        # 너무 짧으면 그대로 반환
        if len(tip) <= 100:
            return [tip.strip()]
        
        tips = []
        
        # 1. 번호나 불릿 포인트로 분할 시도
        if re.search(r'\d+\.\s|[-•*]\s', tip):
            parts = re.split(r'(?=\d+\.\s|[-•*]\s)', tip)
            for part in parts:
                clean_part = re.sub(r'^\d+\.\s*|^[-•*]\s*', '', part.strip())
                if len(clean_part) > 10:
                    tips.append(clean_part)
        
        # 2. 문장 단위로 분할 시도
        elif len(tip) > 200:
            sentences = re.split(r'[.!?]\s+', tip)
            current_tip = ""
            
            for sentence in sentences:
                if len(current_tip + sentence) < 100:
                    current_tip += sentence + ". "
                else:
                    if current_tip.strip():
                        tips.append(current_tip.strip())
                    current_tip = sentence + ". "
            
            if current_tip.strip():
                tips.append(current_tip.strip())
        
        # 3. 분할 실패 시 원본 반환
        if not tips:
            tips = [tip.strip()]
        
        return tips[:3]  # 최대 3개로 제한
    
    def _filter_and_dedupe_tips(self, tips: List[str]) -> List[str]:
        """팁 필터링 및 중복 제거"""
        if not tips:
            return []
        
        filtered_tips = []
        seen = set()
        
        for tip in tips:
            tip = tip.strip()
            
            # 너무 짧거나 긴 팁 제거
            if len(tip) < 10 or len(tip) > 300:
                continue
            
            # 중복 확인 (소문자 변환하여 비교)
            tip_lower = tip.lower()
            if tip_lower in seen:
                continue
            
            seen.add(tip_lower)
            filtered_tips.append(tip)
            
            # 최대 5개로 제한
            if len(filtered_tips) >= 5:
                break
        
        return filtered_tips

# 서비스 인스턴스
details_extractor = DetailsExtractor()