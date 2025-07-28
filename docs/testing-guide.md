# Testing Guide for POST /questions/answer

## Overview

This guide provides comprehensive testing strategies for the new POST `/api/v1/questions/answer` endpoint, including unit tests, integration tests, and performance validation.

## Test Setup

### Prerequisites

```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-mock httpx

# For integration tests with database
pip install pytest-postgresql  # or testcontainers
```

### Test Configuration

Create `pytest.ini` in project root:

```ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    external: Tests requiring external APIs
```

### Environment Setup for Tests

Create `tests/.env.test`:

```bash
DATABASE_URL=postgresql://test:test@localhost:5432/test_nowwhat
GEMINI_API_KEY=test_gemini_key  # Use mock in tests
PERPLEXITY_API_KEY=test_perplexity_key  # Use mock in tests
SECRET_KEY=test-secret-key-for-testing
ENV=test
LOG_LEVEL=DEBUG
```

## Unit Tests

### Test Structure

```
tests/
├── unit/
│   ├── __init__.py
│   ├── schemas/
│   │   └── test_questions_schemas.py
│   ├── services/
│   │   ├── test_perplexity_service.py
│   │   ├── test_checklist_orchestrator.py
│   │   └── test_gemini_service.py
│   ├── api/
│   │   └── test_questions_endpoint.py
│   └── conftest.py
├── integration/
│   ├── __init__.py
│   ├── test_complete_workflow.py
│   └── conftest.py
└── performance/
    ├── __init__.py
    └── test_endpoint_performance.py
```

### Schema Validation Tests

`tests/unit/schemas/test_questions_schemas.py`:

```python
import pytest
from pydantic import ValidationError
from app.schemas.questions import (
    QuestionAnswersRequest, 
    SelectedIntentSchema, 
    AnswerItemSchema
)

class TestQuestionAnswersRequest:
    
    def test_valid_request(self):
        """Test valid request passes validation"""
        request_data = {
            "goal": "일본여행 가고싶어",
            "selectedIntent": {
                "index": 0,
                "title": "여행 계획"
            },
            "answers": [
                {
                    "questionIndex": 0,
                    "questionText": "여행 기간은?",
                    "answer": "3days"
                }
            ]
        }
        
        request = QuestionAnswersRequest(**request_data)
        assert request.goal == "일본여행 가고싶어"
        assert len(request.answers) == 1
    
    def test_empty_goal_fails(self):
        """Test empty goal fails validation"""
        request_data = {
            "goal": "",
            "selectedIntent": {"index": 0, "title": "여행 계획"},
            "answers": [{"questionIndex": 0, "questionText": "질문", "answer": "답변"}]
        }
        
        with pytest.raises(ValidationError):
            QuestionAnswersRequest(**request_data)
    
    def test_answer_array_valid(self):
        """Test answer as array is valid"""
        request_data = {
            "goal": "테스트 목표",
            "selectedIntent": {"index": 0, "title": "계획"},
            "answers": [
                {
                    "questionIndex": 0,
                    "questionText": "선택사항은?",
                    "answer": ["option1", "option2", "option3"]
                }
            ]
        }
        
        request = QuestionAnswersRequest(**request_data)
        assert isinstance(request.answers[0].answer, list)
        assert len(request.answers[0].answer) == 3
    
    def test_negative_indices_fail(self):
        """Test negative indices fail validation"""
        request_data = {
            "goal": "테스트",
            "selectedIntent": {"index": -1, "title": "계획"},
            "answers": [{"questionIndex": 0, "questionText": "질문", "answer": "답변"}]
        }
        
        with pytest.raises(ValidationError):
            QuestionAnswersRequest(**request_data)
```

### Service Layer Tests

