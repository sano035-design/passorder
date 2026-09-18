# 패스오더 A/B 테스트 대시보드 디자인 시스템 명세서 (design.md)

본 문서는 패스오더(Pass Order) 교차 브랜드 통합 적립 A/B 테스트 성과 대시보드([`output/passorder_dashboard.html`](file:///c:/Users/sano0/OneDrive/문서/바탕%20화면/claudeproject/패스오더/output/passorder_dashboard.html))의 시각 스타일, UI/UX 컴포넌트, 디자인 토큰 및 인터랙션 표준 명세서입니다.

---

## 1. 디자인 컨셉 및 브랜드 아이덴티티 (Brand Identity & Tone)

* **Pass Order Dark Aesthetic (공식 다크 테마)**:
  - 공식 패스오더 비즈니스 웹사이트(`templates/passorder_tone_manner.png`)의 톤앤매너를 계승하여, 깊이 있는 **다크 블랙(`--bg-dark-root: #0A0C10`)**을 기본 캔버스로 적용.
  - 야간/실내 환경에서도 눈이 편안하며 데이터 시각화의 명도 대비를 극대화하는 프로덕트 분석 전용 다크 인터페이스.
* **Signature Pass Order Orange Accent (시그니처 주황 포인트)**:
  - 브랜드 핵심 상징색인 **비비드 오렌지(`--po-orange: #FF5C1E`, #FF6525)**를 활용하여 핵심 KPI, 주요 차트, 활성 탭에 생동감과 시각적 주목도를 부여.
  - 상단 로고(`templates/passorder_logo.png`)의 고유 타이포그래피를 재현하여 **'패스'(Pure White) + '오더'(Pass Order Orange)**의 강렬한 브랜드 일체감 형성.
* **High-Contrast Layered Cards (입체적 카드 레이어)**:
  - 배경(`var(--bg-dark-root)`) 위에 한 단계 밝은 다크 서피스(`var(--bg-card: #181B26)`)와 미세 보더(`var(--border-dark: #262A3B)`)를 둘러 컴포넌트 간의 뚜렷한 시각 위계(Visual Hierarchy) 구축.
* **Clutter-Free Data Table (정돈된 노-랩 표 레이아웃)**:
  - 가로 스크롤 및 불필요한 줄바꿈을 원천 차단(`white-space: nowrap`)하여 주차별 잔존율과 격차를 단정하고 균형 있게 표시.

---

## 2. 디자인 토큰 명세 (CSS Variables)

```css
:root {
  /* 1. 브랜드 주조색 (Pass Order Signature Orange) */
  --po-orange: #FF5C1E;                           /* 패스오더 대표 오렌지 */
  --po-orange-hover: #E84D12;                     /* 버튼 및 호버 인터랙션 */
  --po-orange-gradient: linear-gradient(135deg, #FF6525 0%, #FF4500 100%); /* KPI 카드 메인 그라데이션 */

  /* 2. 서피스 및 배경 (Dark Theme) */
  --bg-dark-root: #0A0C10;                       /* 최상위 페이지 배경 (Deep Dark Black) */
  --bg-header: #12141C;                          /* 상단 헤더 및 탭 네비게이션 서피스 */
  --bg-card: #181B26;                            /* 메인 차트 및 패널 카드 서피스 */
  --bg-card-hover: #1E2230;                      /* 인터랙티브 카드 호버 서피스 */

  /* 3. 보더 및 구분선 */
  --border-dark: #262A3B;                        /* 표준 컴포넌트 경계선 */
  --border-subtle: #1F2230;                      /* 테이블 행 및 얇은 구분선 */

  /* 4. 타이포그래피 컬러 (High-Contrast Scale) */
  --text-white: #FFFFFF;                         /* 순백색 (헤더, 핵심 수치, 타이틀) */
  --text-gray-light: #E2E8F0;                    /* 본문 및 서브 헤더 */
  --text-gray-muted: #94A3B8;                    /* 라벨, 축 눈금, 비활성 텍스트 */
  --text-gray-dim: #64748B;                      /* 부가 캡션 및 미세 안내 */

  /* 5. 시맨틱 액센트 컬러 */
  --emerald-bright: #10B981;                     /* 긍정적 성과 / 리프트 (Green) */
  --emerald-soft: rgba(16, 185, 129, 0.15);     /* 에메랄드 소프트 배지 배경 */
  --orange-soft: rgba(255, 92, 30, 0.15);       /* 오렌지 소프트 배지 배경 */

  /* 6. 형태 및 그림자 */
  --radius-xl: 18px;                             /* 헤더 및 대형 패널 라운딩 */
  --radius-lg: 14px;                             /* KPI 카드 및 내부 박스 라운딩 */
  --radius-md: 10px;                             /* 탭 버튼 및 알약 배지 라운딩 */
  --shadow-dark: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
}
```

---

## 3. 타이포그래피 시스템 (Typography)

* **기본 폰트 패밀리**: 
  - 본문/UI: `"Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
  - 숫자/KPI 수치: `'Outfit', sans-serif` (모던 지오메트릭 넘버 폰트)
* **타이포그래피 스케일**:
  - `Header Title`: 21px, Weight 800, Letter-spacing -0.4px
  - `Panel Title`: 17px, Weight 800, Letter-spacing -0.3px
  - `KPI Main Number`: 28px, Weight 900, Font Outfit
  - `Body / Table Cell`: 13px, Weight 500 / 700 (Data values)
  - `Badge / Tag Label`: 11px ~ 12px, Weight 700 ~ 800

---

## 4. 컴포넌트별 상세 스타일 가이드

### 4.1. 상단 공식 로고 컴포넌트 (`.po-official-logo`)
- **디자인 출처**: `templates/passorder_logo.png`
- **스타일**:
  ```css
  .po-official-logo {
    display: inline-flex;
    align-items: center;
    font-weight: 900;
    font-size: 30px;
    letter-spacing: -1px;
    padding: 6px 14px;
    background: #0E1017;
    border-radius: 12px;
    border: 1px solid #222636;
  }
  .po-logo-pass { color: #FFFFFF; }
  .po-logo-order { color: #FF5C1E; }
  ```

### 4.2. 대조군 A vs 실험군 B 식별 미니 카드 (`.group-mini-card`)
- **목적**: 방문자가 어떤 그룹이 기존 방식이고 어떤 그룹이 신규 기획인지 0.5초 만에 인지.
- **스타일**:
  - **대조군 A**: 모노톤 차콜 카드(`background: #181B26`, `border: 1px solid #2B2F42`), 아이콘 🏪, 설명: *기존 단일 매장 스탬프 (교차 불가 ❌)*
  - **실험군 B**: 소프트 오렌지 글로우 카드(`background: rgba(255, 92, 30, 0.1)`, `border: 1px solid rgba(255, 92, 30, 0.4)`), 아이콘 ☕, 설명: *교차 브랜드 통합 적립 (전 매장 사용 ⭕)*

### 4.3. 주황색 핵심 KPI 카드 (`.kpi-orange-card`)
- **스타일**:
  - 배경: `var(--po-orange-gradient)` (선명하고 따뜻한 비비드 주황 그라데이션)
  - 텍스트: **100% 순백색(White `#FFFFFF`)**
  - 장식: 우측 상단 반투명 원형 데코레이션(`rgba(255, 255, 255, 0.08)`)으로 입체감 부여
  - 대조군 비교 텍스트 및 Lift 배지: 화이트 알약 배지(`background: #FFFFFF; color: #E84D12; font-weight: 900;`)

### 4.4. 주차별 잔존율 표 (Strict No-Wrap Table)
- **스타일**:
  - 모든 `<th>`, `<td>`에 `white-space: nowrap;` 강제 적용.
  - 실험군 B 수치 열: 소프트 오렌지 틴트(`background: rgba(255, 92, 30, 0.07); color: #FFA585; font-weight: 800;`).
  - 성과 격차 열: 에메랄드 그린 배지(`background: rgba(16, 185, 129, 0.15); color: #34D399;`).
  - Week 12 최종 주차 행: 은은한 하이라이트 배경으로 약 3배 유지 성과 강조.

### 4.5. 핵심 구간별 전환율 세로 막대 그래프 (`stageConversionChart`)
- **목적**: 텍스트 형태의 서술을 배제하고, 구간별 전환율과 이탈 방어 효과를 직관적으로 비교.
- **시각적 특징**:
  - `topValuesPlugin`을 커스텀 탑재하여 **막대 최상단에 정확한 전환율 수치(82.9%, 90.8% 등)를 흰색 볼드 텍스트로 상시 표기**.
  - 결제확인 ➔ 최종구매 구간(A군 81.5% vs B군 90.8%)에 핵심 방어 구간 별표(★) 라벨링.

---

## 5. 반응형 브레이크포인트 가이드

- **데스크톱 와이드 (1400px 이상)**: 5열 KPI 그리드, 2분할 메인 차트/표 레이아웃 최적화.
- **일반 랩탑/태블릿 (768px ~ 1200px)**: 3열 KPI 그리드 자동 재배치, 차트 및 테이블 상하 스택 배치.
- **모바일 (768px 이하)**: 1열 KPI 스택, 탭 네비게이션 세로 전환, 표 가로 터치 스크롤 지원.
