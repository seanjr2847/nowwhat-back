import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.schemas.questions import QuestionAnswersRequest, QuestionAnswersResponse, AnswerItemSchema
from app.services.gemini_service import gemini_service
from app.services.perplexity_service import perplexity_service
from app.crud.session import validate_session_basic
from app.models.database import Checklist, ChecklistItem, Answer, User
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
        """사용자 답변 데이터베이스 저장"""
        
        try:
            # 답변들을 Answer 모델로 변환하여 저장
            for answer_item in request.answers:
                # answer가 리스트인 경우 문자열로 변환
                answer_text = answer_item.answer
                if isinstance(answer_text, list):
                    answer_text = ", ".join(answer_text)
                
                # 임시로 question_id 생성 (실제로는 questions 테이블과 연동 필요)
                temp_question_id = f"q_{answer_item.questionIndex}_{user.id}"
                
                answer_record = Answer(
                    question_id=temp_question_id,
                    user_id=user.id,
                    answer=answer_text
                )
                
                db.add(answer_record)
            
            db.commit()
            logger.info(f"Saved {len(request.answers)} answers for user {user.id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save user answers: {str(e)}")
            raise ChecklistGenerationError("답변 저장에 실패했습니다")
    
    async def _generate_enhanced_checklist(
        self, 
        request: QuestionAnswersRequest
    ) -> List[str]:
        """AI 생성 + 검색 보강을 통한 체크리스트 생성"""
        
        try:
            # 병렬 실행: AI 체크리스트 생성 + 검색 쿼리 실행
            ai_task = self._generate_ai_checklist(request)
            search_task = self._perform_parallel_search(request)
            
            # 두 작업을 병렬로 실행
            ai_checklist, search_results = await asyncio.gather(ai_task, search_task)
            
            # 검색 결과를 활용하여 체크리스트 보강
            enhanced_checklist = await perplexity_service.enhance_checklist_with_search(
                ai_checklist, search_results
            )
            
            # 체크리스트 품질 검증 및 조정
            final_checklist = self._validate_and_adjust_checklist(enhanced_checklist)
            
            return final_checklist
            
        except Exception as e:
            logger.error(f"Enhanced checklist generation failed: {str(e)}")
            # 실패 시 기본 체크리스트 반환
            return await self._get_fallback_checklist(request)
    
    async def _generate_ai_checklist(self, request: QuestionAnswersRequest) -> List[str]:
        """Gemini AI를 통한 기본 체크리스트 생성"""
        
        try:
            # 답변 정보를 텍스트로 변환
            answer_context = self._format_answers_for_ai(request.answers)
            
            # Gemini에 체크리스트 생성 요청
            prompt = self._create_checklist_prompt(
                request.goal, 
                request.selectedIntent.title, 
                answer_context
            )
            
            # AI 호출 (기존 gemini_service 활용)
            checklist_items = await self._call_gemini_for_checklist(prompt)
            
            logger.info(f"Generated {len(checklist_items)} items via Gemini AI")
            return checklist_items
            
        except Exception as e:
            logger.error(f"AI checklist generation failed: {str(e)}")
            return self._get_default_checklist_template(request.selectedIntent.title)
    
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
                request.selectedIntent.title,
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
    
    async def _get_fallback_checklist(self, request: QuestionAnswersRequest) -> List[str]:
        """모든 생성 방법 실패 시 사용할 폴백 체크리스트"""
        
        logger.warning("Using fallback checklist due to generation failures")
        return self._get_default_checklist_template(request.selectedIntent.title)
    
    async def _save_final_checklist(
        self,
        request: QuestionAnswersRequest,
        checklist_items: List[str],
        user: User,
        db: Session
    ) -> str:
        """최종 체크리스트를 데이터베이스에 저장"""
        
        try:
            # 체크리스트 ID 생성
            checklist_id = self._generate_checklist_id()
            
            # Checklist 레코드 생성
            checklist = Checklist(
                id=checklist_id,
                title=f"{request.selectedIntent.title}: {request.goal}",
                description=f"'{request.goal}' 목표 달성을 위한 맞춤형 체크리스트",
                category=request.selectedIntent.title,
                progress=0.0,
                is_public=True,
                user_id=user.id
            )
            
            db.add(checklist)
            db.flush()  # ID를 얻기 위해 flush
            
            # ChecklistItem 레코드들 생성
            for order, item_text in enumerate(checklist_items):
                item = ChecklistItem(
                    checklist_id=checklist.id,
                    text=item_text,
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

# 서비스 인스턴스
checklist_orchestrator = ChecklistOrchestrator()