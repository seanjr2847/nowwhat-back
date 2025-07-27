#!/usr/bin/env python3
"""
API 테스트 스크립트
"""

import requests
import json

def test_intent_analyze_api():
    """의도 분석 API 테스트"""
    url = "http://localhost:8000/api/v1/intents/analyze"
    data = {"goal": "일본여행 가고싶어"}
    headers = {"Content-Type": "application/json"}
    
    try:
        print("🚀 의도 분석 API 테스트 시작...")
        print(f"URL: {url}")
        print(f"Data: {data}")
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        print(f"✅ 응답 상태: {response.status_code}")
        print(f"📝 응답 내용:")
        
        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 응답 구조 검증
            if "sessionId" in result and "intents" in result:
                print("✅ 응답 구조가 올바릅니다!")
                print(f"세션 ID: {result['sessionId']}")
                print(f"의도 개수: {len(result['intents'])}")
                
                for i, intent in enumerate(result['intents']):
                    print(f"  {i+1}. {intent.get('icon', '❓')} {intent.get('title', 'Unknown')}")
                    print(f"     {intent.get('description', 'No description')}")
            else:
                print("❌ 응답 구조가 예상과 다릅니다.")
        else:
            print(f"❌ API 호출 실패: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

def test_health_check():
    """헬스 체크 테스트"""
    try:
        url = "http://localhost:8000/"
        response = requests.get(url, timeout=5)
        print(f"🏥 헬스 체크: {response.status_code}")
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print("🧪 API 테스트 시작")
    print("=" * 50)
    
    # 1. 헬스 체크
    if test_health_check():
        print("✅ 서버가 실행 중입니다.")
    else:
        print("❌ 서버가 실행되지 않았습니다.")
        exit(1)
    
    print()
    
    # 2. 의도 분석 API 테스트
    test_intent_analyze_api()
    
    print("\n🏁 테스트 완료!") 