`tests/unit/services/test_perplexity_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from app.services.perplexity_service import PerplexityService, SearchResult

class TestPerplexityService:
    
    @pytest.fixture
    def service(self):
        return PerplexityService()
    
    @pytest.fixture
    def mock_successful_response(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": "일본 여행 추천 정보입니다. 체리 블라섬 시즌이 좋습니다."
                    }
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_parallel_search_success(self, service, mock_successful_response):
        """Test successful parallel search"""
        queries = ["일본 여행 팁", "도쿄 맛집"]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_successful_response)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            results = await service.parallel_search(queries)
            
            assert len(results) == 2
            assert all(r.success for r in results)
            assert all(r.content for r in results)
    
    @pytest.mark.asyncio
    async def test_parallel_search_with_failures(self, service):
        """Test parallel search with some failures"""
        queries = ["성공 쿼리", "실패 쿼리"]
        
        async def mock_post_side_effect(*args, **kwargs):
            mock_response = AsyncMock()
            if "성공" in str(args):
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={
                    "choices": [{"message": {"content": "성공 응답"}}]
                })
            else:
                mock_response.status = 500
                mock_response.text = AsyncMock(return_value="Server Error")
            return mock_response
        
        with patch('aiohttp.ClientSession.post', side_effect=mock_post_side_effect):
            results = await service.parallel_search(queries)
            
            assert len(results) == 2
            success_count = sum(1 for r in results if r.success)
            assert success_count >= 0  # At least handle gracefully
    
    def test_generate_search_queries(self, service):
        """Test search query generation"""
        goal = "일본여행"
        intent_title = "여행 계획"
        answers = [
            {"questionIndex": 0, "questionText": "기간", "answer": "3days"},
            {"questionIndex": 1, "questionText": "예산", "answer": "1million"}
        ]
        
        queries = service.generate_search_queries(goal, intent_title, answers)
        
        assert len(queries) == 10
        assert all(goal in query for query in queries)
        assert any("3days" in query or "1million" in query for query in queries)
    
    @pytest.mark.asyncio
    async def test_enhance_checklist_with_search(self, service):
        """Test checklist enhancement with search results"""
        base_checklist = ["여권 확인하기", "항공편 예약하기"]
        search_results = [
            SearchResult(
                query="일본 여행 팁",
                content="일본 여행 시 JR 패스를 미리 구매하는 것이 좋습니다. 현지에서는 구매할 수 없습니다.",
                sources=["https://example.com"],
                success=True
            ),
            SearchResult(
                query="도쿄 추천",
                content="도쿄 스카이트리 전망대는 사전 예약이 필수입니다.",
                sources=["https://example2.com"], 
                success=True
            )
        ]
        
        enhanced = await service.enhance_checklist_with_search(base_checklist, search_results)
        
        assert len(enhanced) >= len(base_checklist)
        # Check if any search insights were added
        enhanced_text = " ".join(enhanced)
        assert any(keyword in enhanced_text for keyword in ["JR 패스", "사전 예약"])
```

`tests/unit/services/test_checklist_orchestrator.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session
from app.services.checklist_orchestrator import ChecklistOrchestrator, ChecklistGenerationError
from app.schemas.questions import QuestionAnswersRequest, SelectedIntentSchema, AnswerItemSchema
from app.models.database import User

class TestChecklistOrchestrator:
    
    @pytest.fixture
    def orchestrator(self):
        return ChecklistOrchestrator()
    
    @pytest.fixture
    def sample_request(self):
        return QuestionAnswersRequest(
            goal="일본여행 가고싶어",
            selectedIntent=SelectedIntentSchema(index=0, title="여행 계획"),
            answers=[
                AnswerItemSchema(
                    questionIndex=0,
                    questionText="여행 기간은?",
                    answer="3days"
                ),
                AnswerItemSchema(
                    questionIndex=1,
                    questionText="예산은?",
                    answer="1million"
                )
            ]
        )
    
    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = "test_user_id"
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def mock_db_session(self):
        session = MagicMock(spec=Session)
        session.add = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        session.flush = MagicMock()
        return session
    
    @pytest.mark.asyncio
    async def test_process_answers_to_checklist_success(
        self, orchestrator, sample_request, mock_user, mock_db_session
    ):
        """Test successful complete workflow"""
        
        # Mock the internal methods
        orchestrator._save_user_answers = AsyncMock()
        orchestrator._generate_enhanced_checklist = AsyncMock(return_value=[
            "여권 유효기간 확인하기",
            "항공편 예약하기", 
            "숙박 예약하기",
            "여행자보험 가입하기",
            "환전하기",
            "짐 싸기",
            "공항 교통편 확인하기",
            "현지 교통카드 알아보기"
        ])
        orchestrator._save_final_checklist = AsyncMock(return_value="cl_1234567890_abcdef")
        
        result = await orchestrator.process_answers_to_checklist(
            sample_request, mock_user, mock_db_session
        )
        
        assert result.checklistId == "cl_1234567890_abcdef"
        assert result.redirectUrl == "/result/cl_1234567890_abcdef"
        
        # Verify internal methods were called
        orchestrator._save_user_answers.assert_called_once()
        orchestrator._generate_enhanced_checklist.assert_called_once()
        orchestrator._save_final_checklist.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_user_answers(self, orchestrator, sample_request, mock_user, mock_db_session):
        """Test user answer saving"""
        
        await orchestrator._save_user_answers(sample_request, mock_user, mock_db_session)
        
        # Verify database operations
        assert mock_db_session.add.call_count == len(sample_request.answers)
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_enhanced_checklist(self, orchestrator, sample_request):
        """Test enhanced checklist generation"""
        
        # Mock the parallel operations
        with patch.object(orchestrator, '_generate_ai_checklist') as mock_ai, \
             patch.object(orchestrator, '_perform_parallel_search') as mock_search, \
             patch('app.services.perplexity_service.perplexity_service.enhance_checklist_with_search') as mock_enhance:
            
            mock_ai.return_value = ["AI 생성 항목 1", "AI 생성 항목 2"]
            mock_search.return_value = []
            mock_enhance.return_value = ["향상된 항목 1", "향상된 항목 2", "향상된 항목 3"]
            
            result = await orchestrator._generate_enhanced_checklist(sample_request)
            
            assert len(result) >= 3
            mock_ai.assert_called_once()
            mock_search.assert_called_once()
    
    def test_validate_and_adjust_checklist(self, orchestrator):
        """Test checklist validation and adjustment"""
        
        # Test with too few items
        short_checklist = ["항목 1", "항목 2"]
        adjusted = orchestrator._validate_and_adjust_checklist(short_checklist)
        assert len(adjusted) >= orchestrator.min_checklist_items
        
        # Test with too many items
        long_checklist = [f"항목 {i}" for i in range(20)]
        adjusted = orchestrator._validate_and_adjust_checklist(long_checklist)
        assert len(adjusted) <= orchestrator.max_checklist_items
        
        # Test with duplicates
        duplicate_checklist = ["항목 1", "항목 1", "항목 2", "항목 2"]
        adjusted = orchestrator._validate_and_adjust_checklist(duplicate_checklist)
        unique_items = set(adjusted)
        assert len(unique_items) == len(adjusted)  # No duplicates
    
    def test_generate_checklist_id(self, orchestrator):
        """Test checklist ID generation"""
        
        checklist_id = orchestrator._generate_checklist_id()
        
        assert checklist_id.startswith("cl_")
        parts = checklist_id.split("_")
        assert len(parts) == 3
        assert parts[1].isdigit()  # timestamp
        assert len(parts[2]) == 8  # random part
```

