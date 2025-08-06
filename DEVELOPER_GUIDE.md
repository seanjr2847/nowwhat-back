# 개발자 가이드

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd nowwhat-back

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# 필수 환경 변수 설정
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://...
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SECRET_KEY=your_jwt_secret_key
```

### 3. 데이터베이스 설정
```bash
# 마이그레이션 실행
alembic upgrade head

# 또는 자동 테이블 생성 (개발용)
python run.py  # 시작 시 자동 생성
```

### 4. 개발 서버 실행
```bash
# FastAPI 개발 서버 (권장)
python run.py

# 또는 직접 uvicorn 사용
uvicorn app.main:app --reload --port 8000
```

## 🏗️ 개발 워크플로

### 브랜치 전략
```
main           # 프로덕션 브랜치
├── develop    # 개발 통합 브랜치  
└── feature/*  # 기능 개발 브랜치
```

### 커밋 컨벤션
```bash
feat: 새로운 기능 추가
fix: 버그 수정  
docs: 문서 변경
style: 코드 포맷팅
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드 프로세스, 툴 설정
```

### 개발 사이클
1. **기능 브랜치 생성**: `git checkout -b feature/new-feature`
2. **개발 및 테스트**: 로컬에서 기능 구현 및 검증
3. **커밋**: 의미있는 단위로 커밋
4. **Pull Request**: develop 브랜치로 PR 생성
5. **코드 리뷰**: 팀 리뷰 후 승인
6. **병합**: develop 브랜치에 병합
7. **배포**: main 브랜치로 병합 후 프로덕션 배포

## 🧪 테스트 가이드

### 테스트 환경 설정
```bash
# 테스트 의존성 설치
pip install pytest pytest-asyncio pytest-mock httpx pytest-cov

# 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=app --cov-report=html

# 특정 테스트 실행
pytest tests/test_auth.py
pytest -k "test_login"
```

### 테스트 구조
```
tests/
├── conftest.py              # 공통 fixture
├── test_main.py            # 앱 기본 기능
├── unit/                   # 단위 테스트
│   ├── test_services/
│   ├── test_crud/
│   └── test_utils/
├── integration/            # 통합 테스트
│   ├── test_auth_flow.py
│   ├── test_api_endpoints.py
│   └── test_database.py
└── fixtures/               # 테스트 데이터
    ├── users.py
    └── checklists.py
```

### 테스트 작성 예제
```python
# tests/integration/test_auth_flow.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_google_oauth_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock Google OAuth response
        mock_token = "mock_google_token"
        
        response = await client.post(
            "/api/v1/auth/google",
            json={"googleToken": mock_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "accessToken" in data
        assert "refreshToken" in data
```

## 🎯 API 개발 패턴

### 1. 엔드포인트 추가 절차
```python
# 1. 스키마 정의 (app/schemas/nowwhat.py)
class NewFeatureRequest(BaseModel):
    name: str
    description: Optional[str] = None

class NewFeatureResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

# 2. 데이터베이스 모델 추가 (app/models/database.py)
class NewFeature(Base):
    __tablename__ = "new_features"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# 3. CRUD 작업 추가 (app/crud/new_feature.py)
class CRUDNewFeature:
    def create(self, db: Session, *, obj_in: NewFeatureRequest) -> NewFeature:
        db_obj = NewFeature(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

# 4. API 엔드포인트 추가 (app/api/v1/endpoints/new_feature.py)
@router.post("/", response_model=NewFeatureResponse)
async def create_new_feature(
    feature_data: NewFeatureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.new_feature.create(db=db, obj_in=feature_data)

# 5. 라우터 등록 (app/api/v1/api.py)
from app.api.v1.endpoints import new_feature
api_router.include_router(
    new_feature.router, 
    prefix="/new-features", 
    tags=["new-features"]
)
```

### 2. 데이터베이스 마이그레이션
```bash
# 새 마이그레이션 생성
alembic revision --autogenerate -m "Add new feature table"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1

# 마이그레이션 히스토리 확인
alembic history
```

### 3. AI 서비스 통합 패턴
```python
# app/services/my_ai_service.py
from app.services.gemini_service import GeminiService

class MyAIService:
    def __init__(self):
        self.gemini = GeminiService()
    
    async def process_data(self, input_data: str) -> dict:
        prompt = f"분석해주세요: {input_data}"
        
        try:
            response = await self.gemini.generate_content(
                prompt=prompt,
                model="gemini-2.5-flash"
            )
            return {"result": response}
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            return {"error": str(e)}

# 엔드포인트에서 사용
@router.post("/analyze")
async def analyze_data(data: str):
    ai_service = MyAIService()
    result = await ai_service.process_data(data)
    return APIResponse(success=True, data=result)
```

## 🔧 개발 도구 및 설정

### VS Code 설정 (.vscode/settings.json)
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "88"],
    "files.associations": {
        "*.py": "python"
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ]
}
```

### 권장 VS Code 익스텐션
- Python
- Python Docstring Generator
- REST Client
- SQLite Viewer
- GitLens
- Prettier

### 디버깅 설정 (.vscode/launch.json)
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/run.py",
            "console": "integratedTerminal",
            "env": {
                "ENV": "development"
            }
        }
    ]
}
```

## 📝 코딩 스타일 가이드

### Python 코드 스타일
```python
# Good: 타입 힌트 사용
def create_user(name: str, email: str) -> User:
    return User(name=name, email=email)

# Good: 비동기 함수 적절한 사용
async def get_user_data(user_id: str) -> Optional[User]:
    return await database.fetch_user(user_id)

# Good: 예외 처리
try:
    result = await expensive_operation()
    logger.info(f"Operation successful: {result}")
    return result
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

# Good: 로깅 패턴
logger.info(f"🌊 Starting process for user: {user_id}")
logger.error(f"❌ Process failed: {error_message}")
logger.info(f"✅ Process completed successfully")
```

### 데이터베이스 패턴
```python
# Good: 트랜잭션 관리
def create_checklist_with_items(db: Session, checklist_data: dict) -> Checklist:
    try:
        checklist = Checklist(**checklist_data)
        db.add(checklist)
        db.flush()  # ID 생성을 위해
        
        for item_data in checklist_data["items"]:
            item = ChecklistItem(checklist_id=checklist.id, **item_data)
            db.add(item)
        
        db.commit()
        return checklist
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create checklist: {e}")
        raise

# Good: 쿼리 최적화
def get_user_with_checklists(db: Session, user_id: str) -> Optional[User]:
    return (
        db.query(User)
        .options(joinedload(User.checklists))
        .filter(User.id == user_id)
        .first()
    )
```

## 🚨 문제 해결 가이드

### 일반적인 문제들

#### 1. 데이터베이스 연결 오류
```bash
# 증상: "could not connect to server"
# 해결:
1. DATABASE_URL 환경 변수 확인
2. Neon 데이터베이스 상태 확인
3. 네트워크 연결 확인

# 디버깅:
python -c "from app.core.database import test_connection; print(test_connection())"
```

#### 2. Gemini API 오류
```bash
# 증상: "API_KEY_INVALID" 
# 해결:
1. GEMINI_API_KEY 환경 변수 확인
2. Google AI Studio에서 API 키 상태 확인
3. 할당량 초과 여부 확인

# 디버깅:
curl -H "Authorization: Bearer $GEMINI_API_KEY" https://generativelanguage.googleapis.com/v1beta/models
```

#### 3. OAuth 인증 오류
```bash
# 증상: "invalid_client"
# 해결:
1. GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET 확인
2. Google Cloud Console에서 OAuth 설정 확인
3. 허용된 도메인 목록 확인
```

#### 4. 마이그레이션 오류
```bash
# 증상: "Target database is not up to date"
# 해결:
alembic stamp head  # 현재 상태를 최신으로 마크
alembic upgrade head  # 마이그레이션 재실행

# 완전 초기화 (주의: 데이터 손실)
alembic downgrade base
alembic upgrade head
```

### 로그 확인 방법
```bash
# 로컬 개발 시
python run.py  # 콘솔에서 직접 확인

# Vercel 배포 시  
vercel logs --app=nowwhat-back

# 특정 로그 레벨만 확인
export LOG_LEVEL=DEBUG
python run.py
```

## 📈 성능 최적화 팁

### 1. 데이터베이스 최적화
```python
# Good: 배치 삽입
def bulk_create_items(db: Session, items: List[dict]) -> List[ChecklistItem]:
    db_items = [ChecklistItem(**item) for item in items]
    db.bulk_save_objects(db_items)
    db.commit()
    return db_items

# Good: 선택적 로딩
def get_checklist_summary(db: Session, user_id: str) -> List[dict]:
    return (
        db.query(Checklist.id, Checklist.title, Checklist.progress)
        .filter(Checklist.user_id == user_id)
        .all()
    )
```

### 2. API 최적화
```python
# Good: 비동기 병렬 처리
async def get_enriched_checklist(checklist_id: str) -> dict:
    tasks = [
        get_checklist_data(checklist_id),
        get_user_progress(checklist_id),
        get_related_feedback(checklist_id)
    ]
    
    checklist, progress, feedback = await asyncio.gather(*tasks)
    
    return {
        "checklist": checklist,
        "progress": progress, 
        "feedback": feedback
    }
```

### 3. Gemini API 최적화
```python
# Good: 토큰 사용량 최적화
def optimize_prompt(base_prompt: str, context: dict) -> str:
    # 불필요한 컨텍스트 제거
    essential_context = {
        k: v for k, v in context.items() 
        if k in ["goal", "intent", "user_answers"]
    }
    
    return f"{base_prompt}\n컨텍스트: {essential_context}"
```

## 🔄 배포 가이드

### Vercel 배포 설정
```json
// vercel.json
{
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.9"
  }
}
```

### 배포 체크리스트
- [ ] 환경 변수 설정 완료
- [ ] 데이터베이스 마이그레이션 완료
- [ ] API 문서 업데이트
- [ ] 테스트 통과 확인
- [ ] 로그 레벨 프로덕션으로 설정
- [ ] CORS 설정 확인

```bash
# 배포 명령어
vercel --prod

# 환경 변수 설정
vercel env add GEMINI_API_KEY
vercel env add DATABASE_URL
# ... 기타 환경 변수
```

---

*이 개발자 가이드는 실제 개발 경험을 바탕으로 작성되었으며, 프로젝트 진화와 함께 지속적으로 업데이트됩니다.*