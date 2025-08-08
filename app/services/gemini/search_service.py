"""
검색 기능 전용 서비스

비즈니스 로직:
- 체크리스트 아이템 기반 실시간 웹 검색 전담
- 다중 검색 쿼리의 병렬 실행으로 성능 최적화
- 검색 결과의 구조화 및 품질 관리
- 검색 실패 시에도 안정적인 결과 반환
"""

import asyncio
import json
import logging
from typing import List, Dict, Any

from app.core.config import settings
from app.prompts.search_prompts import get_search_prompt
from .api_client import GeminiApiClient
from .config import GeminiConfig, SearchResult
from .utils import create_error_result

logger = logging.getLogger(__name__)


class SearchService:
    """웹 검색 기능 전용 서비스 (SRP)
    
    비즈니스 로직:
    - 체크리스트 아이템별로 생성된 검색 쿼리를 병렬 처리
    - API 제한(MAX_CONCURRENT_SEARCHES)을 고려한 배치 처리
    - 각 배치별로 asyncio.gather로 병렬 실행으로 성능 최적화
    - 성공/실패 통계 및 로깅으로 검색 품질 모니터링
    - 검색 실패 시에도 오류 결과 객체로 전체 결과에 포함
    """
    
    def __init__(self, api_client: GeminiApiClient):
        """검색 서비스 초기화
        
        Args:
            api_client: Gemini API 클라이언트 (DIP - 의존성 주입)
        """
        self.api_client = api_client
        logger.info("SearchService initialized")
    
    async def parallel_search(self, queries: List[str]) -> List[SearchResult]:
        """다중 검색 쿼리 병렬 실행
        
        비즈니스 로직:
        - 체크리스트 아이템별로 생성된 검색 쿼리를 병렬 처리
        - API 제한(MAX_CONCURRENT_SEARCHES)을 고려한 배치 처리
        - 각 배치별로 asyncio.gather로 병렬 실행으로 성능 최적화
        - 성공/실패 통계 및 로깅으로 검색 품질 모니터링
        - 검색 실패 시에도 오류 결과 객체로 전체 결과에 포함
        
        Args:
            queries: 검색할 쿼리 리스트
            
        Returns:
            List[SearchResult]: 검색 결과 리스트 (성공/실패 모두 포함)
        """
        logger.info("🚀 GEMINI 병렬 검색 시작")
        logger.info(f"   📝 요청된 쿼리 수: {len(queries)}개")
        
        if not queries:
            logger.warning("⚠️  검색 쿼리가 비어있습니다")
            return []
        
        # 쿼리 내용 로깅 (처음 5개만)
        for i, query in enumerate(queries[:5]):
            logger.info(f"   🔍 쿼리 {i+1}: {query}")
        if len(queries) > 5:
            logger.info(f"   ... 그 외 {len(queries) - 5}개 더")
        
        try:
            # 배치별 병렬 처리로 API 제한 준수
            all_results = await self._execute_batched_searches(queries)
            
            # 결과 분석 및 로깅
            processed_results = self._process_search_results(queries, all_results)
            self._log_search_summary(queries, processed_results)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"💥 병렬 검색 전체 실패: {str(e)}")
            logger.error(f"   🔄 모든 쿼리를 실패 처리합니다")
            return [create_error_result(query, str(e)) for query in queries]
    
    async def _execute_batched_searches(self, queries: List[str]) -> List[Any]:
        """배치별 검색 실행
        
        비즈니스 로직:
        - 전체 쿼리를 API 제한에 맞춰 배치로 분할
        - 각 배치를 병렬로 실행하여 최대 성능 확보
        - 배치 간 순차 실행으로 API 제한 준수
        - 모든 배치 결과를 통합하여 반환
        """
        all_results = []
        batch_size = settings.MAX_CONCURRENT_SEARCHES
        
        logger.info(f"📦 {len(queries)}개 쿼리를 {batch_size}개씩 배치로 처리")
        
        for i in range(0, len(queries), batch_size):
            batch_queries = queries[i:i+batch_size]
            batch_number = i // batch_size + 1
            
            logger.info(f"🔄 배치 {batch_number}: {len(batch_queries)}개 쿼리 처리 중...")
            
            # 배치별 병렬 검색 실행
            tasks = [self._search_single_query(query) for query in batch_queries]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(batch_results)
        
        return all_results
    
    def _process_search_results(self, queries: List[str], raw_results: List[Any]) -> List[SearchResult]:
        """검색 결과 처리 및 분류
        
        비즈니스 로직:
        - 원시 검색 결과를 SearchResult 객체로 변환
        - 예외 발생한 검색은 오류 결과 객체로 변환
        - 성공/실패 쿼리를 분류하여 통계 생성
        - 모든 검색에 대해 일관된 결과 구조 보장
        """
        processed_results = []
        success_queries = []
        failed_queries = []
        
        for i, result in enumerate(raw_results):
            query = queries[i]
            
            if isinstance(result, Exception):
                logger.error(f"❌ 검색 실패 [{i+1}]: '{query[:50]}...' - {str(result)}")
                processed_results.append(create_error_result(query, str(result)))
                failed_queries.append(query)
            else:
                if result.success:
                    logger.info(f"✅ 검색 성공 [{i+1}]: '{query[:50]}...' ({len(result.content)}자)")
                    success_queries.append(query)
                else:
                    logger.warning(f"⚠️  검색 실패 [{i+1}]: '{query[:50]}...' - {result.error_message}")
                    failed_queries.append(query)
                processed_results.append(result)
        
        return processed_results
    
    def _log_search_summary(self, queries: List[str], results: List[SearchResult]):
        """검색 결과 요약 로깅
        
        비즈니스 로직:
        - 전체 검색 세션의 성공률 및 통계 정보 제공
        - 성공한 검색 결과의 품질 지표 (응답 길이 등) 분석
        - 실패한 검색의 예시를 통한 문제점 파악
        - 운영 모니터링 및 성능 최적화를 위한 메트릭 제공
        """
        success_count = len([r for r in results if r.success])
        failed_count = len(results) - success_count
        
        # 결과 요약
        logger.info("=" * 60)
        logger.info("📊 GEMINI 검색 결과 요약")
        logger.info("=" * 60)
        logger.info(f"✅ 성공: {success_count}개")
        logger.info(f"❌ 실패: {failed_count}개")
        logger.info(f"📈 성공률: {(success_count/len(queries)*100):.1f}%")
        
        if success_count > 0:
            # 성공한 검색 결과의 내용 길이 통계
            content_lengths = [len(r.content) for r in results if r.success and r.content]
            if content_lengths:
                avg_length = sum(content_lengths) / len(content_lengths)
                min_length = min(content_lengths)
                max_length = max(content_lengths)
                logger.info(f"📏 응답 길이: 평균 {avg_length:.0f}자 (최소 {min_length}, 최대 {max_length})")
            
            # 성공한 쿼리 몇 개 예시
            success_examples = [q for q, r in zip(queries, results) if r.success][:3]
            for query in success_examples:
                logger.info(f"   ✅ '{query[:40]}...'")
        
        if failed_count > 0:
            failed_examples = [q for q, r in zip(queries, results) if not r.success][:3]
            logger.warning(f"⚠️  실패한 쿼리 {min(3, failed_count)}개 예시:")
            for query in failed_examples:
                logger.warning(f"   ❌ '{query[:40]}...'")
        
        logger.info("=" * 60)
    
    async def _search_single_query(self, query: str) -> SearchResult:
        """단일 검색 쿼리 실시간 실행
        
        비즈니스 로직:
        - 개별 체크리스트 아이템에 대한 Google 검색 기반 실시간 정보 수집
        - get_search_prompt()로 구조화된 검색 프롬프트 생성
        - Gemini API의 웹 검색 기능으로 최신 정보 획득
        - 검색 시간 추적 및 성능 모니터링
        - 예외 발생 시 SearchResult 오류 객체로 안전한 실패 처리
        """
        start_time = asyncio.get_event_loop().time()
        logger.debug(f"🔍 단일 검색 시작: '{query[:50]}...'")
        
        try:
            # 체크리스트 아이템에 대한 구체적인 프롬프트 생성
            prompt = get_search_prompt(query)
            logger.debug(f"📝 생성된 프롬프트 길이: {len(prompt)}자")

            # Gemini API 호출 (웹 검색 활성화)
            response = await self.api_client.call_api_with_search(prompt)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # 응답 파싱
            result = self._parse_search_response(query, response)
            
            if result.success:
                logger.debug(f"✅ 검색 완료 ({elapsed:.2f}초): {len(result.content)}자 응답")
            else:
                logger.warning(f"⚠️  검색 실패 ({elapsed:.2f}초): {result.error_message}")
            
            return result
                        
        except asyncio.TimeoutError:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"⏰ 검색 타임아웃 ({elapsed:.2f}초)")
            logger.error(f"   쿼리: '{query[:50]}...'")
            return create_error_result(query, f"Search timeout after {elapsed:.2f}s")
        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"💥 검색 예외 발생 ({elapsed:.2f}초)")
            logger.error(f"   쿼리: '{query[:50]}...'")
            logger.error(f"   오류: {str(e)}")
            return create_error_result(query, f"Exception: {str(e)}")
    
    def _parse_search_response(self, query: str, response: str) -> SearchResult:
        """Gemini 웹 검색 응답 구조화 파싱
        
        비즈니스 로직:
        - Structured Output으로 수신된 JSON 형태의 검색 결과를 SearchResult 객체로 변환
        - tips, contacts, links, price, location 등 다양한 정보 유형 처리
        - JSON 파싱 실패 시 원본 컨텐츠를 폴백 데이터로 활용
        - 링크 정보를 sources 배열로 추출하여 손막 추적
        - 모든 경우에 유효한 SearchResult 객체 반환 보장
        """
        try:
            if not response or not response.strip():
                return create_error_result(query, "Empty response")
            
            content = response.strip()
            logger.debug(f"Parsing structured output response: {content[:200]}...")
            
            # Structured Output으로 인해 이미 올바른 JSON 형식이어야 함
            try:
                structured_data = json.loads(content)
                logger.info(f"Successfully parsed structured JSON response for query: {query[:50]}...")
                
                # 응답 구조 검증
                if not isinstance(structured_data, dict):
                    logger.warning("Response is not a dictionary, using as-is")
                    structured_data = {"tips": [content], "contacts": [], "links": [], "price": None, "location": None}
                
                # 링크 정보를 sources로 변환
                sources = []
                if "links" in structured_data and isinstance(structured_data["links"], list):
                    for link in structured_data["links"]:
                        if isinstance(link, dict) and "url" in link:
                            sources.append(link["url"])
                        elif isinstance(link, str):
                            sources.append(link)
                
                return SearchResult(
                    query=query,
                    content=json.dumps(structured_data, ensure_ascii=False),
                    sources=sources,
                    success=True
                )
                
            except json.JSONDecodeError as json_err:
                logger.warning(f"Failed to parse structured JSON for query '{query}': {json_err}")
                logger.warning(f"Raw content: {content[:200]}...")
                
                # Structured Output 실패시 폴백
                fallback_data = {
                    "tips": [content] if content else ["정보를 찾을 수 없습니다."],
                    "contacts": [],
                    "links": [],
                    "price": None,
                    "location": None
                }
                
                return SearchResult(
                    query=query,
                    content=json.dumps(fallback_data, ensure_ascii=False),
                    sources=[],
                    success=True
                )
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini structured response for query '{query}': {str(e)}")
            return create_error_result(query, f"Parse error: {str(e)}")
    
    def generate_search_queries_from_checklist(
        self,
        checklist_items: List[str],
        goal: str,
        answers: List[Dict[str, Any]]
    ) -> List[str]:
        """체크리스트 아이템 기반 검색 쿼리 생성
        
        비즈니스 로직:
        - 생성된 체크리스트 아이템 각각을 검색 쿼리로 1:1 변환
        - 사용자의 목표와 답변 맥락을 고려한 쿼리 최적화
        - 각 아이템에 대해 구체적이고 실행 가능한 검색 쿼리 제공
        - 모든 체크리스트 아이템에 대한 쿼리 보장으로 완전한 검색 범위
        
        Args:
            checklist_items: 생성된 체크리스트 아이템 리스트
            goal: 사용자 목표
            answers: 사용자 답변 데이터
            
        Returns:
            List[str]: 검색 쿼리 리스트
        """
        logger.info("🎯 GEMINI 검색 쿼리 생성 시작")
        logger.info(f"   📋 체크리스트 아이템: {len(checklist_items)}개")
        logger.info(f"   🎯 목표: {goal[:50]}...")
        logger.info(f"   💬 답변: {len(answers)}개")
        
        # 체크리스트 아이템을 그대로 검색 쿼리로 사용 (1:1 매핑)
        search_queries = []
        
        for i, item in enumerate(checklist_items):
            if item and item.strip():
                # 체크리스트 아이템을 검색에 최적화된 형태로 변환
                # 예: "여행 보험 가입하기" -> "여행 보험 종류 비교 가입 방법"
                search_query = item.strip()
                
                # 기본적인 검색 키워드 최적화 (선택적)
                if "하기" in search_query:
                    search_query = search_query.replace("하기", "방법")
                if "준비" in search_query:
                    search_query += " 체크리스트"
                
                search_queries.append(search_query)
                logger.debug(f"   🔍 쿼리 {i+1}: {search_query}")
            else:
                logger.warning(f"   ⚠️  빈 체크리스트 아이템 건너뛰기: 인덱스 {i}")
        
        logger.info(f"✅ 1:1 매핑 완료: {len(checklist_items)}개 아이템 → {len(search_queries)}개 쿼리")
        
        if not search_queries:
            logger.error("🚨 생성된 검색 쿼리가 없습니다!")
            logger.error("   체크리스트 아이템이 비어있을 수 있습니다.")
        elif len(search_queries) != len(checklist_items):
            logger.warning(f"⚠️  쿼리 수 불일치: {len(checklist_items)}개 아이템 vs {len(search_queries)}개 쿼리")
        
        return search_queries