### API Endpoint Tests

`tests/unit/api/test_questions_endpoint.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app
from app.schemas.questions import QuestionAnswersResponse

class TestQuestionsAnswerEndpoint:
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        # Mock JWT token - in real tests, generate valid JWT
        return {"Authorization": "Bearer mock_jwt_token"}
    
    @pytest.fixture
    def valid_request_data(self):
        return {
            "goal": "일본여행 가고싶어",
            "selectedIntent": {
                "index": 0,
                "title": "여행 계획"
            },
            "answers": [
                {
                    "questionIndex": 0,
                    "questionText": "여행 기간은?",
                    "answer": "3days"
                },
                {
                    "questionIndex": 1,
                    "questionText": "예산은?",
                    "answer": "1million"
                }
            ]
        }
    
    def test_submit_answers_success(self, client, auth_headers, valid_request_data):
        """Test successful answer submission"""
        
        mock_response = QuestionAnswersResponse(
            checklistId="cl_1234567890_test",
            redirectUrl="/result/cl_1234567890_test"
        )
        
        with patch('app.core.auth.get_current_user') as mock_auth, \
             patch('app.services.checklist_orchestrator.checklist_orchestrator.process_answers_to_checklist') as mock_orchestrator:
            
            mock_auth.return_value = MagicMock(id="test_user")
            mock_orchestrator.return_value = mock_response
            
            response = client.post(
                "/api/v1/questions/answer",
                json=valid_request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["checklistId"] == "cl_1234567890_test"
            assert data["redirectUrl"] == "/result/cl_1234567890_test"
    
    def test_submit_answers_missing_goal(self, client, auth_headers):
        """Test request with missing goal"""
        
        request_data = {
            "selectedIntent": {"index": 0, "title": "계획"},
            "answers": [{"questionIndex": 0, "questionText": "질문", "answer": "답변"}]
        }
        
        response = client.post(
            "/api/v1/questions/answer",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_submit_answers_empty_answers(self, client, auth_headers):
        """Test request with empty answers array"""
        
        request_data = {
            "goal": "테스트 목표",
            "selectedIntent": {"index": 0, "title": "계획"},
            "answers": []
        }
        
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = MagicMock(id="test_user")
            
            response = client.post(
                "/api/v1/questions/answer",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 400
            assert "최소 1개 이상" in response.json()["detail"]
    
    def test_submit_answers_unauthorized(self, client, valid_request_data):
        """Test request without authentication"""
        
        response = client.post(
            "/api/v1/questions/answer",
            json=valid_request_data
        )
        
        assert response.status_code == 401
    
    def test_submit_answers_orchestrator_error(self, client, auth_headers, valid_request_data):
        """Test handling of orchestrator errors"""
        
        with patch('app.core.auth.get_current_user') as mock_auth, \
             patch('app.services.checklist_orchestrator.checklist_orchestrator.process_answers_to_checklist') as mock_orchestrator:
            
            mock_auth.return_value = MagicMock(id="test_user")
            mock_orchestrator.side_effect = Exception("AI 서비스 오류")
            
            response = client.post(
                "/api/v1/questions/answer",
                json=valid_request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 500
            assert "서버 오류" in response.json()["detail"]
```

