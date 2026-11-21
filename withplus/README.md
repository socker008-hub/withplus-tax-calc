# 위드플러스 세금계산기 MCP

업스테이지 `korean-tax-calc-mcp`(MIT)를 포크해 세무법인 위드플러스용으로 운영하는 버전입니다.
계산 엔진(93개 도구, 법인세·소득세·양도·상속증여·부가세·가산세, 연도표 2016~2026)은 원본 그대로 쓰고,
`withplus/` 폴더에 운영 기능만 덧붙였습니다. **원본 파일은 한 줄도 고치지 않았습니다** → 원본이 업데이트되면 GitHub의 "Sync fork" 버튼으로 그대로 받아올 수 있습니다.

## 1. 구조

```
Claude (Desktop / Code / claude.ai)
   │  "2026 사업연도 과세표준 5억 법인세는?"
   ▼
[local]  내 PC에서 stdio로 직접 실행 ─────────┐
[public] https://mcp.withplustax.com/mcp       │
   → Cloudflare Tunnel → 사무실 PC :8001        │
   → withplus_tax (토큰 확인·로그·안내문구)     │
   ▼                                           ▼
korean_tax_calc_mcp (원본 엔진: 연도별 세율표 → 조문 순서대로 코드 계산 → 결과 + 근거 조문)
```

AI는 "어떤 도구에 어떤 숫자를 넣을지"만 정하고, 계산은 코드가 합니다. 연도표가 없는 해(예: 2027)는 추정하지 않고 오류로 멈춥니다.

## 2. 원본과 달라진 점

| 구분 | 원본 | 위드플러스판 |
|---|---|---|
| 서버 이름 | korean-tax-calc-mcp | withplus-tax-calc (위드플러스 세금계산기) |
| 외부 공개 시 인증 | 없음(누구나 접속) | 접속 토큰 필수, 세무사별 발급, 틀리면 401 |
| 공개 도메인 접속 | localhost 외 도메인은 421로 거절 | `WITHPLUS_PUBLIC_HOSTS` 도메인 허용 |
| 서버 PC 파일 접근 도구 | PDF 경로 읽기 3개 + 엑셀 저장 1개 | 공개 모드에서만 끔(외부인이 서버 PC 파일을 읽고 쓰지 못하게). 내 PC 모드는 93개 전부 사용 |
| 사용 기록 | 없음 | `logs/usage-YYYY-MM.jsonl` — 누가·언제·어떤 도구(입력값은 저장 안 함) |
| 결과 안내문구 | 없음 | 공개 모드 결과마다 "검토 보조자료·세무사 검토 필요·문의처" (끌 수 있음) |

## 3. 설치 A — 내 PC에서만 쓰기 (10분)

1. GitHub에서 `UpstageAI/korean-tax-calc-mcp` → **Fork** (내 계정에 `withplus-tax-calc` 이름으로)
2. 받은 압축파일의 `withplus` 폴더를 포크한 저장소 최상위에 복사 → 커밋·푸시
3. 사무실 PC에 `C:\withplus-tax-calc` 로 클론 (또는 압축 해제)
4. `withplus\deploy\install.bat` 더블클릭 → uv(파이썬 관리 도구)와 프로그램이 자동 설치됨
5. Claude Desktop → 설정 → 개발자 → 설정 편집 → `deploy\claude_desktop_config.example.json` 내용 붙여넣기(경로의 `<윈도우사용자>`만 바꾸기) → Claude Desktop 재시작
   - Claude Code라면: `claude mcp add withplus-tax -- uv run --project C:\withplus-tax-calc\withplus withplus-tax-calc --mode local`
6. 확인: Claude에게 "퇴직금 1억 근속 15년 2026년 퇴직 퇴직소득세" → **2,175,000원**, 근속연수공제 27,500,000원이 나오면 정상

### 직원 PC — 원클릭 설치 (`deploy\staff_setup.bat`)

직원에게 `staff_setup.bat` 파일 하나만 보내면 됩니다. 더블클릭하면 아래를 자동으로 합니다.

1. GitHub에서 최신 버전을 내려받아 `%USERPROFILE%\withplus-tax-calc` 에 설치(다시 실행하면 업데이트, `.env` 는 유지)
2. uv 없으면 설치 → `uv sync`
3. Claude Desktop이 켜져 있으면 종료할 때까지 대기
4. Claude Desktop 설정 파일에 `withplus-tax` 등록 — 기존 설정은 그대로 두고, 고치기 전에 `.bak-날짜시각` 백업. 설정 파일 형식이 깨져 있으면 손대지 않고 중단
5. 계산 테스트(퇴직소득세 2,175,000원)까지 확인

준비물: Claude Desktop 설치·로그인, 인터넷. 관리자 권한은 필요 없습니다.
인터넷에서 받은 .bat 이라 "Windows의 PC 보호" 창이 뜨면 **추가 정보 → 실행** 을 누릅니다.
설정 등록만 다시 하려면 `withplus` 폴더에서 `uv run python deploy\register_claude_desktop.py`.

### 직원 PC — 확장 파일(.mcpb) 설치 (무료 요금제 등 설정 파일 방식이 안 될 때)

`withplus-tax-<버전>.mcpb` 파일 하나를 직원에게 보내고, 직원은 **파일을 더블클릭 → Claude Desktop 설치 창에서 설치**만 하면 됩니다.
Python·패키지는 Claude Desktop이 처음 실행할 때 자동으로 준비합니다(1~2분). 데스크톱 확장은 무료 요금제를 포함한 모든 사용자가 쓸 수 있습니다.

