from fastapi import APIRouter, HTTPException, Depends
from app.schemas.nowwhat import Question, QuestionGenerateResponse, AnswerRequest, APIResponse
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/generate/{intent_id}", response_model=QuestionGenerateResponse)
async def generate_questions(intent_id: str, current_user=Depends(get_current_user)):
    """선택한 의도의 맞춤 질문 조회 - 3-5개 질문"""
    try:
        # TODO: 실제 질문 생성 로직
        # 1. intent_id로 의도 정보 조회
        # 2. AI를 통한 맞춤 질문 생성
        # 3. 3-5개 질문 반환
        
        # 임시 질문 목록
        sample_questions = [
            Question(
                id="q1",
                text="하루에 몇 시간 정도 운동할 시간이 있나요?",
                type="single",
                options=["30분 미만", "30분-1시간", "1-2시간", "2시간 이상"],
                category="time"
            ),
            Question(
                id="q2", 
                text="선호하는 운동 유형은 무엇인가요? (복수 선택 가능)",
                type="multiple",
                options=["유산소", "근력운동", "요가/필라테스", "팀스포츠", "야외활동"],
                category="preference"
            ),
            Question(
                id="q3",
                text="현재 운동 경험 수준은 어느 정도인가요?",
                type="single",
                options=["초보자", "중급자", "상급자", "전문가"],
                category="level"
            ),
            Question(
                id="q4",
                text="운동을 통해 가장 달성하고 싶은 목표는?",
                type="single",
                options=["체중 감량", "근육 증가", "체력 향상", "건강 유지"],
                category="goal"
            )
        ]
        
        return QuestionGenerateResponse(
            success=True,
            message="맞춤 질문이 생성되었습니다.",
            data=sample_questions
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="의도를 찾을 수 없습니다.")

@router.post("/answer", response_model=APIResponse)
async def submit_answer(answer_data: AnswerRequest, current_user=Depends(get_current_user)):
    """질문 답변 제출 - 단일/다중 선택"""
    try:
        # TODO: 실제 답변 저장 로직
        # 1. 답변 유효성 검증
        # 2. DB에 답변 저장
        # 3. 답변 완료 시 체크리스트 생성 트리거
        
        return APIResponse(
            success=True,
            message="답변이 성공적으로 제출되었습니다.",
            data={"answerId": "answer_123", "timestamp": answer_data.answeredAt}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="답변 제출에 실패했습니다.")