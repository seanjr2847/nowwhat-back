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
        self.max_concurrent_searches = getattr(settings, 'MAX_CONCURRENT_SEARCHES', 5)  # 10 -> 5로 줄임
        self.timeout_seconds = getattr(settings, 'SEARCH_TIMEOUT_SECONDS', 15)
        
        # 상세한 초기화 로깅
        logger.info("=" * 60)
        logger.info("🔍 PERPLEXITY SERVICE 초기화")
        logger.info("=" * 60)
        
        # API 키 상태 로깅
        if not self.api_key:
            logger.error("🚨 PERPLEXITY_API_KEY not found in environment variables!")
            logger.error("   ❌ 체크리스트 아이템에 details가 추가되지 않습니다.")
            logger.error("   💡 환경변수 PERPLEXITY_API_KEY를 설정해주세요.")
            logger.error("   📝 예시: export PERPLEXITY_API_KEY=pplx-xxxxx")
        else:
            logger.info(f"✅ Perplexity API 키 확인됨")
            logger.info(f"   🔑 키 길이: {len(self.api_key)} 문자")
            logger.info(f"   🌐 API URL: {self.api_url}")
            logger.info(f"   ⚡ 최대 동시 검색: {self.max_concurrent_searches}개")
            logger.info(f"   ⏱️  검색 타임아웃: {self.timeout_seconds}초")
        
        logger.info("=" * 60)
    
    async def parallel_search(self, queries: List[str]) -> List[SearchResult]:
        """10개의 검색 쿼리를 병렬로 실행"""
        logger.info("🚀 PERPLEXITY 병렬 검색 시작")
        logger.info(f"   📝 요청된 쿼리 수: {len(queries)}개")
        
        if not queries:
            logger.warning("⚠️  검색 쿼리가 비어있습니다")
            return []
        
        # 쿼리 내용 로깅
        for i, query in enumerate(queries[:5]):  # 처음 5개만 로깅
            logger.info(f"   🔍 쿼리 {i+1}: {query}")
        if len(queries) > 5:
            logger.info(f"   ... 그 외 {len(queries) - 5}개 더")
        
        if not self.api_key:
            logger.error("🚨 PERPLEXITY API 키가 없어 검색을 건너뜁니다")
            logger.error("   ❌ 모든 검색이 실패 처리됩니다")
            return [self._create_empty_result(query) for query in queries]
        
        # 최대 동시 검색 수 제한
        limited_queries = queries[:self.max_concurrent_searches]
        if len(queries) > self.max_concurrent_searches:
            logger.warning(f"⚠️  쿼리 수 제한: {len(queries)} → {len(limited_queries)}개")
        
        try:
            logger.info(f"⚡ {len(limited_queries)}개 쿼리 병렬 실행 중...")
            
            # 병렬 검색 실행
            tasks = [self._search_single_query(query) for query in limited_queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리 및 결과 정리
            processed_results = []
            success_queries = []
            failed_queries = []
            
            for i, result in enumerate(results):
                query = limited_queries[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ 검색 실패 [{i+1}]: '{query[:50]}...' - {str(result)}")
                    processed_results.append(self._create_error_result(query, str(result)))
                    failed_queries.append(query)
                else:
                    if result.success:
                        logger.info(f"✅ 검색 성공 [{i+1}]: '{query[:50]}...' ({len(result.content)}자)")
                        success_queries.append(query)
                    else:
                        logger.warning(f"⚠️  검색 실패 [{i+1}]: '{query[:50]}...' - {result.error_message}")
                        failed_queries.append(query)
                    processed_results.append(result)
            
            success_count = len(success_queries)
            failed_count = len(failed_queries)
            
            # 결과 요약
            logger.info("=" * 60)
            logger.info("📊 PERPLEXITY 검색 결과 요약")
            logger.info("=" * 60)
            logger.info(f"✅ 성공: {success_count}개")
            logger.info(f"❌ 실패: {failed_count}개")
            logger.info(f"📈 성공률: {(success_count/len(limited_queries)*100):.1f}%")
            
            if success_count > 0:
                # 성공한 검색 결과의 내용 길이 통계
                content_lengths = [len(r.content) for r in processed_results if r.success and r.content]
                if content_lengths:
                    avg_length = sum(content_lengths) / len(content_lengths)
                    min_length = min(content_lengths)
                    max_length = max(content_lengths)
                    logger.info(f"📏 응답 길이: 평균 {avg_length:.0f}자 (최소 {min_length}, 최대 {max_length})")
                
                # 성공한 쿼리 몇 개 예시
                for query in success_queries[:3]:
                    logger.info(f"   ✅ '{query[:40]}...'")
            
            if failed_count > 0:
                logger.warning(f"⚠️  실패한 쿼리 {min(3, failed_count)}개 예시:")
                for query in failed_queries[:3]:
                    logger.warning(f"   ❌ '{query[:40]}...'")
            
            logger.info("=" * 60)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"💥 병렬 검색 전체 실패: {str(e)}")
            logger.error(f"   🔄 모든 쿼리를 실패 처리합니다")
            return [self._create_error_result(query, str(e)) for query in limited_queries]
    
    async def _search_single_query(self, query: str) -> SearchResult:
        """단일 검색 쿼리 실행"""
        start_time = asyncio.get_event_loop().time()
        logger.debug(f"🔍 단일 검색 시작: '{query[:50]}...'")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a helpful assistant that provides structured information. 
                        Always respond in JSON format with the following structure:
                        {
                            "tips": ["practical tip 1", "practical tip 2"],
                            "contacts": [{"name": "contact name", "phone": "phone number", "email": "email"}],
                            "links": [{"title": "link description", "url": "https://..."}],
                            "price": "price information or null",
                            "location": "location/address information or null"
                        }
                        Include only relevant, accurate information. Use null for missing data."""
                    },
                    {
                        "role": "user", 
                        "content": f"{query} (한국어로 답변해주세요. JSON 형식으로만 응답하세요.)"
                    }
                ],
                "max_tokens": 1000,  # 500 -> 1000으로 늘림
                "temperature": 0.1,  # 더 일관성 있게
                "stream": False
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.debug(f"📡 API 요청 전송 중: {self.api_url}")
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    if response.status == 200:
                        logger.debug(f"✅ API 응답 수신 ({elapsed:.2f}초): '{query[:30]}...'")
                        data = await response.json()
                        result = self._parse_perplexity_response(query, data)
                        
                        if result.success:
                            logger.debug(f"✅ 파싱 성공: {len(result.content)}자 응답")
                        else:
                            logger.warning(f"⚠️  파싱 실패: {result.error_message}")
                        
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"🚨 Perplexity API 오류 {response.status}")
                        logger.error(f"   쿼리: '{query[:50]}...'")
                        logger.error(f"   응답: {error_text[:200]}...")
                        logger.error(f"   소요시간: {elapsed:.2f}초")
                        
                        return self._create_error_result(query, f"API error {response.status}: {error_text[:100]}")
                        
        except asyncio.TimeoutError:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"⏰ 검색 타임아웃 ({elapsed:.2f}초)")
            logger.error(f"   쿼리: '{query[:50]}...'")
            logger.error(f"   타임아웃 설정: {self.timeout_seconds}초")
            return self._create_error_result(query, f"Search timeout after {elapsed:.2f}s")
        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"💥 검색 예외 발생 ({elapsed:.2f}초)")
            logger.error(f"   쿼리: '{query[:50]}...'")
            logger.error(f"   오류: {str(e)}")
            return self._create_error_result(query, f"Exception: {str(e)}")
    
    def _parse_perplexity_response(self, query: str, data: Dict[str, Any]) -> SearchResult:
        """Perplexity API 응답 파싱 (JSON 구조화된 응답)"""
        try:
            if "choices" not in data or not data["choices"]:
                return self._create_error_result(query, "No choices in response")
            
            choice = data["choices"][0]
            if "message" not in choice:
                return self._create_error_result(query, "No message in choice")
            
            content = choice["message"].get("content", "").strip()
            if not content:
                return self._create_error_result(query, "Empty content in response")
            
            # JSON 파싱 시도
            try:
                import json
                # JSON 부분만 추출 (```json ... ``` 형태로 올 수 있음)
                json_content = content
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    if end != -1:
                        json_content = content[start:end].strip()
                elif "{" in content:
                    # 첫 번째 { 부터 마지막 } 까지 추출
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start != -1 and end > start:
                        json_content = content[start:end]
                
                # 잘린 JSON 복구 시도
                if json_content.count('"') % 2 != 0:
                    # 홀수개의 따옴표가 있으면 문자열이 잘림
                    json_content += '"'
                
                # 열린 배열/객체 닫기
                open_brackets = json_content.count('[') - json_content.count(']')
                open_braces = json_content.count('{') - json_content.count('}')
                
                if open_brackets > 0:
                    json_content += ']' * open_brackets
                if open_braces > 0:
                    json_content += '}' * open_braces
                
                structured_data = json.loads(json_content)
                logger.info(f"Successfully parsed JSON response for query: {query[:50]}...")
                
                return SearchResult(
                    query=query,
                    content=json.dumps(structured_data),  # 구조화된 데이터를 JSON 문자열로
                    sources=structured_data.get("links", []),
                    success=True
                )
                
            except json.JSONDecodeError as json_err:
                logger.warning(f"Failed to parse JSON for query '{query}': {json_err}")
                logger.warning(f"Raw content: {content[:200]}...")
                # JSON 파싱 실패시 기존 텍스트 방식으로 폴백
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
        
        logger.info("🎯 PERPLEXITY 검색 쿼리 생성 시작")
        logger.info(f"   📋 체크리스트 아이템: {len(checklist_items)}개")
        logger.info(f"   🎯 목표: {goal[:50]}...")
        logger.info(f"   💬 답변: {len(answers)}개")
        
        # 답변에서 핵심 컨텍스트 추출
        answer_context = self._extract_answer_context(answers)
        logger.info(f"   🔍 추출된 컨텍스트: '{answer_context[:80]}...' ({len(answer_context)}자)")
        
        search_queries = []
        
        # 각 체크리스트 아이템을 기반으로 검색 쿼리 생성
        processed_items = checklist_items[:10]  # 최대 10개 아이템
        logger.info(f"   📝 처리할 아이템: {len(processed_items)}개")
        
        for i, item in enumerate(processed_items):
            logger.debug(f"   🔍 아이템 {i+1} 처리: '{item[:50]}...'")
            
            # 아이템에서 핵심 키워드 추출
            core_keywords = self._extract_core_keywords_from_item(item)
            logger.debug(f"      키워드: {core_keywords}")
            
            if core_keywords:
                # 여러 패턴의 검색 쿼리 생성
                queries = self._generate_item_specific_queries(core_keywords, answer_context)
                logger.debug(f"      생성된 쿼리: {queries}")
                search_queries.extend(queries)
            else:
                logger.warning(f"      ⚠️  키워드 추출 실패: '{item[:30]}...'")
        
        # 중복 제거 및 길이 제한
        unique_queries = list(dict.fromkeys(search_queries))[:15]  # 최대 15개
        
        logger.info("=" * 50)
        logger.info("📝 생성된 검색 쿼리 목록")
        logger.info("=" * 50)
        for i, query in enumerate(unique_queries):
            logger.info(f"   {i+1:2d}. {query}")
        logger.info("=" * 50)
        
        logger.info(f"✅ 쿼리 생성 완료: {len(search_queries)} → {len(unique_queries)}개 (중복 제거)")
        
        if not unique_queries:
            logger.error("🚨 생성된 검색 쿼리가 없습니다!")
            logger.error("   체크리스트 아이템에서 키워드 추출이 실패했을 수 있습니다.")
        
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