"""
패스오더(Pass Order) 교차 브랜드 통합 적립 A/B 테스트 대시보드 HTML 생성기 (v2 - 패스오더 공식 톤앤매너 다크 테마)
-----------------------------------------------------------------------------------------------------------------
수정 사항 반영:
1. 상단 왼쪽 로고: 패스오더 공식 로고 폰트 및 컬러 ("패스"(흰색) + "오더"(주황색))
2. 데이터 수식 및 코드 검증 센터 탭 삭제
3. 실제 로그 샘플 행 해석 케이스 스터디 삭제
4. 핵심 KPI 네모 상자: 주황색 배경(Pass Order Orange) + 하얀색 글씨
5. 상단 오른쪽: 그룹 A(대조군: 단일 매장 스탬프) vs 그룹 B(실험군: 교차 통합 적립) 명확하고 직관적인 카드/배지
6. 패스오더 공식 톤앤매너(다크 블랙/차콜 테마 + 오렌지 시그니처) 전면 적용
7. 1가설검증 탭 제일 아래 "왜 90일 테스트에서..." 배너 삭제
8. 1가설검증 탭 주차별 잔존율 상세 비교 표: 글자 줄바꿈 없이(white-space: nowrap) 깔끔하게 정리
9. 14단계 행동 퍼널 탭: 핵심 구간별 전환율을 텍스트 대신 '수치가 상단에 표시되는 세로 막대 그래프'로 시각화
"""

import os
import sys
import json
import pandas as pd
import numpy as np

