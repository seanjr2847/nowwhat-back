import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Perplexity API 검색 결과"""
    query: str
    content: str
    sources: List[str]
    success: bool
    error_message: Optional[str] = None

class PerplexityService:
    """Perplexity API를 통한 실시간 정보 검색 서비스"""
    
    def __init__(self):
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.api_key = getattr(settings, 'PERPLEXITY_API_KEY', '')
        self.max_concurrent_searches = getattr(settings, 'MAX_CONCURRENT_SEARCHES', 10)
        self.timeout_seconds = getattr(settings, 'SEARCH_TIMEOUT_SECONDS', 15)
        
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not found in settings - search functionality will be disabled")
    
    async def parallel_search(self, queries: List[str]) -> List[SearchResult]:
        """10개의 검색 쿼리를 병렬로 실행"""
        if not self.api_key:
            logger.warning("Perplexity API key not available, returning empty results")
            return [self._create_empty_result(query) for query in queries]
        
        if not queries:
            return []
        
        # 최대 동시 검색 수 제한
        limited_queries = queries[:self.max_concurrent_searches]
        
        try:
            # 병렬 검색 실행
            tasks = [self._search_single_query(query) for query in limited_queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리 및 결과 정리
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Search failed for query '{limited_queries[i]}': {str(result)}")
                    processed_results.append(self._create_error_result(limited_queries[i], str(result)))
                else:
                    processed_results.append(result)
            
            success_count = sum(1 for r in processed_results if r.success)
            logger.info(f"Completed parallel search: {success_count}/{len(limited_queries)} successful")
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Parallel search failed: {str(e)}")
            return [self._create_error_result(query, str(e)) for query in limited_queries]
    
    async def _search_single_query(self, query: str) -> SearchResult:
        """단일 검색 쿼리 실행"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides current, accurate information. Provide concise, factual answers with reliable sources."
                    },
                    {
                        "role": "user", 
                        "content": query
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.2,
                "stream": False
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_perplexity_response(query, data)
                    else:
                        error_text = await response.text()
                        logger.error(f"Perplexity API error {response.status}: {error_text}")
                        return self._create_error_result(query, f"API error {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error(f"Search timeout for query: {query}")
            return self._create_error_result(query, "Search timeout")
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            return self._create_error_result(query, str(e))
    
    def _parse_perplexity_response(self, query: str, data: Dict[str, Any]) -> SearchResult:
        """Perplexity API 응답 파싱"""
        try:
            if "choices" not in data or not data["choices"]:
                return self._create_error_result(query, "No choices in response")
            
            choice = data["choices"][0]
            if "message" not in choice:
                return self._create_error_result(query, "No message in choice")
            
            content = choice["message"].get("content", "").strip()
            if not content:
                return self._create_error_result(query, "Empty content in response")
            
            # 소스 정보 추출 (Perplexity는 보통 응답에 소스를 포함)
            sources = self._extract_sources_from_content(content)
            
            return SearchResult(
                query=query,
                content=content,
                sources=sources,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Perplexity response for query '{query}': {str(e)}")
            return self._create_error_result(query, f"Parse error: {str(e)}")
    
    def _extract_sources_from_content(self, content: str) -> List[str]:
        """콘텐츠에서 소스 URL 추출"""
        import re
        
        # URL 패턴 매칭
        url_pattern = r'https?://[^\s\])]+'
        sources = re.findall(url_pattern, content)
        
        # 중복 제거 및 정리
        unique_sources = list(set(sources))
        return unique_sources[:5]  # 최대 5개 소스
    
    def _create_empty_result(self, query: str) -> SearchResult:
        """빈 결과 생성 (API 키 없음)"""
        return SearchResult(
            query=query,
            content="검색 기능을 사용할 수 없습니다.",
            sources=[],
            success=False,
            error_message="Perplexity API key not configured"
        )
    
    def _create_error_result(self, query: str, error_message: str) -> SearchResult:
        """에러 결과 생성"""
        return SearchResult(
            query=query,
            content="",
            sources=[],
            success=False,
            error_message=error_message
        )
    
    def generate_search_queries(
        self, 
        goal: str, 
        intent_title: str, 
        answers: List[Dict[str, Any]]
    ) -> List[str]:
        """사용자 정보를 바탕으로 검색 쿼리 생성"""
        
        # 답변에서 핵심 정보 추출
        answer_context = self._extract_answer_context(answers)
        
        # 의도별 검색 쿼리 템플릿
        query_templates = {
            "여행 계획": [
                f"{goal} 최신 정보 2024",
                f"{goal} 추천 일정 가이드",
                f"{goal} 필수 준비물 체크리스트",
                f"{goal} 예산 계획 팁",
                f"{goal} 현지 문화 주의사항",
                f"{goal} 교통편 예약 방법",
                f"{goal} 숙박 추천 지역",
                f"{goal} 맛집 현지 추천",
                f"{goal} 관광지 입장료 정보",
                f"{goal} 여행 보험 필수사항"
            ],
            "계획 세우기": [
                f"{goal} 단계별 실행 방법",
                f"{goal} 성공 사례 분석",
                f"{goal} 필요 준비물 리스트",
                f"{goal} 예상 소요 시간",
                f"{goal} 예산 계획 가이드",
                f"{goal} 주의사항 체크포인트",
                f"{goal} 효율적인 순서",
                f"{goal} 도구 추천",
                f"{goal} 전문가 조언",
                f"{goal} 실패 요인 분석"
            ],
            "정보 찾기": [
                f"{goal} 최신 트렌드 2024",
                f"{goal} 전문가 의견",
                f"{goal} 비교 분석",
                f"{goal} 가격 정보",
                f"{goal} 리뷰 모음",
                f"{goal} 추천 순위",
                f"{goal} 장단점 비교",
                f"{goal} 구매 가이드",
                f"{goal} 사용법 설명",
                f"{goal} 문제 해결 방법"
            ]
        }
        
        # 기본 쿼리 선택
        base_queries = query_templates.get(intent_title, query_templates["계획 세우기"])
        
        # 답변 컨텍스트가 있으면 쿼리 개인화
        if answer_context:
            personalized_queries = []
            for query in base_queries[:7]:  # 7개는 기본, 3개는 개인화
                personalized_queries.append(f"{query} {answer_context}")
            
            # 추가 개인화 쿼리 3개
            personalized_queries.extend([
                f"{goal} {answer_context} 맞춤 추천",
                f"{goal} {answer_context} 경험담",
                f"{goal} {answer_context} 주의사항"
            ])
            
            return personalized_queries
        
        return base_queries
    
    def _extract_answer_context(self, answers: List[Dict[str, Any]]) -> str:
        """답변에서 검색에 유용한 컨텍스트 추출"""
        context_parts = []
        
        for answer_item in answers:
            answer = answer_item.get("answer", "")
            if isinstance(answer, list):
                answer = " ".join(answer)
            
            # 의미있는 답변만 추가 (짧은 코드성 답변 제외)
            if len(answer) > 2 and not answer.isdigit():
                context_parts.append(answer)
        
        return " ".join(context_parts[:3])  # 최대 3개 답변 컨텍스트
    
    async def enhance_checklist_with_search(
        self, 
        base_checklist: List[str], 
        search_results: List[SearchResult]
    ) -> List[str]:
        """검색 결과를 활용하여 체크리스트 보강"""
        
        if not search_results:
            return base_checklist
        
        # 성공적인 검색 결과만 필터링
        successful_results = [r for r in search_results if r.success and r.content]
        
        if not successful_results:
            logger.warning("No successful search results to enhance checklist")
            return base_checklist
        
        # 검색 결과에서 유용한 정보 추출
        enhancement_info = []
        for result in successful_results:
            # 짧고 실용적인 팁 추출
            tips = self._extract_actionable_tips(result.content)
            enhancement_info.extend(tips)
        
        # 중복 제거 및 품질 필터링
        unique_enhancements = list(set(enhancement_info))
        quality_enhancements = [tip for tip in unique_enhancements if len(tip) > 10 and len(tip) < 100]
        
        # 기존 체크리스트와 병합
        enhanced_checklist = base_checklist.copy()
        
        # 유용한 정보가 있으면 체크리스트에 추가
        for enhancement in quality_enhancements[:5]:  # 최대 5개 추가
            if not any(enhancement.lower() in item.lower() for item in enhanced_checklist):
                enhanced_checklist.append(f"💡 {enhancement}")
        
        logger.info(f"Enhanced checklist: {len(base_checklist)} -> {len(enhanced_checklist)} items")
        return enhanced_checklist
    
    def _extract_actionable_tips(self, content: str) -> List[str]:
        """콘텐츠에서 실행 가능한 팁 추출"""
        tips = []
        
        # 문장 단위로 분리
        sentences = content.split('. ')
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            # 실행 가능한 팁의 특징을 가진 문장 찾기
            actionable_keywords = ['추천', '필요', '준비', '확인', '예약', '구매', '신청', '방문', '연락']
            
            if any(keyword in sentence for keyword in actionable_keywords):
                if 20 <= len(sentence) <= 80:  # 적절한 길이
                    tips.append(sentence)
        
        return tips[:3]  # 최대 3개 팁

# 서비스 인스턴스
perplexity_service = PerplexityService()