- 만들기(저장소 최상위, Node.js 필요): `python withplus/deploy/build_mcpb.py` → `withplus/dist/withplus-tax-<버전>.mcpb`
- 업데이트: 원본 업데이트 후 다시 빌드해서 새 .mcpb 를 배포(같은 이름 확장은 덮어써짐)
- `staff_setup.bat` 으로 이미 등록한 PC에서 둘 다 켜지면 같은 도구가 두 번 보일 수 있으니 하나만 쓰세요.

## 4. 설치 B — mcp.withplustax.com 으로 외부 공개 (직원·테스트 세무사용)

전제: withplustax.com 이 Cloudflare에 연결되어 있고, 사무실 PC가 켜져 있어야 합니다. 포트 개방(공유기 설정)은 필요 없습니다.

1. 위 A의 1~4 완료
2. 토큰 발급: `deploy\new_token.bat` 실행 → 나온 문자열을 사람마다 하나씩
3. `withplus\.env` 를 메모장으로 열어 수정
   ```
   WITHPLUS_MODE=public
   WITHPLUS_PUBLIC_HOSTS=mcp.withplustax.com
   WITHPLUS_TOKENS=조덕희:토큰1,홍길동세무사:토큰2
   ```
4. `deploy\run_public.bat` 실행 → 창에 `허용 도메인: mcp.withplustax.com, 토큰 2개` 가 보이면 정상
5. Cloudflare Tunnel 연결 (명령 프롬프트, 최초 1회)
   ```
   winget install --id Cloudflare.cloudflared
   cloudflared tunnel login
   cloudflared tunnel create withplus-tax
   cloudflared tunnel route dns withplus-tax mcp.withplustax.com
   ```
   `deploy\cloudflared-config.example.yml` 을 `C:\Users\<사용자>\.cloudflared\config.yml` 로 복사(터널ID 채우기) 후
   `cloudflared service install` → 윈도우 서비스로 상시 실행
6. 자동 시작: `deploy\register_autostart.bat` (윈도우 로그인 시 서버 자동 실행)
7. 확인: 브라우저에서 `https://mcp.withplustax.com/health` → `{"status": "ok"}`

**사용자 연결 방법**

| 사용 환경 | 연결 |
|---|---|
| Claude Code | `claude mcp add --transport http withplus-tax https://mcp.withplustax.com/mcp --header "Authorization: Bearer 토큰"` |
| claude.ai / Claude Desktop "커스텀 커넥터" | URL에 `https://mcp.withplustax.com/mcp?key=토큰` 입력 (헤더 입력란이 없을 때 쓰는 방식 — 주소가 노출되면 토큰도 노출되므로 사람별로 발급하고 유출 시 그 토큰만 삭제) |

토큰 회수: `.env` 에서 그 사람 항목을 지우고 `run_public.bat` 재시작.

## 5. 업데이트 (매년 세법 개정 반영)

1. GitHub 내 포크 화면 → **Sync fork** → Update branch (withplus 폴더는 원본과 겹치지 않아 충돌 없음)
2. 사무실 PC에서 `deploy\update.bat` → 원본 1,400여 개 + 위드플러스 테스트가 모두 passed 인지 확인 → 서버 재시작

## 6. 검증 결과 (2026-11-03, 원본 v0.19.0)

| 항목 | 결과 |
|---|---|
| 원본 테스트 | 1,439 passed, 1 skipped |
| 위드플러스 테스트 | 13 passed (토큰·도메인·도구 차단·안내문구·로그·계산값) |
| 실제 서버 기동 후 공식 MCP 클라이언트로 호출 | public 89개 도구 / local 93개 도구 정상 |
| 퇴직금 1억·근속 15년(2026) | 2,175,000원 = 손계산 일치 |
| 과세표준 5억 법인세 2025 / 2026 | 75,000,000원 / 80,000,000원 (2026 세율 1%p 인상 반영) |
| 과소신고 추가세액 1천만원 일반 | 1,000,000원 (10%) |
| 납부지연 1천만원, 기한 2026-06-01 → 10-07 납부 | 128일 × 0.022% = 281,600원 |

## 7. 주의사항

- **연도표 2026년까지만** — 2027 귀속분은 원본이 업데이트되기 전까지 계산을 거부합니다(추정하지 않음). 원본 유지보수가 멈추면 연도표(`korean_tax_calc_mcp/data`, 엔진 코드)를 직접 갱신해야 합니다.
- **납부기한 휴일 순연은 자동 아님** — 납부지연가산세의 `due`에는 휴일 순연을 반영한 실제 기한을 넣어야 합니다(예: 2026.5.31.은 일요일 → 6.1.).
- **사실관계 판단은 세무사 몫** — 1세대1주택 요건, 특수관계, 업무관련성 등은 도구가 판단하지 않거나 입력값을 그대로 믿습니다.
- **고객 개인정보** — 계산 입력에는 실명·주민번호를 넣을 필요가 없습니다. 로그에는 입력값이 저장되지 않지만, Claude 대화 자체에는 남습니다.
- **사무실 PC 의존** — PC가 꺼지거나 절전되면 공개 서버도 멈춥니다(절전 해제 필요). 상시 운영이 중요해지면 클라우드 서버 이전을 검토.
- 원본 LICENSE(MIT, Upstage) 파일과 NOTICE를 지우지 마세요.

## 8. 파일

```
withplus/
  withplus_tax/server.py   운영 래퍼(이름·토큰·공개모드·로그·안내문구)
  withplus_tax/config.py   .env 설정 읽기
  tests/test_withplus.py   래퍼 테스트
  deploy/                  설치·실행·토큰·자동시작·업데이트 bat, Cloudflare·Claude Desktop 설정 예시
  .env.example             설정 견본(.env 로 복사해서 사용, Git 제외)
  NOTICE                   원저작자 고지
```
