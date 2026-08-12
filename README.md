# DART MCP 서버 - Replit 배포 가이드 (태블릿용)

## 1. Replit 가입 및 Repl 생성
1. 태블릿 브라우저에서 https://replit.com 접속 → 회원가입/로그인
2. 우측 상단 "+ Create" → 템플릿에서 **Python** 선택
3. 이름은 자유롭게 (예: dart-mcp-server) 입력 후 생성

## 2. 코드 붙여넣기
1. 왼쪽 파일 목록에서 기본 생성된 `main.py`를 **삭제**
2. 새 파일 `app.py` 생성 → `dart_mcp_server.py`의 내용을 그대로 복사해서 붙여넣기
3. 새 파일 `requirements.txt` 생성 → 이 문서와 함께 받은 requirements.txt 내용 붙여넣기

## 3. API 키 등록 (절대 코드에 직접 쓰지 마세요)
1. 왼쪽 메뉴에서 자물쇠 아이콘 **Secrets** 클릭
2. Key: `DART_API_KEY`
3. Value: 발급받으신 DART 인증키 40자리
4. Add new secret 클릭

## 4. 패키지 설치 및 실행
1. 하단 **Shell** 탭 클릭
2. `pip install -r requirements.txt` 입력 후 엔터
3. 설치 끝나면 상단 **Run** 버튼 클릭
4. 우측에 웹뷰가 뜨면서 공개 URL이 생성됨 (예: `https://dart-mcp-server.사용자명.repl.co`)
   - 이 URL을 메모해두세요

> 참고: Replit 무료 플랜은 일정 시간 사용이 없으면 서버가 자동으로 잠들 수 있습니다.
> 다시 쓸 땐 Replit 페이지를 열어 Run을 한 번 더 눌러주면 됩니다.

## 5. Claude 앱에 커넥터로 등록
1. Claude 앱 → 설정(⚙️) → **Customize** → **Connectors**
2. **+ Add custom connector** 클릭
3. 이름: `DART`
4. URL: 4번에서 확인한 Replit 주소 (필요시 뒤에 `/mcp` 붙여서 시도)
5. Add 클릭 → 정상 연결되면 이후 대화에서 자동으로 도구가 인식됨

## 6. 사용 예시 (연결 후 채팅에서)
- "2024년 이후 기술특례상장한 회사들의 증권신고서를 찾아서 피어그룹과 배수를 정리해줘"
- 위 요청이 오면 Claude가 자동으로 search_disclosures → get_document_text 도구를 호출해서
  실제 DART 원문을 읽고 답변합니다.

## 문제 발생 시
- "DART_API_KEY 환경변수가 설정되어 있지 않습니다" 오류 → 3번 Secrets 설정 다시 확인
- 커넥터 연결 실패 → Replit이 잠들어 있는지 확인 (Run 다시 클릭), URL 끝 경로(/mcp 유무) 바꿔서 재시도
- pip install 에러 → Shell에서 `pip install mcp requests` 로 개별 설치 시도