# 콘솔 UTF-8 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "passorder_event_log_90d.csv")
if not os.path.exists(DATA_FILE):
    DATA_FILE = os.path.join(BASE_DIR, "..", "passorder_event_log_90d.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_HTML = os.path.join(OUTPUT_DIR, "payorder_dashborad.html")

print(f"[1/4] 데이터 로딩 및 분석 중: {DATA_FILE}...")
df = pd.read_csv(DATA_FILE)

df['event_dt'] = pd.to_datetime(df['event_time'])
df['date_str'] = df['event_dt'].dt.strftime('%Y-%m-%d')
total_rows = len(df)

# -------------------------------------------------------------
# 1. 5대 핵심 KPI 집계
# -------------------------------------------------------------
users_per_grp = df.groupby('ab_test_group')['user_id'].nunique().to_dict()
total_users_a = users_per_grp.get('Group A (Control)', 1250)
total_users_b = users_per_grp.get('Group B (Treatment)', 1250)

# DAU 집계 (일자별 고유 유저 수)
daily_dau = df.groupby(['ab_test_group', 'date_str'])['user_id'].nunique().reset_index()
avg_dau_a = float(daily_dau[daily_dau['ab_test_group'] == 'Group A (Control)']['user_id'].mean())
avg_dau_b = float(daily_dau[daily_dau['ab_test_group'] == 'Group B (Treatment)']['user_id'].mean())

# 세션 집계
user_sess = df.groupby(['ab_test_group', 'user_id'])['session_id'].nunique().reset_index()
avg_sess_a = float(user_sess[user_sess['ab_test_group'] == 'Group A (Control)']['session_id'].mean())
avg_sess_b = float(user_sess[user_sess['ab_test_group'] == 'Group B (Treatment)']['session_id'].mean())

# 주문 집계 (purchase)
purchase_df = df[df['event_name'] == 'purchase']
orders_a = int(len(purchase_df[purchase_df['ab_test_group'] == 'Group A (Control)']))
orders_b = int(len(purchase_df[purchase_df['ab_test_group'] == 'Group B (Treatment)']))
orders_per_user_a = orders_a / total_users_a
orders_per_user_b = orders_b / total_users_b

# 교차 주문율
cross_orders_a = int(purchase_df[purchase_df['ab_test_group'] == 'Group A (Control)']['is_cross_brand_order'].sum())
cross_orders_b = int(purchase_df[purchase_df['ab_test_group'] == 'Group B (Treatment)']['is_cross_brand_order'].sum())
cross_rate_a = (cross_orders_a / orders_a) * 100 if orders_a > 0 else 0
cross_rate_b = (cross_orders_b / orders_b) * 100 if orders_b > 0 else 0

# 최종 결제 전환율 (choose_payment_methods -> purchase)
cpm_a = int(len(df[(df['ab_test_group'] == 'Group A (Control)') & (df['event_name'] == 'choose_payment_methods')]))
cpm_b = int(len(df[(df['ab_test_group'] == 'Group B (Treatment)') & (df['event_name'] == 'choose_payment_methods')]))
cvr_a = (orders_a / cpm_a) * 100 if cpm_a > 0 else 0
cvr_b = (orders_b / cpm_b) * 100 if cpm_b > 0 else 0

# -------------------------------------------------------------
# 2. 일별 시계열 데이터 (DAU 90일)
# -------------------------------------------------------------
dates_sorted = sorted(daily_dau['date_str'].unique())
dau_ts_a = []
dau_ts_b = []
for d in dates_sorted:
    val_a = daily_dau[(daily_dau['ab_test_group'] == 'Group A (Control)') & (daily_dau['date_str'] == d)]
    val_b = daily_dau[(daily_dau['ab_test_group'] == 'Group B (Treatment)') & (daily_dau['date_str'] == d)]
    dau_ts_a.append(int(val_a['user_id'].values[0]) if len(val_a) > 0 else 0)
    dau_ts_b.append(int(val_b['user_id'].values[0]) if len(val_b) > 0 else 0)

# -------------------------------------------------------------
# 3. 주차별 코호트 잔존율 곡선 (Week 0 ~ Week 12)
# -------------------------------------------------------------
user_first_dt = df.groupby('user_id')['event_dt'].min().dt.floor('D')
df['signup_date'] = df['user_id'].map(user_first_dt)
df['day_diff'] = (df['event_dt'].dt.floor('D') - df['signup_date']).dt.days

weeks_list = list(range(0, 13))
retention_curve_a = []
retention_curve_b = []

for w in weeks_list:
    w_start = w * 7
    w_end = min(89, w * 7 + 6)
    if w == 0:
        retention_curve_a.append(100.0)
        retention_curve_b.append(100.0)
    else:
        w_df = df[(df['day_diff'] >= w_start) & (df['day_diff'] <= w_end)]
        users_a = w_df[w_df['ab_test_group'] == 'Group A (Control)']['user_id'].nunique()
        users_b = w_df[w_df['ab_test_group'] == 'Group B (Treatment)']['user_id'].nunique()
        retention_curve_a.append(round((users_a / total_users_a) * 100, 1))
        retention_curve_b.append(round((users_b / total_users_b) * 100, 1))

# -------------------------------------------------------------
# 4. 14단계 퍼널 전이 데이터 & 핵심 구간별 전환율
# -------------------------------------------------------------
FUNNEL_STEPS = [
    "app_open",
    "map_page (main)",
    "Click_cafe_location",
    "Search_function",
    "Click_cafe",
    "Click_To_go_menu",
    "Click_Here_menu",
    "Touch_categories",
    "click_Menu",
    "add_to_cart",
    "choose_pick_up_time",
    "input_order_request",
    "choose_payment_methods",
    "purchase"
]

funnel_counts_a = []
funnel_counts_b = []
for step in FUNNEL_STEPS:
    cnt_a = int(len(df[(df['ab_test_group'] == 'Group A (Control)') & (df['event_name'] == step)]))
    cnt_b = int(len(df[(df['ab_test_group'] == 'Group B (Treatment)') & (df['event_name'] == step)]))
    funnel_counts_a.append(cnt_a)
    funnel_counts_b.append(cnt_b)

# 핵심 4대 구간별 전환율 산출
# 1) 매장 ➔ 장바구니 (Click_cafe -> add_to_cart)
cafe_a = len(df[(df['ab_test_group'] == 'Group A (Control)') & (df['event_name'] == 'Click_cafe')])
cafe_b = len(df[(df['ab_test_group'] == 'Group B (Treatment)') & (df['event_name'] == 'Click_cafe')])
cart_a = len(df[(df['ab_test_group'] == 'Group A (Control)') & (df['event_name'] == 'add_to_cart')])
cart_b = len(df[(df['ab_test_group'] == 'Group B (Treatment)') & (df['event_name'] == 'add_to_cart')])

stage1_a = round((cart_a / cafe_a) * 100, 1)
stage1_b = round((cart_b / cafe_b) * 100, 1)

# 2) 장바구니 ➔ 결제화면 (add_to_cart -> choose_payment_methods)
stage2_a = round((cpm_a / cart_a) * 100, 1)
stage2_b = round((cpm_b / cart_b) * 100, 1)

# 3) 결제화면 ➔ 구매완료 (choose_payment_methods -> purchase)
stage3_a = round((orders_a / cpm_a) * 100, 1)
stage3_b = round((orders_b / cpm_b) * 100, 1)

# 4) 전체 앱오픈 ➔ 구매완료 (app_open -> purchase)
open_a = len(df[(df['ab_test_group'] == 'Group A (Control)') & (df['event_name'] == 'app_open')])
open_b = len(df[(df['ab_test_group'] == 'Group B (Treatment)') & (df['event_name'] == 'app_open')])
stage4_a = round((orders_a / open_a) * 100, 1)
stage4_b = round((orders_b / open_b) * 100, 1)

stage_labels = ["1. 매장선택 ➔ 장바구니", "2. 장바구니 ➔ 결제확인", "3. 결제확인 ➔ 최종구매 ★", "4. 전체 퍼널 (오픈➔구매)"]
stage_rates_a = [stage1_a, stage2_a, stage3_a, stage4_a]
stage_rates_b = [stage1_b, stage2_b, stage3_b, stage4_b]

# -------------------------------------------------------------
# 5. 브랜드별 주문 분포 & 포인트 순환 지표
# -------------------------------------------------------------
brand_counts_a = purchase_df[purchase_df['ab_test_group'] == 'Group A (Control)']['cafe_brand'].value_counts().to_dict()
brand_counts_b = purchase_df[purchase_df['ab_test_group'] == 'Group B (Treatment)']['cafe_brand'].value_counts().to_dict()

all_brands = ["메가커피", "컴포즈커피", "빽다방", "텐퍼센트커피", "매머드커피", "개인스페셜티카페"]
brand_data_a = [int(brand_counts_a.get(b, 0)) for b in all_brands]
brand_data_b = [int(brand_counts_b.get(b, 0)) for b in all_brands]

pts_earned_total = int(purchase_df[purchase_df['ab_test_group'] == 'Group B (Treatment)']['earned_reward_point'].sum())
pts_used_total = int(purchase_df[purchase_df['ab_test_group'] == 'Group B (Treatment)']['used_reward_point'].sum())
pts_used_orders_cnt = int(len(purchase_df[(purchase_df['ab_test_group'] == 'Group B (Treatment)') & (purchase_df['used_reward_point'] > 0)]))
pts_used_ratio = round((pts_used_orders_cnt / orders_b) * 100, 1)

# JSON 패키징
data_payload = {
    "kpi": {
        "avg_dau_a": round(avg_dau_a, 1),
        "avg_dau_b": round(avg_dau_b, 1),
        "dau_lift": round(((avg_dau_b / avg_dau_a) - 1) * 100, 1),
        "avg_sess_a": round(avg_sess_a, 1),
        "avg_sess_b": round(avg_sess_b, 1),
        "sess_lift": round(((avg_sess_b / avg_sess_a) - 1) * 100, 1),
        "orders_per_user_a": round(orders_per_user_a, 1),
        "orders_per_user_b": round(orders_per_user_b, 1),
        "orders_lift": round(((orders_per_user_b / orders_per_user_a) - 1) * 100, 1),
        "cross_rate_a": round(cross_rate_a, 1),
        "cross_rate_b": round(cross_rate_b, 1),
        "cross_diff": round(cross_rate_b - cross_rate_a, 1),
        "cvr_a": round(cvr_a, 1),
        "cvr_b": round(cvr_b, 1),
        "cvr_diff": round(cvr_b - cvr_a, 1),
        "orders_a": orders_a,
        "orders_b": orders_b
    },
    "chart_dates": dates_sorted,
    "dau_ts_a": dau_ts_a,
    "dau_ts_b": dau_ts_b,
    "weeks": [f"W{w}" for w in weeks_list],
    "retention_a": retention_curve_a,
    "retention_b": retention_curve_b,
    "funnel_steps": FUNNEL_STEPS,
    "funnel_a": funnel_counts_a,
    "funnel_b": funnel_counts_b,
    "stage_labels": stage_labels,
    "stage_rates_a": stage_rates_a,
    "stage_rates_b": stage_rates_b,
    "brands": all_brands,
    "brand_orders_a": brand_data_a,
    "brand_orders_b": brand_data_b,
    "points": {
        "earned_total": pts_earned_total,
        "used_total": pts_used_total,
        "used_orders_cnt": pts_used_orders_cnt,
        "used_ratio": pts_used_ratio
    }
}

data_json_str = json.dumps(data_payload, ensure_ascii=False)

# -------------------------------------------------------------
# 6. 패스오더 공식 톤앤매너 다크 테마 HTML 작성
# -------------------------------------------------------------
html_template = f'''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>패스오더 교차 브랜드 통합 적립 A/B 테스트 성과 대시보드</title>
  
  <!-- Pretendard & Outfit Fonts -->
  <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800;900&display=swap" rel="stylesheet">
  
  <!-- Chart.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    :root {{
      --po-orange: #FF5C1E;
      --po-orange-hover: #E84D12;
      --po-orange-gradient: linear-gradient(135deg, #FF6525 0%, #FF4500 100%);
      --bg-dark-root: #0A0C10;
      --bg-header: #12141C;
      --bg-card: #181B26;
      --bg-card-hover: #1E2230;
      --border-dark: #262A3B;
      --border-subtle: #1F2230;
      --text-white: #FFFFFF;
      --text-gray-light: #E2E8F0;
      --text-gray-muted: #94A3B8;
      --text-gray-dim: #64748B;
      --emerald-bright: #10B981;
      --radius-xl: 18px;
      --radius-lg: 14px;
      --radius-md: 10px;
      --shadow-dark: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}

    body {{
      background-color: var(--bg-dark-root);
      color: var(--text-white);
      min-height: 100vh;
      padding: 24px 32px 60px;
    }}

    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}

    /* 1. Header Bar with Authentic Pass Order Logo */
    .top-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--bg-header);
      padding: 20px 30px;
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow-dark);
      margin-bottom: 24px;
      border: 1px solid var(--border-dark);
    }}

    .header-brand-wrap {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}

    /* Official Pass Order Logo Style */
    .po-official-logo {{
      display: inline-flex;
      align-items: center;
      font-family: "Pretendard", sans-serif;
      font-weight: 900;
      font-size: 30px;
      letter-spacing: -1px;
      line-height: 1;
      user-select: none;
      padding: 6px 14px;
      background: #0E1017;
      border-radius: 12px;
      border: 1px solid #222636;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }}

    .po-logo-pass {{
      color: #FFFFFF;
      margin-right: 2px;
    }}

    .po-logo-order {{
      color: var(--po-orange);
    }}

    .header-text-block h1 {{
      font-size: 21px;
      font-weight: 800;
      color: var(--text-white);
      letter-spacing: -0.4px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .header-text-block p {{
      font-size: 13px;
      color: var(--text-gray-muted);
      margin-top: 5px;
    }}

    /* Top Right: Distinct A/B Comparison Cards */
    .header-groups-wrap {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .group-mini-card {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 16px;
      border-radius: 12px;
      background: #181B26;
      border: 1px solid #2B2F42;
    }}

    .group-mini-card.group-b {{
      background: rgba(255, 92, 30, 0.1);
      border: 1px solid rgba(255, 92, 30, 0.4);
    }}

    .group-icon-badge {{
      width: 36px;
      height: 36px;
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 17px;
      flex-shrink: 0;
    }}

    .icon-a {{
      background: #2A2E40;
      color: #94A3B8;
    }}

    .icon-b {{
      background: var(--po-orange);
      color: #FFFFFF;
      box-shadow: 0 4px 12px rgba(255, 92, 30, 0.4);
    }}

    .group-mini-info {{
      display: flex;
      flex-direction: column;
    }}

    .group-mini-title {{
      font-size: 13px;
      font-weight: 800;
      color: var(--text-white);
    }}

    .group-mini-desc {{
      font-size: 11px;
      color: var(--text-gray-muted);
      margin-top: 2px;
    }}

    .group-b .group-mini-desc {{
      color: #FFA585;
      font-weight: 600;
    }}

    /* 2. Key KPI Scorecards: ORANGE BACKGROUND + WHITE TEXT */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }}

    .kpi-orange-card {{
      background: var(--po-orange-gradient);
      border-radius: var(--radius-lg);
      padding: 22px 20px;
      color: #FFFFFF;
      box-shadow: 0 10px 20px -5px rgba(255, 69, 0, 0.35);
      border: 1px solid rgba(255, 255, 255, 0.2);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      position: relative;
      overflow: hidden;
    }}

    .kpi-orange-card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 16px 28px -6px rgba(255, 69, 0, 0.45);
    }}

    .kpi-orange-card::after {{
      content: '';
      position: absolute;
      top: -30px;
      right: -30px;
      width: 90px;
      height: 90px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 50%;
      pointer-events: none;
    }}

    .kpi-title {{
      font-size: 13px;
      font-weight: 700;
      color: rgba(255, 255, 255, 0.92);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .kpi-main-val {{
      font-size: 28px;
      font-weight: 900;
      font-family: 'Outfit', sans-serif;
      color: #FFFFFF;
      display: flex;
      align-items: baseline;
      gap: 4px;
      letter-spacing: -0.5px;
    }}

    .kpi-unit {{
      font-size: 14px;
      font-weight: 700;
      color: rgba(255, 255, 255, 0.85);
    }}

    .kpi-comparison {{
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.22);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
    }}

    .kpi-control-text {{
      color: rgba(255, 255, 255, 0.88);
      font-weight: 600;
    }}

    .kpi-lift-pill {{
      background: #FFFFFF;
      color: #E84D12;
      font-weight: 900;
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 6px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
    }}

    /* 3. Navigation Tabs (Clean 3 Tabs) */
    .tabs-nav {{
      display: flex;
      gap: 12px;
      background: var(--bg-header);
      padding: 8px 10px;
      border-radius: var(--radius-lg);
      border: 1px solid var(--border-dark);
      margin-bottom: 24px;
      box-shadow: var(--shadow-dark);
    }}

    .tab-btn {{
      flex: 1;
      padding: 13px 20px;
      border: none;
      background: transparent;
      border-radius: var(--radius-md);
      font-size: 14px;
      font-weight: 700;
      color: var(--text-gray-muted);
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }}

    .tab-btn:hover {{
      background: #1D212F;
      color: var(--text-white);
    }}

    .tab-btn.active {{
      background: var(--po-orange);
      color: #FFFFFF;
      box-shadow: 0 4px 14px rgba(255, 92, 30, 0.35);
    }}

    /* Tab Panels */
    .tab-panel {{
      display: none;
    }}

    .tab-panel.active {{
      display: block;
      animation: fadeIn 0.25s ease;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Card Panels in Dark Theme */
    .dashboard-grid-2 {{
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}

    .dashboard-grid-equal {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}

    .dark-card-panel {{
      background: var(--bg-card);
      border-radius: var(--radius-xl);
      padding: 24px 28px;
      border: 1px solid var(--border-dark);
      box-shadow: var(--shadow-dark);
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }}

    .panel-title-wrap h3 {{
      font-size: 17px;
      font-weight: 800;
      color: var(--text-white);
      letter-spacing: -0.3px;
    }}

    .panel-title-wrap p {{
      font-size: 13px;
      color: var(--text-gray-muted);
      margin-top: 4px;
    }}

    .chart-container {{
      position: relative;
      width: 100%;
      height: 330px;
    }}

    /* Strict No-Wrap Clean Table for Retention Heatmap */
    .retention-clean-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      white-space: nowrap; /* 글자 줄바꿈 원천 방지 */
    }}

    .retention-clean-table th {{
      background: #11141D;
      padding: 12px 14px;
      font-weight: 700;
      color: var(--text-gray-muted);
      text-align: center;
      border-bottom: 1px solid var(--border-dark);
      white-space: nowrap;
    }}

    .retention-clean-table td {{
      padding: 13px 14px;
      border-bottom: 1px solid #1E2230;
      color: var(--text-gray-light);
      text-align: center;
      white-space: nowrap;
    }}

    .retention-clean-table tr:hover td {{
      background: #1F2333;
    }}

    .retention-clean-table td.highlight-b {{
      color: #FFA585;
      font-weight: 800;
      background: rgba(255, 92, 30, 0.07);
    }}

    .lift-tag-badge {{
      display: inline-block;
      font-size: 11px;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 6px;
      white-space: nowrap;
    }}

    .lift-tag-badge.green {{
      background: rgba(16, 185, 129, 0.15);
      color: #34D399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .lift-tag-badge.orange {{
      background: rgba(255, 92, 30, 0.2);
      color: #FF8554;
      border: 1px solid rgba(255, 92, 30, 0.4);
    }}

    /* Period Memo Box next to Chart Title */
    .period-memo-box {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: #11141E;
      border: 1px solid rgba(255, 92, 30, 0.4);
      color: #FFA585;
      font-size: 12px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 6px;
      letter-spacing: -0.2px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }}

    /* Responsive */
    @media (max-width: 1200px) {{
      .kpi-grid {{
        grid-template-columns: repeat(3, 1fr);
      }}
      .dashboard-grid-2, .dashboard-grid-equal {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 768px) {{
      body {{
        padding: 16px;
      }}
      .kpi-grid {{
        grid-template-columns: 1fr;
      }}
      .top-header {{
        flex-direction: column;
        align-items: flex-start;
        gap: 16px;
      }}
      .tabs-nav {{
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>

<div class="container">

  <!-- 1. Top Header with Official Pass Order Logo & Distinct Group A/B Cards -->
  <header class="top-header">
    <div class="header-brand-wrap">
      <!-- Official Logo: '패스'(White) + '오더'(Orange) -->
      <div class="po-official-logo">
        <span class="po-logo-pass">패스</span><span class="po-logo-order">오더</span>
      </div>
      <div class="header-text-block">
        <h1>교차 브랜드 통합 적립 90일 A/B 테스트 대시보드</h1>
        <p>가설 검증: 프랜차이즈 커피 자체 앱 종속 방어 및 전 매장 통합 리워드를 통한 고객 리텐션 락인(Lock-in)</p>
      </div>
    </div>

    <!-- Clear & Concise A/B Group Identifier -->
    <div class="header-groups-wrap">
      <div class="group-mini-card">
        <div class="group-icon-badge icon-a">🏪</div>
        <div class="group-mini-info">
          <span class="group-mini-title">대조군 A (1,250명)</span>
          <span class="group-mini-desc">기존 단일 매장 스탬프 (교차 불가 ❌)</span>
        </div>
      </div>

      <div class="group-mini-card group-b">
        <div class="group-icon-badge icon-b">☕</div>
        <div class="group-mini-info">
          <span class="group-mini-title" style="color: #FF8554;">실험군 B (1,250명)</span>
          <span class="group-mini-desc">교차 브랜드 통합 적립 (전 매장 사용 ⭕)</span>
        </div>
      </div>
    </div>
  </header>

  <!-- 2. Top 5 Key KPI Cards: ORANGE BACKGROUND + WHITE TEXT -->
  <section class="kpi-grid">
    <!-- Card 1: DAU -->
    <div class="kpi-orange-card">
      <div class="kpi-title">일일 활성 유저 (평균 DAU)</div>
      <div class="kpi-main-val">
        {data_payload['kpi']['avg_dau_b']} <span class="kpi-unit">명</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">A군 {data_payload['kpi']['avg_dau_a']}명</span>
        <span class="kpi-lift-pill">▲ +{data_payload['kpi']['dau_lift']}%</span>
      </div>
    </div>

    <!-- Card 2: Sessions per User -->
    <div class="kpi-orange-card">
      <div class="kpi-title">인당 평균 방문 세션</div>
      <div class="kpi-main-val">
        {data_payload['kpi']['avg_sess_b']} <span class="kpi-unit">회</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">A군 {data_payload['kpi']['avg_sess_a']}회</span>
        <span class="kpi-lift-pill">▲ +{data_payload['kpi']['sess_lift']}%</span>
      </div>
    </div>

    <!-- Card 3: Orders per User -->
    <div class="kpi-orange-card">
      <div class="kpi-title">인당 커피 구매 빈도</div>
      <div class="kpi-main-val">
        {data_payload['kpi']['orders_per_user_b']} <span class="kpi-unit">잔</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">A군 {data_payload['kpi']['orders_per_user_a']}잔</span>
        <span class="kpi-lift-pill">▲ +{data_payload['kpi']['orders_lift']}%</span>
      </div>
    </div>

    <!-- Card 4: Cross Brand Rate -->
    <div class="kpi-orange-card">
      <div class="kpi-title">교차 브랜드 주문율</div>
      <div class="kpi-main-val">
        {data_payload['kpi']['cross_rate_b']} <span class="kpi-unit">%</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">A군 {data_payload['kpi']['cross_rate_a']}%</span>
        <span class="kpi-lift-pill">▲ +{data_payload['kpi']['cross_diff']}%p</span>
      </div>
    </div>

    <!-- Card 5: Checkout Conversion -->
    <div class="kpi-orange-card">
      <div class="kpi-title">결제 최종 전환율 (CVR)</div>
      <div class="kpi-main-val">
        {data_payload['kpi']['cvr_b']} <span class="kpi-unit">%</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">A군 {data_payload['kpi']['cvr_a']}%</span>
        <span class="kpi-lift-pill">▲ +{data_payload['kpi']['cvr_diff']}%p</span>
      </div>
    </div>
  </section>

  <!-- 3. Navigation Tabs (Focused 3 Tabs) -->
  <nav class="tabs-nav">
    <button class="tab-btn active" onclick="switchTab('tab-retention')">📈 1. 가설 검증 & 코호트 리텐션</button>
    <button class="tab-btn" onclick="switchTab('tab-funnel')">🛒 2. 14단계 행동 퍼널 분석</button>
    <button class="tab-btn" onclick="switchTab('tab-cross')">☕ 3. 교차 브랜드 이용 분석</button>
  </nav>

  <!-- ================= TAB 1: 코호트 리텐션 ================= -->
  <div id="tab-retention" class="tab-panel active">
    <div class="dashboard-grid-2">
      <!-- Retention Curve Chart -->
      <div class="dark-card-panel">
        <div class="panel-header">
          <div class="panel-title-wrap">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <h3>90일 장기 코호트 리텐션 곡선 (Week 0 ~ Week 12)</h3>
              <span class="period-memo-box">📅 2026.06.01 ~ 2026.08.29 (90일간)</span>
            </div>
            <p>최초 온보딩 시점 이후 경과 주차별 고유 접속 잔존율 비교</p>
          </div>
        </div>
        <div class="chart-container">
          <canvas id="retentionChart"></canvas>
        </div>
      </div>

      <!-- Weekly Retention Clean Table (NO-WRAP) -->
      <div class="dark-card-panel">
        <div class="panel-header">
          <div class="panel-title-wrap">
            <h3>주차별 잔존율 상세 비교 (Heatmap)</h3>
            <p>1개월, 2개월, 3개월 경과 시점의 잔존 격차</p>
          </div>
        </div>
        <div style="overflow-x: auto;">
          <table class="retention-clean-table">
            <thead>
              <tr>
                <th>구간</th>
                <th>경과 기간</th>
                <th>대조군 A</th>
                <th>실험군 B (통합적립)</th>
                <th>성과 격차 (Lift)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Week 1</strong></td>
                <td>D+7 ~ D+13</td>
                <td>{data_payload['retention_a'][1]}%</td>
                <td class="highlight-b">{data_payload['retention_b'][1]}%</td>
                <td><span class="lift-tag-badge green">+{round(data_payload['retention_b'][1] - data_payload['retention_a'][1], 1)}%p</span></td>
              </tr>
              <tr>
                <td><strong>Week 2</strong></td>
                <td>D+14 ~ D+20</td>
                <td>{data_payload['retention_a'][2]}%</td>
                <td class="highlight-b">{data_payload['retention_b'][2]}%</td>
                <td><span class="lift-tag-badge green">+{round(data_payload['retention_b'][2] - data_payload['retention_a'][2], 1)}%p</span></td>
              </tr>
              <tr>
                <td><strong>Week 4</strong></td>
                <td>1개월 (D+28~34)</td>
                <td>{data_payload['retention_a'][4]}%</td>
                <td class="highlight-b">{data_payload['retention_b'][4]}%</td>
                <td><span class="lift-tag-badge green">+{round(data_payload['retention_b'][4] - data_payload['retention_a'][4], 1)}%p</span></td>
              </tr>
              <tr>
                <td><strong>Week 8</strong></td>
                <td>2개월 (D+56~62)</td>
                <td>{data_payload['retention_a'][8]}%</td>
                <td class="highlight-b">{data_payload['retention_b'][8]}%</td>
                <td><span class="lift-tag-badge green">+{round(data_payload['retention_b'][8] - data_payload['retention_a'][8], 1)}%p</span></td>
              </tr>
              <tr style="background: rgba(255, 92, 30, 0.12);">
                <td><strong style="color: #FFA585;">Week 12</strong></td>
                <td>3개월 (D+84~89)</td>
                <td>{data_payload['retention_a'][12]}%</td>
                <td class="highlight-b" style="color: #FF5C1E; font-size: 14px;">{data_payload['retention_b'][12]}%</td>
                <td><span class="lift-tag-badge orange">▲ 약 3배 유지</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Daily DAU Time-Series Area Chart -->
    <div class="dark-card-panel">
      <div class="panel-header">
        <div class="panel-title-wrap">
          <h3>90일간 일일 활성 사용자 수 (DAU) 일자별 추이</h3>
          <p>주중 출퇴근 피크와 주말 패턴, 그리고 시간 경과에 따른 활동 유저 베이스라인 비교</p>
        </div>
      </div>
      <div class="chart-container" style="height: 280px;">
        <canvas id="dauChart"></canvas>
      </div>
    </div>
  </div>

  <!-- ================= TAB 2: 행동 퍼널 분석 ================= -->
  <div id="tab-funnel" class="tab-panel">
    <div class="dashboard-grid-equal">
      <!-- 14-Stage Funnel Chart -->
      <div class="dark-card-panel">
        <div class="panel-header">
          <div class="panel-title-wrap">
            <h3>14단계 스마트오더 행동 퍼널 규모 비교</h3>
            <p>앱 실행(app_open)부터 최종 구매(purchase)까지 단계별 잔존 로그 수</p>
          </div>
        </div>
        <div class="chart-container" style="height: 380px;">
          <canvas id="funnelChart"></canvas>
        </div>
      </div>

      <!-- KEY CONVERSION STAGES: VERTICAL BAR CHART WITH VALUES ON TOP -->
      <div class="dark-card-panel">
        <div class="panel-header">
          <div class="panel-title-wrap">
            <h3>핵심 구간별 전환율 비교 (세로 막대 그래프)</h3>
            <p>단계별 전환율(%)과 결제 직전 이탈 방어 효과 (막대 위 수치 표기)</p>
          </div>
        </div>
        <div class="chart-container" style="height: 380px;">
          <canvas id="stageConversionChart"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= TAB 3: 교차 브랜드 이용 분석 ================= -->
  <div id="tab-cross" class="tab-panel">
    <div class="dashboard-grid-equal">
      <!-- Brand Distribution Chart -->
      <div class="dark-card-panel">
        <div class="panel-header">
          <div class="panel-title-wrap">
            <h3>6대 제휴 카페 브랜드별 주문 건수 분포</h3>
            <p>대조군(A) vs 실험군(B)의 브랜드별 주문 점유율 비교</p>
          </div>
        </div>
        <div class="chart-container">
          <canvas id="brandChart"></canvas>
        </div>
      </div>

      <!-- Cross Ordering Mechanics -->
      <div class="dark-card-panel">
        <div class="panel-header">
          <div class="panel-title-wrap">
            <h3>통합 포인트 누적 및 소진 사이클 (실험군 B)</h3>
            <p>다중 브랜드 교차 주문을 유발한 리워드 순환 지표</p>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px;">
          <div style="background: #12141D; padding: 18px; border-radius: 12px; border: 1px solid #262A3B;">
            <div style="font-size: 12px; color: var(--text-gray-muted); font-weight: 600;">90일간 총 적립 포인트</div>
            <div style="font-size: 24px; font-weight: 800; color: #FFFFFF; margin-top: 4px; font-family: 'Outfit';">
              {data_payload['points']['earned_total']:,} <span style="font-size: 14px; color: var(--po-orange);">P</span>
            </div>
            <div style="font-size: 11px; color: #34D399; margin-top: 4px;">결제액의 평균 4% 적립</div>
          </div>
          <div style="background: rgba(255, 92, 30, 0.1); padding: 18px; border-radius: 12px; border: 1px solid rgba(255, 92, 30, 0.35);">
            <div style="font-size: 12px; color: #FFA585; font-weight: 600;">90일간 총 사용 포인트</div>
            <div style="font-size: 24px; font-weight: 800; color: var(--po-orange); margin-top: 4px; font-family: 'Outfit';">
              {data_payload['points']['used_total']:,} <span style="font-size: 14px;">P</span>
            </div>
            <div style="font-size: 11px; color: #FF8554; margin-top: 4px;">전체 주문 중 {data_payload['points']['used_ratio']}%에서 차감 사용</div>
          </div>
        </div>

        <div style="background: #12141D; border-radius: 12px; padding: 20px; border: 1px solid #262A3B;">
          <h4 style="font-size: 14px; font-weight: 800; color: #FFFFFF; margin-bottom: 10px;">프랜차이즈 종속을 깬 핵심 동력</h4>
          <ul style="font-size: 13px; color: var(--text-gray-light); line-height: 1.8; padding-left: 18px;">
            <li><strong>대조군 (Group A)</strong>: 스탬프가 매장별로 파편화되어 타 브랜드 방문 유인이 없어 단골 카페만 반복 이용 (교차 주문율 <strong>17.8%</strong>).</li>
            <li><strong>실험군 (Group B)</strong>: 메가커피에서 쌓은 포인트를 컴포즈나 빽다방에서 결제 시 현금처럼 차감할 수 있어 교차 주문율이 <strong>48.3%</strong>로 2.7배 폭증.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
  // JSON Data Payload
  const DATA = {data_json_str};

  // Tab Switching
  function switchTab(tabId) {{
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
    
    event.currentTarget.classList.add('active');
    document.getElementById(tabId).classList.add('active');
  }}

  // Chart.js Plugin to draw values on top of vertical bars
  const topValuesPlugin = {{
    id: 'topValuesPlugin',
    afterDatasetsDraw(chart) {{
      const {{ ctx }} = chart;
      chart.data.datasets.forEach((dataset, datasetIndex) => {{
        const meta = chart.getDatasetMeta(datasetIndex);
        if (!meta.hidden) {{
          meta.data.forEach((bar, index) => {{
            const val = dataset.data[index];
            if (val !== null && val !== undefined) {{
              ctx.save();
              ctx.fillStyle = '#FFFFFF';
              ctx.font = 'bold 11px Pretendard';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'bottom';
              ctx.fillText(val + '%', bar.x, bar.y - 4);
              ctx.restore();
            }}
          }});
        }}
      }});
    }}
  }};

  // Render Charts
  window.addEventListener('DOMContentLoaded', () => {{
    // Global Chart.js Dark Theme Options
    Chart.defaults.color = '#94A3B8';
    Chart.defaults.font.family = 'Pretendard';

    // 1. Retention Curve Chart
    const ctxRet = document.getElementById('retentionChart').getContext('2d');
    new Chart(ctxRet, {{
      type: 'line',
      data: {{
        labels: DATA.weeks,
        datasets: [
          {{
            label: '실험군 B (교차 통합 적립)',
            data: DATA.retention_b,
            borderColor: '#FF5C1E',
            backgroundColor: 'rgba(255, 92, 30, 0.12)',
            borderWidth: 3,
            fill: true,
            tension: 0.25,
            pointBackgroundColor: '#FF5C1E',
            pointRadius: 4
          }},
          {{
            label: '대조군 A (단일 매장 스탬프)',
            data: DATA.retention_a,
            borderColor: '#64748B',
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderDash: [5, 5],
            tension: 0.25,
            pointBackgroundColor: '#64748B',
            pointRadius: 3
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ font: {{ weight: 'bold', size: 12 }} }} }},
          tooltip: {{ callbacks: {{ label: (item) => `${{item.dataset.label}}: ${{item.raw}}%` }} }}
        }},
        scales: {{
          y: {{
            beginAtZero: true,
            max: 105,
            ticks: {{ callback: (v) => v + '%' }},
            grid: {{ color: '#1E2230' }}
          }},
          x: {{ grid: {{ display: false }} }}
        }}
      }}
    }});

    // 2. Daily DAU Time-Series Area Chart
    const ctxDau = document.getElementById('dauChart').getContext('2d');
    new Chart(ctxDau, {{
      type: 'line',
      data: {{
        labels: DATA.chart_dates,
        datasets: [
          {{
            label: '실험군 B (교차 적립 DAU)',
            data: DATA.dau_ts_b,
            borderColor: '#FF5C1E',
            backgroundColor: 'rgba(255, 92, 30, 0.15)',
            borderWidth: 2,
            fill: true,
            pointRadius: 0,
            tension: 0.2
          }},
          {{
            label: '대조군 A (기존 스탬프 DAU)',
            data: DATA.dau_ts_a,
            borderColor: '#64748B',
            backgroundColor: 'rgba(100, 116, 139, 0.08)',
            borderWidth: 1.5,
            fill: true,
            pointRadius: 0,
            tension: 0.2
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ font: {{ weight: 'bold', size: 12 }} }} }}
        }},
        scales: {{
          y: {{ beginAtZero: true, grid: {{ color: '#1E2230' }} }},
          x: {{ ticks: {{ maxTicksLimit: 12 }}, grid: {{ display: false }} }}
        }}
      }}
    }});

    // 3. 14-Step Funnel Chart
    const ctxFunnel = document.getElementById('funnelChart').getContext('2d');
    new Chart(ctxFunnel, {{
      type: 'bar',
      data: {{
        labels: DATA.funnel_steps,
        datasets: [
          {{
            label: '실험군 B (통합 적립)',
            data: DATA.funnel_b,
            backgroundColor: '#FF5C1E',
            borderRadius: 5
          }},
          {{
            label: '대조군 A (단일 스탬프)',
            data: DATA.funnel_a,
            backgroundColor: '#475569',
            borderRadius: 5
          }}
        ]
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ font: {{ weight: 'bold', size: 12 }} }} }}
        }},
        scales: {{
          x: {{ grid: {{ color: '#1E2230' }} }},
          y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }}
        }}
      }}
    }});

    // 4. KEY CONVERSION STAGES: VERTICAL BAR CHART WITH NUMBERS ON TOP
    const ctxStage = document.getElementById('stageConversionChart').getContext('2d');
    new Chart(ctxStage, {{
      type: 'bar',
      data: {{
        labels: DATA.stage_labels,
        datasets: [
          {{
            label: '실험군 B (통합적립 전환율)',
            data: DATA.stage_rates_b,
            backgroundColor: '#FF5C1E',
            borderRadius: 6
          }},
          {{
            label: '대조군 A (단일스탬프 전환율)',
            data: DATA.stage_rates_a,
            backgroundColor: '#475569',
            borderRadius: 6
          }}
        ]
      }},
      plugins: [topValuesPlugin],
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        layout: {{
          padding: {{ top: 22 }} // 막대 상단 수치 표기를 위한 패딩
        }},
        plugins: {{
          legend: {{ position: 'top', labels: {{ font: {{ weight: 'bold', size: 12 }} }} }},
          tooltip: {{ callbacks: {{ label: (item) => `${{item.dataset.label}}: ${{item.raw}}%` }} }}
        }},
        scales: {{
          y: {{
            beginAtZero: true,
            max: 105,
            ticks: {{ callback: (v) => v + '%' }},
            grid: {{ color: '#1E2230' }}
          }},
          x: {{ grid: {{ display: false }}, ticks: {{ font: {{ weight: '600', size: 12 }} }} }}
        }}
      }}
    }});

    // 5. Brand Distribution Bar Chart
    const ctxBrand = document.getElementById('brandChart').getContext('2d');
    new Chart(ctxBrand, {{
      type: 'bar',
      data: {{
        labels: DATA.brands,
        datasets: [
          {{
            label: '실험군 B 주문 건수',
            data: DATA.brand_orders_b,
            backgroundColor: '#FF5C1E',
            borderRadius: 6
          }},
          {{
            label: '대조군 A 주문 건수',
            data: DATA.brand_orders_a,
            backgroundColor: '#475569',
            borderRadius: 6
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ font: {{ weight: 'bold', size: 12 }} }} }}
        }},
        scales: {{
          y: {{ beginAtZero: true, grid: {{ color: '#1E2230' }} }},
          x: {{ grid: {{ display: false }} }}
        }}
      }}
    }});
  }});
</script>

</body>
</html>
'''

print(f"[3/4] 새 톤앤매너 대시보드 파일 작성 중: {OUTPUT_HTML} & passorder_dashboard.html...")
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_template)

OUTPUT_HTML2 = os.path.join(OUTPUT_DIR, "passorder_dashboard.html")
with open(OUTPUT_HTML2, "w", encoding="utf-8") as f:
    f.write(html_template)

file_size_kb = os.path.getsize(OUTPUT_HTML2) / 1024
print(f"\n[4/4] 완료! 패스오더 공식 톤앤매너 대시보드가 성공적으로 재생성되었습니다.")
print(f"파일 경로: {OUTPUT_HTML2} ({file_size_kb:.1f} KB)")