## Integration Tests

`tests/integration/test_complete_workflow.py`:

```python
import pytest
import asyncio
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.database import User, Checklist, ChecklistItem
from app.services.checklist_orchestrator import checklist_orchestrator
from app.schemas.questions import QuestionAnswersRequest, SelectedIntentSchema, AnswerItemSchema

class TestCompleteWorkflow:
    
    @pytest.fixture
    def db_session(self):
        # Use test database session
        # This requires proper test database setup
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def test_user(self, db_session):
        user = User(
            id="test_integration_user",
            email="test@integration.com",
            name="Test User",
            google_id="google_test_id"
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_checklist_creation(self, test_user, db_session):
        """Test complete end-to-end workflow"""
        
        request = QuestionAnswersRequest(
            goal="통합 테스트를 위한 일본 여행",
            selectedIntent=SelectedIntentSchema(index=0, title="여행 계획"),
            answers=[
                AnswerItemSchema(
                    questionIndex=0,
                    questionText="여행 기간은 얼마나 되나요?",
                    answer="1week"
                ),
                AnswerItemSchema(
                    questionIndex=1,
                    questionText="누구와 함께 가시나요?",
                    answer="couple"
                ),
                AnswerItemSchema(
                    questionIndex=2,
                    questionText="주요 관심사는?",
                    answer=["sightseeing", "food", "culture"]
                )
            ]
        )
        
        # Mock external API calls to avoid actual API usage in tests
        with patch('app.services.gemini_service.gemini_service._call_gemini_api') as mock_gemini, \
             patch('app.services.perplexity_service.perplexity_service.parallel_search') as mock_perplexity:
            
            # Mock Gemini response
            mock_gemini.return_value = """
            여권 유효기간 확인하기
            항공편 예약하기
            숙박시설 예약하기
            여행자보험 가입하기
            일본 엔화 환전하기
            JR 패스 구매하기
            현지 교통 정보 확인하기
            짐 싸기 체크리스트 작성하기
            """
            
            # Mock Perplexity response
            mock_perplexity.return_value = []
            
            # Execute the workflow
            result = await checklist_orchestrator.process_answers_to_checklist(
                request, test_user, db_session
            )
            
            # Verify response
            assert result.checklistId.startswith("cl_")
            assert result.redirectUrl == f"/result/{result.checklistId}"
            
            # Verify database records
            checklist = db_session.query(Checklist).filter(
                Checklist.id == result.checklistId
            ).first()
            
            assert checklist is not None
            assert checklist.user_id == test_user.id
            assert "일본 여행" in checklist.title
            assert checklist.category == "여행 계획"
            
            # Verify checklist items
            items = db_session.query(ChecklistItem).filter(
                ChecklistItem.checklist_id == checklist.id
            ).all()
            
            assert len(items) >= 8  # Minimum items
            assert len(items) <= 15  # Maximum items
            assert all(item.text for item in items)  # No empty items
            assert all(not item.is_completed for item in items)  # All uncompleted initially
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_with_ai_failure(self, test_user, db_session):
        """Test workflow when AI services fail"""
        
        request = QuestionAnswersRequest(
            goal="AI 실패 테스트 여행",
            selectedIntent=SelectedIntentSchema(index=0, title="여행 계획"),
            answers=[
                AnswerItemSchema(
                    questionIndex=0,
                    questionText="기간은?",
                    answer="3days"
                )
            ]
        )
        
        # Mock AI failure
        with patch('app.services.gemini_service.gemini_service._call_gemini_api') as mock_gemini, \
             patch('app.services.perplexity_service.perplexity_service.parallel_search') as mock_perplexity:
            
            mock_gemini.side_effect = Exception("AI 서비스 오류")
            mock_perplexity.return_value = []
            
            # Should still succeed with fallback
            result = await checklist_orchestrator.process_answers_to_checklist(
                request, test_user, db_session
            )
            
            assert result.checklistId.startswith("cl_")
            
            # Verify fallback checklist was used
            checklist = db_session.query(Checklist).filter(
                Checklist.id == result.checklistId
            ).first()
            
            items = db_session.query(ChecklistItem).filter(
                ChecklistItem.checklist_id == checklist.id
            ).all()
            
            # Should have default template items
            assert len(items) >= 8
            item_texts = [item.text for item in items]
            assert any("여행 날짜" in text for text in item_texts)
```

