import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.schemas.questions import QuestionAnswersRequest, QuestionAnswersResponse, AnswerItemSchema
from app.services.gemini_service import gemini_service
from app.services.perplexity_service import perplexity_service
from app.crud.session import validate_session_basic, save_user_answers_to_session
from app.models.database import Checklist, ChecklistItem, User
from app.core.database import get_db

logger = logging.getLogger(__name__)

class ChecklistGenerationError(Exception):
    """체크리스트 생성 관련 예외"""
    pass

class ChecklistOrchestrator:
    """체크리스트 생성을 위한 전체 워크플로우 오케스트레이션"""
    
    def __init__(self):
        self.min_checklist_items = 8
        self.max_checklist_items = 15
        
    async def process_answers_to_checklist(
        self,
        request: QuestionAnswersRequest,
        user: User,
        db: Session
    ) -> QuestionAnswersResponse:
        """전체 답변 처리 및 체크리스트 생성 워크플로우"""
        
        try:
            logger.info(f"Starting checklist generation for user {user.id}")
            
            # 1. 세션 검증 (현재는 생략, 향후 sessionId 기반 검증 추가 가능)
            # session_validation_result = self._validate_session(request, user, db)
            
            # 2. 답변 저장
            await self._save_user_answers(request, user, db)
            
            # 3. AI 체크리스트 생성 및 검색 병렬 실행
            checklist_items = await self._generate_enhanced_checklist(request)
            
            # 4. 최종 체크리스트 저장 및 ID 생성
            checklist_id = await self._save_final_checklist(
                request, checklist_items, user, db
            )
            
            # 5. 응답 생성
            redirect_url = f"/result/{checklist_id}"
            
            logger.info(f"Successfully generated checklist {checklist_id} with {len(checklist_items)} items")
            
            return QuestionAnswersResponse(
                checklistId=checklist_id,
                redirectUrl=redirect_url
            )
            
        except Exception as e:
            logger.error(f"Checklist generation failed: {str(e)}")
            raise ChecklistGenerationError(f"체크리스트 생성에 실패했습니다: {str(e)}")
    
    async def _save_user_answers(
        self, 
        request: QuestionAnswersRequest, 
        user: User, 
        db: Session
    ) -> None:
        """사용자 답변을 IntentSession에 저장 (기존 구조 활용)"""
        
        try:
            # 답변 데이터를 딕셔너리로 변환
            answers_dict = []
            for answer_item in request.answers:
                answer_text = answer_item.answer
                if isinstance(answer_text, list):
                    answer_text = ", ".join(answer_text)
                
                answers_dict.append({
                    "questionIndex": answer_item.questionIndex,
                    "questionText": answer_item.questionText,
                    "answer": answer_text
                })
            
            # 기존 IntentSession 구조를 활용하여 답변 저장
            session_id = save_user_answers_to_session(
                db=db,
                goal=request.goal,
                selected_intent=request.selectedIntent,
                answers=answers_dict,
                user_id=user.id
            )
            
            if session_id:
                logger.info(f"Saved {len(request.answers)} answers to IntentSession {session_id} for user {user.id}")
            else:
                logger.warning(f"No matching session found for goal: {request.goal}")
            
        except Exception as e:
            logger.error(f"Failed to save user answers: {str(e)}")
            raise ChecklistGenerationError("답변 저장에 실패했습니다")
    
    async def _generate_enhanced_checklist(
        self, 
        request: QuestionAnswersRequest
    ) -> List[Dict[str, str]]:
        """AI 생성 + 검색 보강을 통한 체크리스트 생성 (description 포함)"""
        
        try:
            # 병렬 실행: AI 체크리스트 생성 + 검색 쿼리 실행
            ai_task = self._generate_ai_checklist(request)
            search_task = self._perform_parallel_search(request)
            
            # 두 작업을 병렬로 실행
            ai_checklist, search_results = await asyncio.gather(ai_task, search_task)
            
            # 체크리스트 아이템별로 관련 검색 결과를 description으로 매칭
            enhanced_items = await self._match_search_results_to_items(ai_checklist, search_results)
            
            # 체크리스트 품질 검증 및 조정
            final_items = self._validate_and_adjust_enhanced_items(enhanced_items)
            
            return final_items
            
        except Exception as e:
            logger.error(f"Enhanced checklist generation failed: {str(e)}")
            # 실패 시 기본 체크리스트 반환
            fallback_checklist = await self._get_fallback_checklist(request)
            return [{"text": item, "description": ""} for item in fallback_checklist]
    
    async def _generate_ai_checklist(self, request: QuestionAnswersRequest) -> List[str]:
        """Gemini AI를 통한 기본 체크리스트 생성"""
        
        try:
            # 답변 정보를 텍스트로 변환
            answer_context = self._format_answers_for_ai(request.answers)
            
            # Gemini에 체크리스트 생성 요청
            prompt = self._create_checklist_prompt(
                request.goal, 
                request.selectedIntent, 
                answer_context
            )
            
            # AI 호출 (기존 gemini_service 활용)
            checklist_items = await self._call_gemini_for_checklist(prompt)
            
            logger.info(f"Generated {len(checklist_items)} items via Gemini AI")
            return checklist_items
            
        except Exception as e:
            logger.error(f"AI checklist generation failed: {str(e)}")
            return self._get_default_checklist_template(request.selectedIntent)
    
    async def _perform_parallel_search(self, request: QuestionAnswersRequest):
        """병렬 검색 실행"""
        
        try:
            # 답변을 딕셔너리 형태로 변환
            answers_dict = [
                {
                    "questionIndex": item.questionIndex,
                    "questionText": item.questionText,
                    "answer": item.answer
                }
                for item in request.answers
            ]
            
            # 검색 쿼리 생성
            search_queries = perplexity_service.generate_search_queries(
                request.goal,
                request.selectedIntent,
                answers_dict
            )
            
            # 병렬 검색 실행
            search_results = await perplexity_service.parallel_search(search_queries)
            
            success_count = sum(1 for r in search_results if r.success)
            logger.info(f"Parallel search completed: {success_count}/{len(search_queries)} successful")
            
            return search_results
            
        except Exception as e:
            logger.error(f"Parallel search failed: {str(e)}")
            return []
    
    def _create_checklist_prompt(
        self, 
        goal: str, 
        intent_title: str, 
        answer_context: str
    ) -> str:
        """체크리스트 생성용 프롬프트 생성"""
        
        return f"""당신은 개인 맞춤형 체크리스트 생성 전문가입니다.

사용자 정보:
- 목표: "{goal}"
- 선택한 의도: "{intent_title}"
- 답변 내용: {answer_context}

위 정보를 바탕으로 사용자가 목표를 달성하기 위한 체계적인 체크리스트를 생성하세요.

체크리스트 생성 규칙:
1. 시간순으로 정렬된 실행 가능한 항목들
2. 구체적이고 측정 가능한 액션 아이템
3. {self.min_checklist_items}개 이상 {self.max_checklist_items}개 이하
4. 각 항목은 한 문장으로 명확하게 표현
5. 우선순위를 고려한 순서 배열

응답 형식:
- 각 항목을 새 줄로 구분
- 번호나 불릿 포인트 없이 순수 텍스트만
- 예: "여권 유효기간 확인하기"

중요: 사용자의 구체적인 답변 내용을 반영하여 개인화된 체크리스트를 만드세요."""
    
    async def _call_gemini_for_checklist(self, prompt: str) -> List[str]:
        """Gemini API 호출하여 체크리스트 생성"""
        
        try:
            # gemini_service의 기존 API 호출 메서드 활용
            response = await gemini_service._call_gemini_api(prompt)
            
            # 응답 파싱
            checklist_items = self._parse_checklist_response(response)
            
            return checklist_items
            
        except Exception as e:
            logger.error(f"Gemini API call for checklist failed: {str(e)}")
            raise
    
    def _parse_checklist_response(self, response: str) -> List[str]:
        """Gemini 체크리스트 응답 파싱"""
        
        try:
            # 응답에서 체크리스트 항목 추출
            lines = response.strip().split('\n')
            
            checklist_items = []
            for line in lines:
                line = line.strip()
                
                # 빈 줄 제거
                if not line:
                    continue
                
                # 번호나 불릿 포인트 제거
                line = self._clean_checklist_item(line)
                
                # 최소 길이 체크
                if len(line) > 5:
                    checklist_items.append(line)
            
            return checklist_items
            
        except Exception as e:
            logger.error(f"Failed to parse checklist response: {str(e)}")
            raise
    
    def _clean_checklist_item(self, item: str) -> str:
        """체크리스트 항목 정리"""
        
        # 숫자, 불릿 포인트, 대시 등 제거
        import re
        
        # 패턴들 제거
        patterns = [
            r'^\d+\.?\s*',  # 1. 또는 1
            r'^[-*•]\s*',   # - 또는 * 또는 •
            r'^[\[\]]\s*',  # [ ] 체크박스
            r'^□\s*',       # 빈 체크박스
            r'^✓\s*',       # 체크 마크
        ]
        
        for pattern in patterns:
            item = re.sub(pattern, '', item)
        
        return item.strip()
    
    def _format_answers_for_ai(self, answers: List[AnswerItemSchema]) -> str:
        """답변들을 AI가 이해할 수 있는 형태로 포맷팅"""
        
        formatted_parts = []
        
        for answer_item in answers:
            question = answer_item.questionText
            answer = answer_item.answer
            
            if isinstance(answer, list):
                answer = ", ".join(answer)
            
            formatted_parts.append(f"Q: {question} → A: {answer}")
        
        return " | ".join(formatted_parts)
    
    def _validate_and_adjust_checklist(self, checklist: List[str]) -> List[str]:
        """체크리스트 품질 검증 및 조정"""
        
        # 중복 제거
        unique_items = []
        seen = set()
        
        for item in checklist:
            item_lower = item.lower().strip()
            if item_lower not in seen and len(item) > 5:
                unique_items.append(item)
                seen.add(item_lower)
        
        # 개수 조정
        if len(unique_items) < self.min_checklist_items:
            logger.warning(f"Checklist has only {len(unique_items)} items, adding default items")
            # 부족한 경우 기본 항목 추가
            unique_items.extend(self._get_additional_items(len(unique_items)))
        
        elif len(unique_items) > self.max_checklist_items:
            logger.info(f"Trimming checklist from {len(unique_items)} to {self.max_checklist_items} items")
            unique_items = unique_items[:self.max_checklist_items]
        
        return unique_items
    
    def _get_additional_items(self, current_count: int) -> List[str]:
        """부족한 체크리스트 항목을 위한 기본 항목들"""
        
        default_items = [
            "목표 달성 일정 계획하기",
            "필요한 자료 및 정보 수집하기", 
            "예산 계획 세우기",
            "관련 전문가나 경험자에게 조언 구하기",
            "진행 상황 체크포인트 설정하기",
            "예상 문제점 및 대안 준비하기",
            "최종 점검 및 검토하기"
        ]
        
        needed_count = self.min_checklist_items - current_count
        return default_items[:needed_count]
    
    def _get_default_checklist_template(self, intent_title: str) -> List[str]:
        """의도별 기본 체크리스트 템플릿"""
        
        templates = {
            "여행 계획": [
                "여행 날짜 확정하기",
                "여권 및 비자 확인하기", 
                "항공편 예약하기",
                "숙박시설 예약하기",
                "여행자보험 가입하기",
                "환전 및 카드 준비하기",
                "현지 교통편 조사하기",
                "관광지 정보 수집하기",
                "짐 싸기 체크리스트 만들기",
                "응급상황 대비책 준비하기"
            ],
            "계획 세우기": [
                "목표 구체화하기",
                "현재 상황 점검하기",
                "필요한 자원 파악하기",
                "단계별 실행 계획 수립하기",
                "일정표 작성하기",
                "예산 계획하기",
                "필요한 도구나 재료 준비하기",
                "중간 점검 일정 정하기",
                "예상 문제점 대비책 마련하기",
                "최종 목표 달성 기준 설정하기"
            ]
        }
        
        return templates.get(intent_title, templates["계획 세우기"])
    
    async def _match_search_results_to_items(
        self, 
        checklist_items: List[str], 
        search_results: List
    ) -> List[Dict[str, str]]:
        """체크리스트 아이템별로 관련 검색 결과를 description으로 매칭"""
        
        enhanced_items = []
        
        # 성공적인 검색 결과만 필터링
        successful_results = [r for r in search_results if hasattr(r, 'success') and r.success and r.content]
        
        if not successful_results:
            logger.warning("No successful search results to match with checklist items")
            return [{"text": item, "description": ""} for item in checklist_items]
        
        # 각 체크리스트 아이템에 대해 가장 관련성 높은 검색 결과 찾기
        for item in checklist_items:
            best_description = self._find_best_matching_description(item, successful_results)
            enhanced_items.append({
                "text": item,
                "description": best_description
            })
        
        success_count = sum(1 for item in enhanced_items if item["description"])
        logger.info(f"Matched descriptions for {success_count}/{len(checklist_items)} checklist items")
        
        return enhanced_items
    
    def _find_best_matching_description(self, checklist_item: str, search_results: List) -> str:
        """체크리스트 아이템에 가장 적합한 검색 결과 찾기"""
        
        item_keywords = self._extract_keywords_from_item(checklist_item)
        best_match = ""
        best_score = 0
        
        for result in search_results:
            if not hasattr(result, 'content') or not result.content:
                continue
            
            # 검색 결과에서 실용적인 팁 추출
            tips = self._extract_practical_tips_from_content(result.content)
            
            for tip in tips:
                score = self._calculate_relevance_score(item_keywords, tip)
                if score > best_score and len(tip) > 20:
                    best_score = score
                    best_match = tip
        
        # 적절한 길이로 자르기 (API 응답에서 너무 길지 않게)
        if best_match and len(best_match) > 150:
            best_match = best_match[:147] + "..."
        
        return best_match
    
    def _extract_keywords_from_item(self, item: str) -> List[str]:
        """체크리스트 아이템에서 핵심 키워드 추출 (개선된 버전)"""
        import re
        
        # 확장된 불용어 리스트
        stopwords = [
            '을', '를', '이', '가', '은', '는', '의', '에', '에서', '와', '과', 
            '하기', '하세요', '합니다', '있는', '있다', '되는', '되다', '위한', '위해',
            '통해', '대한', '대해', '같은', '같이', '함께', '모든', '각각', '그리고'
        ]
        
        # 중요한 키워드를 우선적으로 추출
        important_patterns = [
            r'학습|공부|연습|훈련',
            r'준비|계획|예약|신청',
            r'구매|선택|결정|확인',
            r'언어|영어|중국어|일본어|스페인어|프랑스어',
            r'교재|책|앱|강의|수업',
            r'파트너|친구|그룹|팀',
            r'예산|비용|돈|가격'
        ]
        
        keywords = []
        
        # 중요 패턴 먼저 추출
        for pattern in important_patterns:
            matches = re.findall(pattern, item)
            keywords.extend(matches)
        
        # 일반 단어 추출 (한글, 영어, 숫자)
        words = re.findall(r'[가-힣a-zA-Z0-9]+', item)
        for word in words:
            if word not in stopwords and len(word) > 1 and word not in keywords:
                keywords.append(word)
        
        # 중복 제거 및 상위 키워드 반환
        unique_keywords = list(dict.fromkeys(keywords))  # 순서 유지하며 중복 제거
        return unique_keywords[:7]  # 상위 7개 키워드
    
    def _extract_practical_tips_from_content(self, content: str) -> List[str]:
        """검색 결과에서 실용적인 팁 추출 (개선된 버전)"""
        # 다양한 문장 구분자로 분리
        import re
        sentences = re.split(r'[.!?]\s+|[\n\r]+', content.replace('\\n', '\n'))
        tips = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15 or len(sentence) > 180:
                continue
            
            # 실용적인 팁의 특징을 가진 문장 찾기 (확장된 패턴)
            practical_patterns = [
                r'(추천|권장|제안).*\w+',
                r'(필요|준비|확인|체크).*\w+',
                r'(예약|구매|신청|등록).*\w+',
                r'(방법|방식|팁|노하우).*\w+',
                r'(주의|조심|유의).*\w+',
                r'(중요|필수|핵심).*\w+',
                r'(선택|결정|고려).*\w+',
                r'(학습|공부|연습).*\w+',
                r'(무료|할인|저렴).*\w+',
                r'(\d+원|\d+달러|예산|비용).*\w+'
            ]
            
            # 패턴 매칭 점수 계산
            score = 0
            for pattern in practical_patterns:
                if re.search(pattern, sentence):
                    score += 1
            
            # 추가 점수 - URL 링크나 구체적 정보 포함
            if re.search(r'https?://|www\.|\.com|\.kr', sentence):
                score += 2
            if re.search(r'\d+', sentence):  # 숫자 포함
                score += 1
            
            # 점수가 높은 문장만 선택
            if score >= 1:
                # 불필요한 문구 정리
                cleaned_sentence = self._clean_tip_sentence(sentence)
                if cleaned_sentence:
                    tips.append((cleaned_sentence, score))
        
        # 점수 순으로 정렬 후 상위 3개 반환
        tips.sort(key=lambda x: x[1], reverse=True)
        return [tip[0] for tip in tips[:4]]  # 최대 4개 팁
    
    def _clean_tip_sentence(self, sentence: str) -> str:
        """팁 문장 정리"""
        import re
        
        # 불필요한 문구 제거
        sentence = re.sub(r'^(또한|그리고|따라서|하지만|그러나)\s*', '', sentence)
        sentence = re.sub(r'\s*(입니다|습니다|해요|해야|됩니다)\.?$', '', sentence)
        
        # 너무 짧거나 의미없는 문장 필터링
        if len(sentence) < 10:
            return ""
        
        # 첫 글자 대문자 처리 (영어인 경우)
        if sentence and sentence[0].islower():
            sentence = sentence[0].upper() + sentence[1:]
        
        return sentence.strip()
    
    def _calculate_relevance_score(self, item_keywords: List[str], tip: str) -> float:
        """아이템 키워드와 팁의 관련성 점수 계산 (개선된 가중치 적용)"""
        if not item_keywords:
            return 0.0
        
        score = 0.0
        tip_lower = tip.lower()
        
        for i, keyword in enumerate(item_keywords):
            keyword_lower = keyword.lower()
            
            if keyword_lower in tip_lower:
                # 키워드 위치에 따른 가중치 (앞쪽 키워드가 더 중요)
                position_weight = 1.0 - (i * 0.1)
                
                # 키워드 길이에 따른 가중치 (긴 키워드가 더 중요)
                length_weight = min(len(keyword) / 5.0, 2.0)
                
                # 키워드가 단어 경계에서 매칭되는지 확인 (부분 매칭 vs 완전 매칭)
                import re
                if re.search(r'\b' + re.escape(keyword_lower) + r'\b', tip_lower):
                    boundary_weight = 1.5  # 완전 매칭에 더 높은 점수
                else:
                    boundary_weight = 1.0  # 부분 매칭
                
                keyword_score = position_weight * length_weight * boundary_weight
                score += keyword_score
        
        # 정규화 (최대 점수로 나누기)
        max_possible_score = sum(1.0 * min(len(kw) / 5.0, 2.0) * 1.5 for kw in item_keywords)
        normalized_score = score / max_possible_score if max_possible_score > 0 else 0.0
        
        return min(normalized_score, 1.0)  # 최대 1.0으로 제한
    
    def _validate_and_adjust_enhanced_items(self, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """향상된 체크리스트 아이템들의 품질 검증 및 조정"""
        
        # 중복 제거
        unique_items = []
        seen_texts = set()
        
        for item in items:
            text = item["text"].strip()
            if text and text not in seen_texts:
                unique_items.append(item)
                seen_texts.add(text)
        
        # 길이 조정
        if len(unique_items) < self.min_checklist_items:
            needed_count = self.min_checklist_items - len(unique_items)
            default_items = self._get_default_items_for_padding()
            for i in range(min(needed_count, len(default_items))):
                unique_items.append({
                    "text": default_items[i],
                    "description": ""
                })
        elif len(unique_items) > self.max_checklist_items:
            unique_items = unique_items[:self.max_checklist_items]
        
        return unique_items
    
    async def _get_fallback_checklist(self, request: QuestionAnswersRequest) -> List[str]:
        """모든 생성 방법 실패 시 사용할 폴백 체크리스트"""
        
        logger.warning("Using fallback checklist due to generation failures")
        return self._get_default_checklist_template(request.selectedIntent)
    
    async def _save_final_checklist(
        self,
        request: QuestionAnswersRequest,
        checklist_items: List[Dict[str, str]],
        user: User,
        db: Session
    ) -> str:
        """최종 체크리스트를 데이터베이스에 저장"""
        
        try:
            # 체크리스트 ID 생성
            checklist_id = self._generate_checklist_id()
            
            # 답변 정보를 description에 포함 (임시 해결책)
            answer_summary = self._format_answers_for_description(request.answers)
            
            # Checklist 레코드 생성
            checklist = Checklist(
                id=checklist_id,
                title=f"{request.selectedIntent}: {request.goal}",
                description=f"'{request.goal}' 목표 달성을 위한 맞춤형 체크리스트\n\n답변 요약:\n{answer_summary}",
                category=request.selectedIntent,
                progress=0.0,
                is_public=True,
                user_id=user.id
            )
            
            db.add(checklist)
            db.flush()  # ID를 얻기 위해 flush
            
            # ChecklistItem 레코드들 생성 (description 포함)
            for order, item_data in enumerate(checklist_items):
                # item_data가 딕셔너리인 경우와 문자열인 경우 모두 처리
                if isinstance(item_data, dict):
                    text = item_data.get("text", "")
                    # description은 아직 데이터베이스 모델에 없으므로 로깅만
                    description = item_data.get("description", "")
                    if description:
                        logger.info(f"Item '{text[:30]}...' has description: {description[:50]}...")
                else:
                    text = str(item_data)
                
                item = ChecklistItem(
                    checklist_id=checklist.id,
                    text=text,
                    is_completed=False,
                    order=order
                )
                db.add(item)
            
            db.commit()
            
            logger.info(f"Saved checklist {checklist_id} with {len(checklist_items)} items")
            return checklist_id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save checklist: {str(e)}")
            raise ChecklistGenerationError("체크리스트 저장에 실패했습니다")
    
    def _generate_checklist_id(self) -> str:
        """체크리스트 ID 생성 (cl_{timestamp}_{random})"""
        
        timestamp = int(datetime.now().timestamp())
        random_part = str(uuid.uuid4())[:8]
        
        return f"cl_{timestamp}_{random_part}"
    
    def _format_answers_for_description(self, answers: List[AnswerItemSchema]) -> str:
        """답변들을 설명 텍스트로 포맷팅"""
        
        formatted_parts = []
        
        for answer_item in answers:
            question = answer_item.questionText
            answer = answer_item.answer
            
            if isinstance(answer, list):
                answer = ", ".join(answer)
            
            formatted_parts.append(f"• {question}: {answer}")
        
        return "\n".join(formatted_parts)

# 서비스 인스턴스
checklist_orchestrator = ChecklistOrchestrator()