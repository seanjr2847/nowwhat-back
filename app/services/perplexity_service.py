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
        
        # API 키 상태 로깅
        if not self.api_key:
            logger.error("🚨 PERPLEXITY_API_KEY not found in environment variables!")
            logger.error("   체크리스트 아이템에 description이 추가되지 않습니다.")
            logger.error("   환경변수 PERPLEXITY_API_KEY를 설정해주세요.")
        else:
            logger.info(f"✅ Perplexity API 키 확인됨 (길이: {len(self.api_key)} 문자)")
            logger.info(f"   최대 동시 검색: {self.max_concurrent_searches}개")
            logger.info(f"   검색 타임아웃: {self.timeout_seconds}초")
    
    async def parallel_search(self, queries: List[str]) -> List[SearchResult]:
        """10개의 검색 쿼리를 병렬로 실행"""
        if not self.api_key:
            logger.error("🚨 Perplexity API 키가 없어 검색을 건너뜁니다")
            logger.error(f"   {len(queries)}개 쿼리: {', '.join(queries[:3])}{'...' if len(queries) > 3 else ''}")
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
            failed_count = len(limited_queries) - success_count
            
            if success_count > 0:
                logger.info(f"🔍 검색 완료: {success_count}/{len(limited_queries)}개 성공")
                # 성공한 검색 결과의 내용 길이 로깅
                content_lengths = [len(r.content) for r in processed_results if r.success and r.content]
                if content_lengths:
                    avg_length = sum(content_lengths) / len(content_lengths)
                    logger.info(f"   평균 응답 길이: {avg_length:.0f}자")
            else:
                logger.warning(f"⚠️ 모든 검색 실패: {failed_count}개 실패")
                logger.warning("   체크리스트 아이템에 description이 추가되지 않습니다")
            
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
                        logger.error(f"🚨 Perplexity API 오류 {response.status} (쿼리: '{query[:30]}...')")
                        logger.error(f"   응답: {error_text[:100]}...")
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
    
    def generate_search_queries_from_checklist(
        self,
        checklist_items: List[str],
        goal: str,
        answers: List[Dict[str, Any]]
    ) -> List[str]:
        """체크리스트 아이템 기반으로 검색 쿼리 생성 (범용적 방식)"""
        
        # 답변에서 핵심 컨텍스트 추출
        answer_context = self._extract_answer_context(answers)
        
        search_queries = []
        
        # 각 체크리스트 아이템을 기반으로 검색 쿼리 생성
        for item in checklist_items[:10]:  # 최대 10개 아이템
            # 아이템에서 핵심 키워드 추출
            core_keywords = self._extract_core_keywords_from_item(item)
            
            if core_keywords:
                # 여러 패턴의 검색 쿼리 생성
                queries = self._generate_item_specific_queries(core_keywords, answer_context)
                search_queries.extend(queries)
        
        # 중복 제거 및 길이 제한
        unique_queries = list(dict.fromkeys(search_queries))[:15]  # 최대 15개
        
        logger.info(f"Generated {len(unique_queries)} search queries from {len(checklist_items)} checklist items")
        return unique_queries
    
    def _extract_core_keywords_from_item(self, item: str) -> List[str]:
        """체크리스트 아이템에서 검색에 유용한 핵심 키워드 추출"""
        import re
        
        # 불용어 제거
        stopwords = [
            '을', '를', '이', '가', '은', '는', '의', '에', '에서', '와', '과',
            '하기', '하세요', '합니다', '위한', '위해', '통해', '대한', '함께'
        ]
        
        # 명사형 키워드 우선 추출
        noun_patterns = [
            r'[가-힣]{2,}(?:앱|어플|플랫폼|서비스|사이트)',  # 서비스 관련
            r'[가-힣]{2,}(?:교재|책|자료|가이드)',  # 학습 자료
            r'[가-힣]{2,}(?:계획|일정|스케줄)',  # 계획 관련
            r'[가-힣]{2,}(?:예산|비용|가격|돈)',  # 비용 관련
            r'[가-힣]{2,}(?:방법|방식|팁|노하우)',  # 방법 관련
        ]
        
        keywords = []
        
        # 특수 패턴 먼저 추출
        for pattern in noun_patterns:
            matches = re.findall(pattern, item)
            keywords.extend(matches)
        
        # 일반 명사 추출 (2글자 이상)
        words = re.findall(r'[가-힣a-zA-Z]{2,}', item)
        for word in words:
            if word not in stopwords and word not in keywords:
                keywords.append(word)
        
        return keywords[:5]  # 상위 5개 키워드
    
    def _generate_item_specific_queries(self, keywords: List[str], context: str = "") -> List[str]:
        """키워드를 기반으로 다양한 검색 쿼리 생성"""
        if not keywords:
            return []
        
        main_keyword = keywords[0]
        additional_keywords = " ".join(keywords[1:3]) if len(keywords) > 1 else ""
        
        # 검색 패턴 템플릿 (범용적)
        query_patterns = [
            f"{main_keyword} 방법 추천",
            f"{main_keyword} 가이드 팁", 
            f"{main_keyword} {additional_keywords} 정보".strip(),
        ]
        
        # 컨텍스트가 있으면 개인화
        if context and len(context) > 5:
            context_short = context[:30]  # 너무 길지 않게
            query_patterns.append(f"{main_keyword} {context_short} 추천")
        
        return query_patterns[:2]  # 아이템당 최대 2개 쿼리
    
    def _extract_answer_context(self, answers: List[Dict[str, Any]]) -> str:
        """답변에서 검색에 유용한 컨텍스트 추출 (유연한 방식)"""
        meaningful_answers = []
        
        for answer_item in answers:
            answer = answer_item.get("answer", "")
            
            if isinstance(answer, list):
                answer = " ".join(answer)
            
            # 의미있는 답변 필터링 (일반적인 조건들)
            if self._is_meaningful_answer(answer):
                meaningful_answers.append(answer.strip())
        
        # 답변 길이와 구체성을 기준으로 정렬 (긴 답변이 더 구체적일 가능성)
        meaningful_answers.sort(key=len, reverse=True)
        
        # 상위 답변들을 조합 (최대 3개)
        selected_answers = meaningful_answers[:3]
        final_context = " ".join(selected_answers)
        
        # 검색 쿼리에 적합한 길이로 조정
        if len(final_context) > 120:
            final_context = final_context[:117] + "..."
        
        return final_context
    
    def _is_meaningful_answer(self, answer: str) -> bool:
        """답변이 의미있는 컨텍스트인지 판단"""
        if not answer or len(answer.strip()) < 2:
            return False
        
        answer = answer.strip()
        
        # 명백히 의미없는 답변들 제외
        meaningless_patterns = [
            # 단일 문자나 기호
            r'^[ㄱ-ㅎㅏ-ㅣ]$',  # 단일 한글 자음/모음
            r'^[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]$',  # 단일 특수문자
            r'^\d+$',  # 숫자만
            # 무의미한 반복
            r'^(.)\1{2,}$',  # 같은 문자 3번 이상 반복
            # 임시/빈 답변 패턴
            r'^(없음|없다|모름|잘모름|해당없음|패스)$',
            r'^(.|_|-|\s)*$',  # 특수문자나 공백만
        ]
        
        import re
        for pattern in meaningless_patterns:
            if re.match(pattern, answer, re.IGNORECASE):
                return False
        
        # 최소 길이 체크 (너무 짧은 답변 제외)
        if len(answer) < 3:
            return False
        
        # 의미있는 단어가 포함되어 있는지 체크
        meaningful_chars = re.findall(r'[가-힣a-zA-Z0-9]', answer)
        if len(meaningful_chars) < 2:
            return False
        
        return True
    
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