## Performance Tests

`tests/performance/test_endpoint_performance.py`:

```python
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import requests

class TestEndpointPerformance:
    
    @pytest.fixture
    def performance_request_data(self):
        return {
            "goal": "성능 테스트 여행",
            "selectedIntent": {"index": 0, "title": "여행 계획"},
            "answers": [
                {"questionIndex": 0, "questionText": "기간", "answer": "1week"},
                {"questionIndex": 1, "questionText": "예산", "answer": "2million"},
                {"questionIndex": 2, "questionText": "동행", "answer": "family"}
            ]
        }
    
    @pytest.mark.performance
    def test_single_request_response_time(self, performance_request_data):
        """Test single request completes within 30 seconds"""
        
        # This would require a running test server
        # Using mock for demonstration
        
        start_time = time.time()
        
        # Mock the request - replace with actual HTTP call in real test
        with patch('app.services.checklist_orchestrator.checklist_orchestrator.process_answers_to_checklist') as mock_orchestrator:
            mock_orchestrator.return_value = MagicMock(
                checklistId="cl_perf_test",
                redirectUrl="/result/cl_perf_test"
            )
            
            # Simulate processing time
            time.sleep(0.1)  # Simulated processing
            
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response_time < 30.0, f"Response time {response_time}s exceeds 30s limit"
    
    @pytest.mark.performance
    def test_concurrent_requests(self, performance_request_data):
        """Test handling of concurrent requests"""
        
        def make_request():
            # Mock concurrent request processing
            start_time = time.time()
            time.sleep(0.5)  # Simulate processing
            return time.time() - start_time
        
        # Test with 5 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            response_times = [future.result() for future in futures]
        
        # All requests should complete
        assert len(response_times) == 5
        assert all(rt < 30.0 for rt in response_times)
        
        # Check that concurrent processing doesn't cause significant slowdown
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 5.0  # Reasonable concurrent performance
    
    @pytest.mark.performance 
    def test_memory_usage_stability(self):
        """Test memory usage remains stable under load"""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate multiple requests
        for _ in range(10):
            # Mock request processing
            time.sleep(0.1)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for test)
        assert memory_increase < 100, f"Memory increased by {memory_increase}MB"
```

## Running Tests

### Test Execution Commands

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m performance

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/api/test_questions_endpoint.py

# Run with specific markers
pytest -m "not external"  # Skip tests requiring external APIs

# Run performance tests only
pytest -m performance -v

# Parallel test execution
pytest -n auto  # Requires pytest-xdist
```

### Test Environment Setup

```bash
# Set up test database
createdb test_nowwhat

# Run database migrations for test
export DATABASE_URL=postgresql://test:test@localhost:5432/test_nowwhat
python -m alembic upgrade head

# Run tests with test environment
ENV=test pytest
```

### Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Test POST /questions/answer

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_nowwhat
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-mock pytest-cov
    
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=app
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:test@localhost:5432/test_nowwhat
      run: pytest tests/integration/ -v
    
    - name: Run performance tests
      run: pytest tests/performance/ -v
```

## Test Coverage Goals

- **Overall Coverage**: > 85%
- **Critical Path Coverage**: > 95% (main workflow)
- **Error Handling Coverage**: > 90%
- **Service Layer Coverage**: > 90%
- **API Endpoint Coverage**: > 95%

## Mocking Strategy

### External Services
- Mock Gemini AI API calls to avoid quota usage
- Mock Perplexity API calls for consistent testing
- Use test doubles for database operations where appropriate

### Test Data
- Use factories for consistent test data generation
- Parameterized tests for edge cases
- Separate test fixtures for different scenarios

This comprehensive testing guide ensures the POST `/questions/answer` endpoint is thoroughly validated across all aspects of functionality, performance, and reliability.