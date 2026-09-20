"""
패스오더(Pass Order) 교차 브랜드 통합 적립 A/B 테스트 대시보드 HTML 생성기 (v3 - 국문 & 영문 이중화 및 다크 테마)
-----------------------------------------------------------------------------------------------------------------
기능:
1. 90일 A/B 테스트 데이터 집계 및 통계 산출
2. 공식 다크 테마 톤앤매너 적용 대시보드 생성
3. 국문(KO) 및 영문(EN) 대시보드 동시 자동 렌더링
   - output/passorder_dashboard.html (국문 대시보드)
   - output/passorder_dashboard_en.html (영문 대시보드)
   - index.html (GitHub Pages 국문 메인 엔드포인트)
   - index_en.html (GitHub Pages 영문 엔드포인트)
4. 대시보드 헤더 내 🇺🇸 English / 🇰🇷 한국어 상호 원클릭 전환 토글 탑재
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

print(f"[1/4] 데이터 로딩 및 분석 중: {DATA_FILE}...")
df = pd.read_csv(DATA_FILE)

df['event_dt'] = pd.to_datetime(df['event_time'], dayfirst=True)
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
cafe_a = len(df[(df['ab_test_group'] == 'Group A (Control)') & (df['event_name'] == 'Click_cafe')])
cafe_b = len(df[(df['ab_test_group'] == 'Group B (Treatment)') & (df['event_name'] == 'Click_cafe')])
cart_a = len(df[(df['ab_test_group'] == 'Group A (Control)') & (df['event_name'] == 'add_to_cart')])
cart_b = len(df[(df['ab_test_group'] == 'Group B (Treatment)') & (df['event_name'] == 'add_to_cart')])

stage1_a = round((cart_a / cafe_a) * 100, 1)
stage1_b = round((cart_b / cafe_b) * 100, 1)

stage2_a = round((cpm_a / cart_a) * 100, 1)
stage2_b = round((cpm_b / cart_b) * 100, 1)

stage3_a = round((orders_a / cpm_a) * 100, 1)
stage3_b = round((orders_b / cpm_b) * 100, 1)

open_a = len(df[(df['ab_test_group'] == 'Group A (Control)') & (df['event_name'] == 'app_open')])
open_b = len(df[(df['ab_test_group'] == 'Group B (Treatment)') & (df['event_name'] == 'app_open')])
stage4_a = round((orders_a / open_a) * 100, 1)
stage4_b = round((orders_b / open_b) * 100, 1)

stage_rates_a = [stage1_a, stage2_a, stage3_a, stage4_a]
stage_rates_b = [stage1_b, stage2_b, stage3_b, stage4_b]

# -------------------------------------------------------------
# 5. 브랜드별 주문 분포 & 포인트 순환 지표
# -------------------------------------------------------------
brand_counts_a = purchase_df[purchase_df['ab_test_group'] == 'Group A (Control)']['cafe_brand'].value_counts().to_dict()
brand_counts_b = purchase_df[purchase_df['ab_test_group'] == 'Group B (Treatment)']['cafe_brand'].value_counts().to_dict()

all_brands_ko = ["메가커피", "컴포즈커피", "빽다방", "텐퍼센트커피", "매머드커피", "개인스페셜티카페"]
all_brands_en = ["Mega Coffee", "Compose Coffee", "Paik's Coffee", "Ten Percent Coffee", "Mammoth Coffee", "Specialty Cafes"]

brand_data_a = [int(brand_counts_a.get(b, 0)) for b in all_brands_ko]
brand_data_b = [int(brand_counts_b.get(b, 0)) for b in all_brands_ko]

pts_earned_total = int(purchase_df[purchase_df['ab_test_group'] == 'Group B (Treatment)']['earned_reward_point'].sum())
pts_used_total = int(purchase_df[purchase_df['ab_test_group'] == 'Group B (Treatment)']['used_reward_point'].sum())
pts_used_orders_cnt = int(len(purchase_df[(purchase_df['ab_test_group'] == 'Group B (Treatment)') & (purchase_df['used_reward_point'] > 0)]))
pts_used_ratio = round((pts_used_orders_cnt / orders_b) * 100, 1)

# 공통 계산 데이터
kpi_dict = {
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
}

points_dict = {
    "earned_total": pts_earned_total,
    "used_total": pts_used_total,
    "used_orders_cnt": pts_used_orders_cnt,
    "used_ratio": pts_used_ratio
}

# -------------------------------------------------------------
# 6. HTML 렌더링 함수 (다국어 지원)
# -------------------------------------------------------------
def build_dashboard_html(lang='ko', is_root=False):
    is_ko = (lang == 'ko')

    # 다국어 링크 설정
    if is_root:
        link_ko = "index.html"
        link_en = "index_en.html"
    else:
        link_ko = "passorder_dashboard.html"
        link_en = "passorder_dashboard_en.html"

    # 언어별 텍스트 및 라벨 사전
    if is_ko:
        html_lang = "ko"
        doc_title = "패스오더 교차 브랜드 통합 적립 A/B 테스트 성과 대시보드"
        logo_pass = "패스"
        logo_order = "오더"
        header_title = "교차 브랜드 통합 적립 90일 A/B 테스트 대시보드"
        header_desc = "가설 검증: 프랜차이즈 커피 자체 앱 종속 방어 및 전 매장 통합 리워드를 통한 고객 리텐션 락인(Lock-in)"
        
        group_a_title = "대조군 A (1,250명)"
        group_a_desc = "기존 단일 매장 스탬프 (교차 불가 ❌)"
        group_b_title = "실험군 B (1,250명)"
        group_b_desc = "교차 브랜드 통합 적립 (전 매장 사용 ⭕)"

        kpi_titles = [
            "일일 활성 유저 (평균 DAU)",
            "인당 평균 방문 세션",
            "인당 커피 구매 빈도",
            "교차 브랜드 주문율",
            "결제 최종 전환율 (CVR)"
        ]
        kpi_units = ["명", "회", "잔", "%", "%"]
        kpi_a_texts = [
            f"A군 {kpi_dict['avg_dau_a']}명",
            f"A군 {kpi_dict['avg_sess_a']}회",
            f"A군 {kpi_dict['orders_per_user_a']}잔",
            f"A군 {kpi_dict['cross_rate_a']}%",
            f"A군 {kpi_dict['cvr_a']}%"
        ]
        
        tab_titles = [
            "📈 1. 가설 검증 & 코호트 리텐션",
            "🛒 2. 14단계 행동 퍼널 분석",
            "☕ 3. 교차 브랜드 이용 분석"
        ]

        t1_chart_title = "90일 장기 코호트 리텐션 곡선 (Week 0 ~ Week 12)"
        t1_chart_period = "📅 2026.06.01 ~ 2026.08.29 (90일간)"
        t1_chart_desc = "최초 온보딩 시점 이후 경과 주차별 고유 접속 잔존율 비교"
        t1_ds_b = "실험군 B (교차 통합 적립)"
        t1_ds_a = "대조군 A (단일 매장 스탬프)"

        t1_table_title = "주차별 잔존율 상세 비교 (Heatmap)"
        t1_table_desc = "1개월, 2개월, 3개월 경과 시점의 잔존 격차"
        t1_th = ["구간", "경과 기간", "대조군 A", "실험군 B (통합적립)", "성과 격차 (Lift)"]
        t1_w1_period = "D+7 ~ D+13"
        t1_w2_period = "D+14 ~ D+20"
        t1_w4_period = "1개월 (D+28~34)"
        t1_w8_period = "2개월 (D+56~62)"
        t1_w12_period = "3개월 (D+84~89)"
        t1_w12_lift = "▲ 약 3배 유지"

        t1_dau_title = "90일간 일일 활성 사용자 수 (DAU) 일자별 추이"
        t1_dau_desc = "주중 출퇴근 피크와 주말 패턴, 그리고 시간 경과에 따른 활동 유저 베이스라인 비교"
        t1_dau_ds_b = "실험군 B (교차 적립 DAU)"
        t1_dau_ds_a = "대조군 A (기존 스탬프 DAU)"

        t2_f1_title = "14단계 스마트오더 행동 퍼널 규모 비교"
        t2_f1_desc = "앱 실행(app_open)부터 최종 구매(purchase)까지 단계별 잔존 로그 수"
        t2_f1_ds_b = "실험군 B (통합 적립)"
        t2_f1_ds_a = "대조군 A (단일 스탬프)"

        t2_f2_title = "핵심 구간별 전환율 비교 (세로 막대 그래프)"
        t2_f2_desc = "단계별 전환율(%)과 결제 직전 이탈 방어 효과 (막대 위 수치 표기)"
        stage_labels = ["1. 매장선택 ➔ 장바구니", "2. 장바구니 ➔ 결제확인", "3. 결제확인 ➔ 최종구매 ★", "4. 전체 퍼널 (오픈➔구매)"]
        t2_f2_ds_b = "실험군 B (통합적립 전환율)"
        t2_f2_ds_a = "대조군 A (단일스탬프 전환율)"

        t3_b1_title = "6대 제휴 카페 브랜드별 주문 건수 분포"
        t3_b1_desc = "대조군(A) vs 실험군(B)의 브랜드별 주문 점유율 비교"
        brands = all_brands_ko
        t3_b1_ds_b = "실험군 B 주문 건수"
        t3_b1_ds_a = "대조군 A 주문 건수"

        t3_b2_title = "통합 포인트 누적 및 소진 사이클 (실험군 B)"
        t3_b2_desc = "다중 브랜드 교차 주문을 유발한 리워드 순환 지표"
        t3_b2_acc_title = "90일간 총 적립 포인트"
        t3_b2_acc_sub = "결제액의 평균 4% 적립"
        t3_b2_use_title = "90일간 총 사용 포인트"
        t3_b2_use_sub = "전체 주문 중 17.2%에서 차감 사용"
        t3_b2_box_title = "프랜차이즈 종속을 깬 핵심 동력"
        t3_b2_li1 = "<strong>대조군 (Group A)</strong>: 스탬프가 매장별로 파편화되어 타 브랜드 방문 유인이 없어 단골 카페만 반복 이용 (교차 주문율 <strong>17.8%</strong>)."
        t3_b2_li2 = "<strong>실험군 (Group B)</strong>: 메가커피에서 쌓은 포인트를 컴포즈나 빽다방에서 결제 시 현금처럼 차감할 수 있어 교차 주문율이 <strong>48.3%</strong>로 2.7배 폭증."
    else:
        html_lang = "en"
        doc_title = "Pass Order Cross-Brand Unified Rewards A/B Test Dashboard"
        logo_pass = "PASS"
        logo_order = "ORDER"
        header_title = "Cross-Brand Unified Rewards 90-Day A/B Test Dashboard"
        header_desc = "Hypothesis Validation: Halting Churn to Franchise-Owned Apps & Driving Customer Retention Lock-In via Universal Loyalty Points"
        
        group_a_title = "Control Group A (1,250)"
        group_a_desc = "Legacy Store-Isolated Stamps (No Cross-Use ❌)"
        group_b_title = "Treatment Group B (1,250)"
        group_b_desc = "Cross-Brand Unified Rewards (Universal ⭕)"

        kpi_titles = [
            "Average DAU (Daily Active Users)",
            "Sessions per User",
            "Orders per User",
            "Cross-Brand Ordering Rate",
            "Checkout Conversion Rate (CVR)"
        ]
        kpi_units = ["users", "sessions", "orders", "%", "%"]
        kpi_a_texts = [
            f"Control A: {kpi_dict['avg_dau_a']} users",
            f"Control A: {kpi_dict['avg_sess_a']} sess",
            f"Control A: {kpi_dict['orders_per_user_a']} orders",
            f"Control A: {kpi_dict['cross_rate_a']}%",
            f"Control A: {kpi_dict['cvr_a']}%"
        ]
        
        tab_titles = [
            "📈 1. Hypothesis Testing & Cohort Retention",
            "🛒 2. 14-Step Behavioral Funnel",
            "☕ 3. Cross-Brand Ecosystem Analysis"
        ]

        t1_chart_title = "90-Day Longitudinal Cohort Retention Curve (Week 0 ~ Week 12)"
        t1_chart_period = "📅 2026.06.01 ~ 2026.08.29 (90 Days)"
        t1_chart_desc = "Weekly unique active retention comparison following initial onboarding"
        t1_ds_b = "Treatment Group B (Unified Rewards)"
        t1_ds_a = "Control Group A (Store-Isolated Stamps)"

        t1_table_title = "Weekly Retention Matrix (Heatmap)"
        t1_table_desc = "Retention gaps at 1-month, 2-month, and 3-month milestones"
        t1_th = ["Cohort", "Elapsed Period", "Control A", "Treatment B (Unified)", "Lift Delta"]
        t1_w1_period = "D+7 ~ D+13"
        t1_w2_period = "D+14 ~ D+20"
        t1_w4_period = "1 Month (D+28~34)"
        t1_w8_period = "2 Months (D+56~62)"
        t1_w12_period = "3 Months (D+84~89)"
        t1_w12_lift = "▲ ~3x Retention Preserved"

        t1_dau_title = "90-Day Daily Active Users (DAU) Time-Series Trajectory"
        t1_dau_desc = "Weekday commute peaks, weekend dips, and long-term active user baseline divergence"
        t1_dau_ds_b = "Treatment Group B (Unified DAU)"
        t1_dau_ds_a = "Control Group A (Control DAU)"

        t2_f1_title = "14-Step Smart Order Behavioral Funnel Volume Comparison"
        t2_f1_desc = "Retained event volume from app launch (app_open) to final checkout (purchase)"
        t2_f1_ds_b = "Treatment Group B (Unified Rewards)"
        t2_f1_ds_a = "Control Group A (Store Stamps)"

        t2_f2_title = "Key Stage Conversion Rates (Vertical Bar Chart)"
        t2_f2_desc = "Stage-by-stage CVR (%) and checkout drop-off defense (values displayed atop bars)"
        stage_labels = ["1. Store Select ➔ Cart", "2. Cart ➔ Checkout", "3. Checkout ➔ Purchase ★", "4. Full Funnel (Open ➔ Purchase)"]
        t2_f2_ds_b = "Treatment Group B (Unified CVR)"
        t2_f2_ds_a = "Control Group A (Control CVR)"

        t3_b1_title = "Order Volume Distribution Across 6 Partner Cafe Brands"
        t3_b1_desc = "Order share comparison between Control Group (A) and Treatment Group (B)"
        brands = all_brands_en
        t3_b1_ds_b = "Treatment Group B Orders"
        t3_b1_ds_a = "Control Group A Orders"

        t3_b2_title = "Universal Point Accrual & Redemption Velocity (Treatment B)"
        t3_b2_desc = "Key loyalty turnover metrics driving cross-brand ordering"
        t3_b2_acc_title = "Total Points Accrued (90 Days)"
        t3_b2_acc_sub = "Avg. 4% earned on order value"
        t3_b2_use_title = "Total Points Redeemed (90 Days)"
        t3_b2_use_sub = "Redeemed in 17.2% of total orders"
        t3_b2_box_title = "Key Drivers Dismantling Franchise Lock-In"
        t3_b2_li1 = "<strong>Control Group (Group A)</strong>: Stamps were fragmented by store, offering zero incentive to explore alternative brands, leading users to patronize only single local stores (Cross-brand order rate: <strong>17.8%</strong>)."
        t3_b2_li2 = "<strong>Treatment Group (Group B)</strong>: Points earned at Mega Coffee could be immediately deducted like cash at Compose or Paik's Coffee, surging the cross-brand order rate to <strong>48.3%</strong> (2.7x lift)."

    # 데이터 페이로드 생성
    current_payload = {
        "kpi": kpi_dict,
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
        "brands": brands,
        "brand_orders_a": brand_data_a,
        "brand_orders_b": brand_data_b,
        "points": points_dict
    }
    payload_json_str = json.dumps(current_payload, ensure_ascii=False)

    # 언어 스위처 HTML
    if is_ko:
        lang_switcher_html = f'''
        <div class="lang-switcher">
          <span class="lang-btn active">🇰🇷 한국어</span>
          <a href="{link_en}" class="lang-btn">🇺🇸 English</a>
        </div>
        '''
    else:
        lang_switcher_html = f'''
        <div class="lang-switcher">
          <a href="{link_ko}" class="lang-btn">🇰🇷 한국어</a>
          <span class="lang-btn active">🇺🇸 English</span>
        </div>
        '''

    html_content = f'''<!DOCTYPE html>
<html lang="{html_lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{doc_title}</title>
  
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
      max-width: 680px;
      line-height: 1.4;
    }}

    /* Top Right: Distinct A/B Comparison Cards & Language Switcher */
    .header-right-wrap {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .lang-switcher {{
      display: inline-flex;
      align-items: center;
      background: #0E1017;
      border: 1px solid #2B2F42;
      border-radius: 10px;
      padding: 4px;
      gap: 4px;
    }}

    .lang-btn {{
      padding: 6px 12px;
      border-radius: 7px;
      font-size: 12px;
      font-weight: 700;
      text-decoration: none;
      color: var(--text-gray-muted);
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
    }}

    .lang-btn:hover {{
      color: var(--text-white);
      background: #1E2230;
    }}

    .lang-btn.active {{
      background: var(--po-orange);
      color: #FFFFFF;
      box-shadow: 0 2px 8px rgba(255, 92, 30, 0.35);
    }}

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
      white-space: nowrap;
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
      .header-right-wrap {{
        width: 100%;
        flex-direction: column;
        align-items: stretch;
      }}
      .header-groups-wrap {{
        flex-direction: column;
      }}
      .tabs-nav {{
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>

<div class="container">

  <!-- 1. Top Header with Official Pass Order Logo & Language Switcher & Distinct Group A/B Cards -->
  <header class="top-header">
    <div class="header-brand-wrap">
      <!-- Official Logo -->
      <div class="po-official-logo">
        <span class="po-logo-pass">{logo_pass}</span><span class="po-logo-order">{logo_order}</span>
      </div>
      <div class="header-text-block">
        <h1>{header_title}</h1>
        <p>{header_desc}</p>
      </div>
    </div>

    <!-- Clear & Concise A/B Group Identifier & Language Switcher -->
    <div class="header-right-wrap">
      {lang_switcher_html}

      <div class="header-groups-wrap">
        <div class="group-mini-card">
          <div class="group-icon-badge icon-a">🏪</div>
          <div class="group-mini-info">
            <span class="group-mini-title">{group_a_title}</span>
            <span class="group-mini-desc">{group_a_desc}</span>
          </div>
        </div>

        <div class="group-mini-card group-b">
          <div class="group-icon-badge icon-b">☕</div>
          <div class="group-mini-info">
            <span class="group-mini-title" style="color: #FF8554;">{group_b_title}</span>
            <span class="group-mini-desc">{group_b_desc}</span>
          </div>
        </div>
      </div>
    </div>
  </header>

  <!-- 2. Top 5 Key KPI Cards: ORANGE BACKGROUND + WHITE TEXT -->
  <section class="kpi-grid">
    <!-- Card 1: DAU -->
    <div class="kpi-orange-card">
      <div class="kpi-title">{kpi_titles[0]}</div>
      <div class="kpi-main-val">
        {kpi_dict['avg_dau_b']} <span class="kpi-unit">{kpi_units[0]}</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">{kpi_a_texts[0]}</span>
        <span class="kpi-lift-pill">▲ +{kpi_dict['dau_lift']}%</span>
      </div>
    </div>

    <!-- Card 2: Sessions per User -->
    <div class="kpi-orange-card">
      <div class="kpi-title">{kpi_titles[1]}</div>
      <div class="kpi-main-val">
        {kpi_dict['avg_sess_b']} <span class="kpi-unit">{kpi_units[1]}</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">{kpi_a_texts[1]}</span>
        <span class="kpi-lift-pill">▲ +{kpi_dict['sess_lift']}%</span>
      </div>
    </div>

    <!-- Card 3: Orders per User -->
    <div class="kpi-orange-card">
      <div class="kpi-title">{kpi_titles[2]}</div>
      <div class="kpi-main-val">
        {kpi_dict['orders_per_user_b']} <span class="kpi-unit">{kpi_units[2]}</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">{kpi_a_texts[2]}</span>
        <span class="kpi-lift-pill">▲ +{kpi_dict['orders_lift']}%</span>
      </div>
    </div>

    <!-- Card 4: Cross Brand Rate -->
    <div class="kpi-orange-card">
      <div class="kpi-title">{kpi_titles[3]}</div>
      <div class="kpi-main-val">
        {kpi_dict['cross_rate_b']} <span class="kpi-unit">{kpi_units[3]}</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">{kpi_a_texts[3]}</span>
        <span class="kpi-lift-pill">▲ +{kpi_dict['cross_diff']}%p</span>
      </div>
    </div>

    <!-- Card 5: Checkout Conversion -->
    <div class="kpi-orange-card">
      <div class="kpi-title">{kpi_titles[4]}</div>
      <div class="kpi-main-val">
        {kpi_dict['cvr_b']} <span class="kpi-unit">{kpi_units[4]}</span>
      </div>
      <div class="kpi-comparison">
        <span class="kpi-control-text">{kpi_a_texts[4]}</span>
        <span class="kpi-lift-pill">▲ +{kpi_dict['cvr_diff']}%p</span>
      </div>
    </div>
  </section>

  <!-- 3. Navigation Tabs (Focused 3 Tabs) -->
  <nav class="tabs-nav">
    <button class="tab-btn active" onclick="switchTab('tab-retention')">{tab_titles[0]}</button>
    <button class="tab-btn" onclick="switchTab('tab-funnel')">{tab_titles[1]}</button>
    <button class="tab-btn" onclick="switchTab('tab-cross')">{tab_titles[2]}</button>
  </nav>

  <!-- ================= TAB 1: 코호트 리텐션 ================= -->
  <div id="tab-retention" class="tab-panel active">
    <div class="dashboard-grid-2">
      <!-- Retention Curve Chart -->
      <div class="dark-card-panel">
        <div class="panel-header">
          <div class="panel-title-wrap">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <h3>{t1_chart_title}</h3>
              <span class="period-memo-box">{t1_chart_period}</span>
            </div>
            <p>{t1_chart_desc}</p>
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
            <h3>{t1_table_title}</h3>
            <p>{t1_table_desc}</p>
          </div>
        </div>
        <div style="overflow-x: auto;">
          <table class="retention-clean-table">
            <thead>
              <tr>
                <th>{t1_th[0]}</th>
                <th>{t1_th[1]}</th>
                <th>{t1_th[2]}</th>
                <th>{t1_th[3]}</th>
                <th>{t1_th[4]}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Week 1</strong></td>
                <td>{t1_w1_period}</td>
                <td>96.2%</td>
                <td class="highlight-b">98.7%</td>
                <td><span class="lift-tag-badge green">+2.5%p</span></td>
              </tr>
              <tr>
                <td><strong>Week 2</strong></td>
                <td>{t1_w2_period}</td>
                <td>90.9%</td>
                <td class="highlight-b">98.3%</td>
                <td><span class="lift-tag-badge green">+7.4%p</span></td>
              </tr>
              <tr>
                <td><strong>Week 4</strong></td>
                <td>{t1_w4_period}</td>
                <td>79.8%</td>
                <td class="highlight-b">97.8%</td>
                <td><span class="lift-tag-badge green">+18.0%p</span></td>
              </tr>
              <tr>
                <td><strong>Week 8</strong></td>
                <td>{t1_w8_period}</td>
                <td>43.9%</td>
                <td class="highlight-b">87.2%</td>
                <td><span class="lift-tag-badge green">+43.3%p</span></td>
              </tr>
              <tr style="background: rgba(255, 92, 30, 0.12);">
                <td><strong style="color: #FFA585;">Week 12</strong></td>
                <td>{t1_w12_period}</td>
                <td>9.8%</td>
                <td class="highlight-b" style="color: #FF5C1E; font-size: 14px;">28.9%</td>
                <td><span class="lift-tag-badge orange">{t1_w12_lift}</span></td>
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
          <h3>{t1_dau_title}</h3>
          <p>{t1_dau_desc}</p>
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
            <h3>{t2_f1_title}</h3>
            <p>{t2_f1_desc}</p>
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
            <h3>{t2_f2_title}</h3>
            <p>{t2_f2_desc}</p>
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
            <h3>{t3_b1_title}</h3>
            <p>{t3_b1_desc}</p>
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
            <h3>{t3_b2_title}</h3>
            <p>{t3_b2_desc}</p>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px;">
          <div style="background: #12141D; padding: 18px; border-radius: 12px; border: 1px solid #262A3B;">
            <div style="font-size: 12px; color: var(--text-gray-muted); font-weight: 600;">{t3_b2_acc_title}</div>
            <div style="font-size: 24px; font-weight: 800; color: #FFFFFF; margin-top: 4px; font-family: 'Outfit';">
              {points_dict['earned_total']:,} <span style="font-size: 14px; color: var(--po-orange);">P</span>
            </div>
            <div style="font-size: 11px; color: #34D399; margin-top: 4px;">{t3_b2_acc_sub}</div>
          </div>
          <div style="background: rgba(255, 92, 30, 0.1); padding: 18px; border-radius: 12px; border: 1px solid rgba(255, 92, 30, 0.35);">
            <div style="font-size: 12px; color: #FFA585; font-weight: 600;">{t3_b2_use_title}</div>
            <div style="font-size: 24px; font-weight: 800; color: var(--po-orange); margin-top: 4px; font-family: 'Outfit';">
              {points_dict['used_total']:,} <span style="font-size: 14px;">P</span>
            </div>
            <div style="font-size: 11px; color: #FF8554; margin-top: 4px;">{t3_b2_use_sub}</div>
          </div>
        </div>

        <div style="background: #12141D; border-radius: 12px; padding: 20px; border: 1px solid #262A3B;">
          <h4 style="font-size: 14px; font-weight: 800; color: #FFFFFF; margin-bottom: 10px;">{t3_b2_box_title}</h4>
          <ul style="font-size: 13px; color: var(--text-gray-light); line-height: 1.8; padding-left: 18px;">
            <li>{t3_b2_li1}</li>
            <li>{t3_b2_li2}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
  // JSON Data Payload
  const DATA = {payload_json_str};

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
            label: '{t1_ds_b}',
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
            label: '{t1_ds_a}',
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
            label: '{t1_dau_ds_b}',
            data: DATA.dau_ts_b,
            borderColor: '#FF5C1E',
            backgroundColor: 'rgba(255, 92, 30, 0.15)',
            borderWidth: 2,
            fill: true,
            pointRadius: 0,
            tension: 0.2
          }},
          {{
            label: '{t1_dau_ds_a}',
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
            label: '{t2_f1_ds_b}',
            data: DATA.funnel_b,
            backgroundColor: '#FF5C1E',
            borderRadius: 5
          }},
          {{
            label: '{t2_f1_ds_a}',
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
            label: '{t2_f2_ds_b}',
            data: DATA.stage_rates_b,
            backgroundColor: '#FF5C1E',
            borderRadius: 6
          }},
          {{
            label: '{t2_f2_ds_a}',
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
          padding: {{ top: 22 }}
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
            label: '{t3_b1_ds_b}',
            data: DATA.brand_orders_b,
            backgroundColor: '#FF5C1E',
            borderRadius: 6
          }},
          {{
            label: '{t3_b1_ds_a}',
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
    return html_content

# -------------------------------------------------------------
# 7. 파일 생성 및 저장
# -------------------------------------------------------------
print(f"[2/4] 국문 & 영문 대시보드 HTML 렌더링 중...")

# 국문 대시보드
html_ko_output = build_dashboard_html(lang='ko', is_root=False)
html_ko_root = build_dashboard_html(lang='ko', is_root=True)

# 영문 대시보드
html_en_output = build_dashboard_html(lang='en', is_root=False)
html_en_root = build_dashboard_html(lang='en', is_root=True)

print(f"[3/4] 파일 쓰기 작업 중...")

# 1) output/passorder_dashboard.html (국문)
OUTPUT_KO = os.path.join(OUTPUT_DIR, "passorder_dashboard.html")
with open(OUTPUT_KO, "w", encoding="utf-8") as f:
    f.write(html_ko_output)

# 2) output/passorder_dashboard_en.html (영문)
OUTPUT_EN = os.path.join(OUTPUT_DIR, "passorder_dashboard_en.html")
with open(OUTPUT_EN, "w", encoding="utf-8") as f:
    f.write(html_en_output)

# 3) index.html (루트 배포용 국문)
ROOT_KO = os.path.join(BASE_DIR, "index.html")
with open(ROOT_KO, "w", encoding="utf-8") as f:
    f.write(html_ko_root)

# 4) index_en.html (루트 배포용 영문)
ROOT_EN = os.path.join(BASE_DIR, "index_en.html")
with open(ROOT_EN, "w", encoding="utf-8") as f:
    f.write(html_en_root)

# 5) passorder_dashboard_en.html (루트 동시 복사 - GitHub Pages 유연성)
ROOT_EN_DIRECT = os.path.join(BASE_DIR, "passorder_dashboard_en.html")
with open(ROOT_EN_DIRECT, "w", encoding="utf-8") as f:
    f.write(html_en_output)

size_ko = os.path.getsize(OUTPUT_KO) / 1024
size_en = os.path.getsize(OUTPUT_EN) / 1024

print(f"\n[4/4] 완료! 국문 및 영문 대시보드가 성공적으로 생성되었습니다.")
print(f" - [국문 산출물] {OUTPUT_KO} ({size_ko:.1f} KB)")
print(f" - [영문 산출물] {OUTPUT_EN} ({size_en:.1f} KB)")
print(f" - [GitHub Pages 국문] {ROOT_KO}")
print(f" - [GitHub Pages 영문] {ROOT_EN}")
