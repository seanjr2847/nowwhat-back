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
    steps: Optional[List[Dict[str, Any]]] = None  # 구조화된 단계별 가이드
    contacts: Optional[List[Dict[str, str]]] = None
    links: Optional[List[Dict[str, str]]] = None
    price: Optional[str] = None

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
            steps=self._extract_steps(combined_content, item_text),
            contacts=self._extract_contacts(combined_content),
            links=self._extract_links(combined_content, all_sources),
            price=self._extract_price(combined_content, item_text)
        )
        
        return details
    
    def _merge_structured_data(self, structured_data: List[dict]) -> ItemDetails:
        """여러 JSON 응답을 병합하여 ItemDetails 생성"""
        merged_steps = []
        merged_contacts = []
        merged_links = []
        price = None
        
        for data in structured_data:
            # Steps 병합 with new structure support
            if data.get("steps") and isinstance(data["steps"], list):
                for step in data["steps"]:
                    if isinstance(step, dict):
                        # 새로운 구조화된 형태 (StepInfo)
                        if all(key in step for key in ["order", "title", "description"]):
                            merged_steps.append(step)
                    elif isinstance(step, str):
                        # 기존 문자열 형태 - 구조화된 형태로 변환
                        step_obj = {
                            "order": len(merged_steps) + 1,
                            "title": f"Step {len(merged_steps) + 1}",
                            "description": step,
                            "estimatedTime": None,
                            "difficulty": None
                        }
                        merged_steps.append(step_obj)
            
            # Contacts 병합
            if data.get("contacts") and isinstance(data["contacts"], list):
                merged_contacts.extend(data["contacts"])
            
            # Links 병합
            if data.get("links") and isinstance(data["links"], list):
                merged_links.extend(data["links"])
            
            # Price (첫 번째 유효한 값 사용)
            if not price and data.get("price") and data["price"] != "null":
                price = data["price"]
        
        # 중복 제거 및 품질 필터링
        unique_steps = self._filter_and_dedupe_steps(merged_steps) if merged_steps else None
        unique_contacts = merged_contacts[:2] if merged_contacts else None
        unique_links = merged_links[:3] if merged_links else None
        
        logger.info(f"Merged steps: {len(unique_steps) if unique_steps else 0} final steps")
        if unique_steps:
            for i, step in enumerate(unique_steps):
                logger.debug(f"  Step {i+1}: {step[:60]}...")
        
        return ItemDetails(
            steps=unique_steps,
            contacts=unique_contacts,
            links=unique_links,
            price=price
        )
    
    def _extract_steps(self, content: str, item_text: str) -> Optional[List[Dict[str, Any]]]:
        """실행 가능한 단계 추출 (구조화된 형태로 반환)"""
        step_patterns = [
            r'팁[:：]\s*([^.!?]+[.!?])',
            r'추천[:：]\s*([^.!?]+[.!?])',
            r'주의사항[:：]\s*([^.!?]+[.!?])',
            r'방법[:：]\s*([^.!?]+[.!?])',
        ]
        
        steps = []
        
        # 패턴 기반 추출
        for pattern in step_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                clean_step = match.strip()
                if len(clean_step) > 10 and len(clean_step) < 100:
                    steps.append(clean_step)
        
        # 문장 단위에서 실용적 팁 찾기
        sentences = re.split(r'[.!?]\s+', content)
        practical_keywords = ['추천', '팁', '방법', '주의', '중요', '필수', '고려']
        
        for sentence in sentences:
            if any(keyword in sentence for keyword in practical_keywords):
                if 20 <= len(sentence) <= 120:
                    steps.append(sentence.strip())
        
        # 중복 제거
        unique_steps = list(dict.fromkeys(steps))
        
        # 구조화된 형태로 변환
        structured_steps = []
        for i, step in enumerate(unique_steps[:5]):
            structured_step = {
                "order": i + 1,
                "title": f"Step {i + 1}",
                "description": step,
                "estimatedTime": None,
                "difficulty": None
            }
            structured_steps.append(structured_step)
        
        return structured_steps if structured_steps else None
    
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
    
    def to_dict(self, details: ItemDetails) -> Dict[str, Any]:
        """ItemDetails를 딕셔너리로 변환"""
        result = {}
        
        if details.steps:
            result['steps'] = details.steps
        if details.contacts:
            result['contacts'] = details.contacts
        if details.links:
            result['links'] = details.links
        if details.price:
            result['price'] = details.price
        
        # 빈 결과라도 딕셔너리를 반환 (None 대신)
        return result
    
    def _split_long_step(self, step: str) -> List[str]:
        """긴 step을 여러 개의 짧은 step으로 분할"""
        step = step.strip()
        
        # 1. JSON 구조가 포함된 경우 정리
        if step.startswith('steps:') or '"' in step or '[' in step or ']' in step:
            # JSON 구조 정리
            step = self._clean_json_artifacts(step)
        
        # 너무 짧으면 그대로 반환
        if len(step) <= 100:
            return [step]
        
        steps = []
        
        # 2. JSON 배열 형태 분할 시도
        if any(x in step for x in ['"', ',', '[', ']', 'steps:']):
            # JSON 구조 정리 후 분할
            cleaned = self._clean_json_artifacts(step)
            
            # 쉼표와 따옴표로 구분된 패턴들 시도
            patterns = [
                r'",\s*"',           # "text", "text"
                r'"\s*,\s*\n*\s*"',  # "text" , "text"
                r'"\.\..*?"',        # "text..", "text"
                r'\.\."\s*,?\s*"',   # text..", "text"
                r'\.",\s*"',         # text.", "text"
            ]
            
            for pattern in patterns:
                if re.search(pattern, cleaned):
                    parts = re.split(pattern, cleaned)
                    for part in parts:
                        clean_part = part.strip().strip('"').strip()
                        if len(clean_part) > 10:
                            # 끝에 있는 불완전한 문구 제거
                            clean_part = re.sub(r'\.\.+$', '', clean_part).strip()
                            if clean_part and not any(x in clean_part.lower() for x in ['steps:', 'contacts', 'links']):
                                steps.append(clean_part)
                    if steps:
                        break
            
            # 위 방법이 실패하면 단순한 줄바꿈으로 분할 시도 (세 번째 예시용)
            if not steps and '\n' in cleaned:
                lines = cleaned.split('\n')
                for line in lines:
                    clean_line = line.strip().strip('"').strip()
                    if len(clean_line) > 10 and not any(x in clean_line.lower() for x in ['steps:', 'contacts', 'links', '[', ']']):
                        clean_line = re.sub(r'\.\.+$', '', clean_line).strip()
                        if clean_line:
                            steps.append(clean_line)
        
        # 3. 번호나 불릿 포인트로 분할 시도
        elif re.search(r'\d+\.\s|[-•*]\s', step):
            parts = re.split(r'(?=\d+\.\s|[-•*]\s)', step)
            for part in parts:
                clean_part = re.sub(r'^\d+\.\s*|^[-•*]\s*', '', part.strip())
                if len(clean_part) > 10:
                    steps.append(clean_part)
        
        # 4. 문장 단위로 분할 시도
        elif len(step) > 200:
            sentences = re.split(r'[.!?]\s+', step)
            current_step = ""
            
            for sentence in sentences:
                if len(current_step + sentence) < 100:
                    current_step += sentence + ". "
                else:
                    if current_step.strip():
                        steps.append(current_step.strip())
                    current_step = sentence + ". "
            
            if current_step.strip():
                steps.append(current_step.strip())
        
        # 5. 분할 실패 시 원본 반환
        if not steps:
            steps = [step]
        
        return steps[:5]  # 최대 5개로 제한
    
    def _clean_json_artifacts(self, text: str) -> str:
        """JSON 구조 아티팩트 제거 (분할용)"""
        # 마크다운 코드 블록 제거
        text = re.sub(r'```json|```', '', text)
        
        # JSON 접두사 제거
        if text.startswith('steps:'):
            text = text[5:].strip()
        
        # JSON 객체 시작/끝 제거
        text = re.sub(r'^\s*{\s*"steps":\s*\[', '', text)
        text = re.sub(r'\]\s*,?\s*"contacts".*$', '', text, flags=re.DOTALL)
        
        # 배열 브래킷 제거
        text = re.sub(r'^\[|\]$', '', text.strip())
        
        # 이스케이프 문자 처리
        text = text.replace('\\"', '"')
        text = text.replace('\\n', ' ')
        
        # 연속된 공백 정리 (쉼표는 유지)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _filter_and_dedupe_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """단계 필터링 및 중복 제거 (구조화된 형태)"""
        if not steps:
            return []
        
        filtered_steps = []
        seen = set()
        
        for step in steps:
            if not isinstance(step, dict):
                continue
                
            description = step.get("description", "").strip()
            
            # 너무 짧거나 긴 단계 제거
            if len(description) < 10 or len(description) > 300:
                continue
            
            # 중복 확인 (description을 소문자 변환하여 비교)
            description_lower = description.lower()
            if description_lower in seen:
                continue
            
            seen.add(description_lower)
            # order를 다시 정렬
            step_copy = step.copy()
            step_copy["order"] = len(filtered_steps) + 1
            filtered_steps.append(step_copy)
            
            # 최대 5개로 제한
            if len(filtered_steps) >= 5:
                break
        
        return filtered_steps

# 서비스 인스턴스
details_extractor = DetailsExtractor()