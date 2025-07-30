# 데이터베이스 마이그레이션 가이드

## 문제 상황

현재 `Answer` 테이블이 `Question` 테이블과 외래키로 연결되어 있어서, 실제 `Question` 레코드 없이는 답변을 저장할 수 없습니다. 이는 POST `/questions/answer` 엔드포인트에서 "답변 저장에 실패했습니다" 오류를 발생시킵니다.

## 해결 방안

새로운 `SessionAnswer` 테이블을 생성하여 세션 기반 답변 저장을 지원합니다.

## 마이그레이션 실행

### 1. 마이그레이션 파일 확인

다음 파일이 생성되었는지 확인하세요:
```
alembic/versions/2025_07_30_0500-fix_answer_table_structure.py
```

### 2. 마이그레이션 실행

```bash
# 현재 마이그레이션 상태 확인
python -m alembic current

# 마이그레이션 실행
python -m alembic upgrade head

# 마이그레이션 성공 확인
python -m alembic current
```

### 3. 새 테이블 구조 확인

마이그레이션 후 다음 테이블이 생성됩니다:

```sql
CREATE TABLE session_answers (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    session_id VARCHAR,
    checklist_id VARCHAR REFERENCES checklists(id) ON DELETE CASCADE,
    goal TEXT NOT NULL,
    selected_intent VARCHAR NOT NULL,
    question_index INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_session_answers_user_id ON session_answers(user_id);
CREATE INDEX idx_session_answers_session_id ON session_answers(session_id);
CREATE INDEX idx_session_answers_checklist_id ON session_answers(checklist_id);
```

## 수정된 코드 동작 방식

### 1. 답변 저장 과정

1. **사용자 답변 접수**: POST `/questions/answer` 엔드포인트 호출
2. **SessionAnswer 생성**: 각 답변을 `session_answers` 테이블에 저장
3. **체크리스트 생성**: AI를 통한 체크리스트 생성
4. **연결 업데이트**: 생성된 체크리스트 ID로 `session_answers` 레코드 업데이트

### 2. 데이터 구조

```python
# 저장되는 데이터 예시
SessionAnswer(
    user_id="user_123",
    session_id=None,  # 현재는 사용하지 않음
    checklist_id="cl_1234567890_abc",  # 체크리스트 생성 후 업데이트
    goal="일본여행 가고싶어",
    selected_intent="여행 계획",
    question_index=0,
    question_text="여행 기간은 얼마나 되나요?",
    answer="3days"
)
```

## 테스트 방법

### 1. API 테스트

```bash
curl -X POST "http://localhost:8000/api/v1/questions/answer" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token" \
  -d '{
    "goal": "일본여행 가고싶어",
    "selectedIntent": "여행 계획",
    "answers": [
      {
        "questionIndex": 0,
        "questionText": "여행 기간은 얼마나 되나요?",
        "answer": "3days"
      }
    ]
  }'
```

### 2. 데이터베이스 확인

```sql
-- 저장된 답변 확인
SELECT * FROM session_answers 
WHERE goal = '일본여행 가고싶어' 
ORDER BY created_at DESC;

-- 생성된 체크리스트 확인
SELECT * FROM checklists 
WHERE title LIKE '%일본여행%' 
ORDER BY created_at DESC;

-- 체크리스트 아이템 확인
SELECT ci.* FROM checklist_items ci
JOIN checklists c ON ci.checklist_id = c.id
WHERE c.title LIKE '%일본여행%'
ORDER BY ci.order;
```

## 로그 확인

성공적인 실행 시 다음과 같은 로그가 출력됩니다:

```
INFO:app.services.checklist_orchestrator:Saved 3 answers to session_answers table for user user_123
INFO:app.services.checklist_orchestrator:Generated 8 items via Gemini AI
INFO:app.services.checklist_orchestrator:Saved checklist cl_1234567890_abc with 8 items and updated 3 session answers
```

## 문제 해결

### 마이그레이션 실패 시

```bash
# 마이그레이션 상태 확인
python -m alembic current

# 마이그레이션 기록 확인
python -m alembic history

# 특정 리비전으로 롤백 (필요한 경우)
python -m alembic downgrade [revision_id]
```

### 답변 저장 실패 시

1. **데이터베이스 연결 확인**
   ```bash
   # 데이터베이스 연결 테스트
   python -c "from app.core.database import get_db; next(get_db())"
   ```

2. **테이블 존재 확인**
   ```sql
   \dt session_answers
   ```

3. **권한 확인**
   - 데이터베이스 사용자가 테이블 생성/수정 권한이 있는지 확인

## 향후 개선 사항

1. **세션 ID 활용**: 실제 세션 기반 추적을 위한 session_id 활용
2. **Answer 테이블 정리**: 기존 Answer 테이블과의 관계 정리
3. **인덱스 최적화**: 쿼리 성능 향상을 위한 추가 인덱스
4. **데이터 보관 정책**: 오래된 session_answers 데이터 정리 정책 수립

## 배포 체크리스트

- [ ] 마이그레이션 파일 검토 완료
- [ ] 로컬 환경에서 마이그레이션 테스트 완료
- [ ] API 엔드포인트 테스트 완료
- [ ] 데이터베이스 백업 완료
- [ ] 프로덕션 마이그레이션 실행
- [ ] 프로덕션 API 테스트 완료
- [ ] 모니터링 및 로그 확인