# Role & Objective
너는 네트워크 자동화 및 Python 풀스택 개발 전문가야. 
현재 우리 학교 네트워크의 메인 라우터인 **ipTIME AX3000M (신규 Gen3 웹 UI 펌웨어 적용, EasyMesh Controller 모드)**에 접속된 학생/교직원 디바이스들의 목록을 실시간으로 조회하고, 특정 기기의 와이파이 연결을 강제로 끊거나(Disconnect) 방화벽 접근 제어(MAC 차단)를 온/오프할 수 있는 Python 제어 프로그램을 개발해 줘.

# Environment & Target Router Specs
- **Router Model:** ipTIME AX3000M (EasyMesh Controller) + A8004T / A604SR (Agents)
- **Admin URL:** `http://192.168.4.1/`
- **Admin ID:** `admin`
- **Admin PW:** `emdeo1004`
- **Target Subnet:** `192.168.4.x` (예: `3A:8D:0F:38:46:0B` / `192.168.4.57` 등 다수 단말 접속 중)
- **UI Architecture:** ipTIME 최신 다크/라이트 테마 UI (구형 `timepro.cgi` 폼 방식이 아닌, `/cgi/service.cgi` 또는 내부 CGI에 JSON Payload를 POST 요청하고 `efm_session_id` 쿠키로 인증하는 방식)

# Core Features to Implement
1. **인증 및 세션 매니저 (`auth.py`)**
   - `http://192.168.4.1/`에 `admin` / `emdeo1004`로 로그인하여 세션 쿠키를 유지하고, 세션 만료 시 자동 재로그인하는 기능.
   - 구형 CGI 방식과 신형 JSON API(`/cgi/service.cgi`) 방식을 모두 테스트하여 현재 펌웨어의 정확한 로그인 엔드포인트를 자동 감지하는 진단 함수 포함.

2. **네트워크 API 패킷 스니퍼 & 분석 도우미 (`inspector.py`)**
   - Playwright(또는 Selenium)를 사용해 `http://192.168.4.1/`에 자동 로그인한 뒤, 브라우저에서 발생하는 모든 XHR/Fetch 요청의 URL, Request Payload(JSON), Response를 가로채서 콘솔과 `api_log.json`에 저장하는 스크립트 작성.
   - 내가 UI에서 EasyMesh의 [Disconnect] 버튼이나 [Firewall -> Access Control] 규칙을 클릭했을 때 날아가는 정확한 JSON 파라미터를 1분 만에 추출할 수 있도록 구성할 것.

3. **디바이스 모니터링 및 제어 엔진 (`controller.py`)**
   - **현재 접속 단말 조회:** EasyMesh 컨트롤러 및 하위 에이전트(hallway 등)에 연결된 모든 기기의 호스트명(예: `iPhone`, `GalaxyS24`), IP 주소(`192.168.4.x`), MAC 주소, 접속 대역(2.4GHz/5GHz), 수신 감도(RSSI), 현재 트래픽(Rx/Tx)을 파싱.
   - **즉시 연결 끊기 (Disconnect):** 특정 MAC 주소를 지정하여 EasyMesh Station의 `Disconnect` 명령 전송.
   - **인터넷 차단/해제 (Firewall Access Control):** 특정 MAC 주소(또는 여러 학생 기기 그룹)를 방화벽 접근 제어 목록에 등록하고, 원클릭(또는 수업 시간표 스케줄)으로 규칙을 `Enable(차단)` / `Disable(해제)`하는 기능.

4. **관리자용 GUI 또는 로컬 웹 대시보드 (`app.py`)**
   - 교무실 PC에서 한눈에 보고 제어할 수 있도록 깔끔한 UI(Streamlit, FastAPI+Tailwind, 또는 PyQt 중 가장 직관적인 로컬 웹 UI 권장)로 구현.
   - 기기 별칭(Alias) 매핑 기능 (MAC 주소에 '홍길동 아이폰', '교무실 PC' 등 메모 저장 기능 - 로컬 JSON/SQLite 활용).
   - 체크박스로 여러 기기를 선택한 뒤 [일괄 인터넷 차단], [일괄 차단 해제], [일괄 재연결(Disconnect)] 버튼 제공.

# Step-by-Step Execution Plan
- **Step 1:** 프로젝트 폴더 구조를 잡고 필요한 패키지(`requests`, `playwright`, `streamlit` 등)가 포함된 `requirements.txt`를 생성해 줘.
- **Step 2:** 먼저 `192.168.4.1`에 접속해 정확한 JSON API 규격을 캡처할 수 있는 `inspector.py`와 기본 `controller.py` 코드를 작성해 줘.
- **Step 3:** 추출된 API를 바로 연결할 수 있도록 모듈화된 대시보드 UI(`app.py`) 코드를 완성해 줘. 코드 내에 하드코딩 없이 설정 파일(`config.json`)로 계정과 공유기 IP(`192.168.4.1`)를 관리하도록 작성해 줘.