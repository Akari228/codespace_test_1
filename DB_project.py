# DB_project.py
import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ==========================================
# 1. Supabase DB 연결 설정
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# ==========================================
# 2. 데이터 호출 및 조작 함수
# ==========================================
def load_job_list():
    """job_master 테이블에서 직업 목록을 동적으로 불러옵니다."""
    try:
        response = supabase.table("job_master").select("job_name").execute()
        jobs = [item["job_name"] for item in response.data]
        return ["전체 직업"] + jobs
    except Exception as e:
        st.error(f"직업 목록을 불러오는 중 오류가 발생했습니다: {e}")
        return ["전체 직업"]

def load_ranking_data(target_boss_id, target_job_name):
    """조건에 맞는 랭킹 데이터를 가져옵니다."""
    try:
        query = supabase.table("rankings").select("user_name, job_name, dps, total_damage, play_duration").eq("boss_id", target_boss_id)
        
        # 전체 직업이 아닐 경우 직업 필터 추가
        if target_job_name != "전체 직업":
            query = query.eq("job_name", target_job_name)
            
        response = query.order("dps", desc=True).limit(10).execute()
        return response.data
    except Exception as e:
        st.error(f"랭킹 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return []

def load_user_detail_log(user_id):
    """특정 유저의 가장 최신 로그를 불러옵니다."""
    try:
        response = supabase.table("play_logs") \
            .select("play_duration, skill_counts, hit_details") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        return response.data
    except Exception as e:
        st.error(f"유저 로그를 불러오는 중 오류가 발생했습니다: {e}")
        return []

def save_mock_data_and_refresh():
    """임시 데이터를 생성하고 Materialized View를 최신화합니다."""
    mock_data = {
        "user_id": "ocid_dummy_001_01",
        "job_id": 22, # 예시: 아델
        "boss_id": "SEREN_P1",
        "play_mode": "RANKING",
        "is_public": True,
        "dps": 125000000,
        "total_damage": 37500000000,
        "play_duration": 340,
        "skill_counts": {"디바이드": 180, "인피니트": 15, "오더": 50},
        "hit_details": {"운석": 2, "장판": 0, "돌진": 1}
    }
    
    try:
        # 1. Mock Data Insert
        supabase.table("play_logs").insert(mock_data).execute()
        # 2. Materialized View 최신화 (RPC 호출)
        supabase.rpc('refresh_rankings_view').execute()
        return True
    except Exception as e:
        st.error(f"데이터 삽입 및 최신화 중 오류가 발생했습니다: {e}")
        return False
    


# --- 사이드바 시작 전에 전 직업 딕셔너리를 정의합니다 ---
# (DB job_master 테이블의 가나다순 ID 체계 완벽 반영)
MAPLE_JOBS = {
    "나이트로드": 1, "나이트워커": 2, "다크나이트": 3, "데몬슬레이어": 4, "데몬어벤져": 5,
    "듀얼블레이더": 6, "라라": 7, "렌": 8, "루미너스": 9, "메르세데스": 10,
    "메카닉": 11, "미하일": 12, "바이퍼": 13, "배틀메이지": 14, "보우마스터": 15,
    "블래스터": 16, "비숍": 17, "섀도어": 18, "소울마스터": 19, "스트라이커": 20,
    "신궁": 21, "아델": 22, "아란": 23, "아크": 24, "아크메이지(불,독)": 25,
    "아크메이지(썬,콜)": 26, "엔젤릭버스터": 27, "에반": 28, "와일드헌터": 29, "윈드브레이커": 30,
    "은월": 31, "일리움": 32, "제논": 33, "제로": 34, "카데나": 35,
    "카이저": 36, "카인": 37, "칼리": 38, "캐논마스터": 39, "캡틴": 40,
    "키네시스": 41, "패스파인더": 42, "팔라딘": 43, "팬텀": 44, "플레임위자드": 45,
    "호영": 46, "히어로": 47
}
# ==========================================
# 3. Streamlit 화면 UI 구성
# ==========================================
st.set_page_config(page_title="메이플스토리 시뮬레이터", page_icon="🍁", layout="wide")

# --- 사이드바: 테스트 기능 (수동 입력 폼으로 업그레이드) ---
with st.sidebar:
    st.header("📝 관리자 수동 입력 도구")
    st.markdown("유니티 연동 전, 시뮬레이션 결과를 직접 입력하여 데이터 파이프라인을 테스트합니다.")
    
    with st.form("manual_insert_form"):
        st.subheader("1. 유저 및 보스 정보")
        input_user_id = st.text_input("유저 ID", value="ocid_dummy_002_01")
        
        # 47개 전 직업 리스트 적용
        input_job_name = st.selectbox("직업 선택", list(MAPLE_JOBS.keys()))
        input_boss = st.selectbox("보스 선택", ["SEREN_P1", "BLACKMAGE_P3"])

        st.subheader("2. 전투 결과")
        input_duration = st.number_input("생존 타임 (초)", min_value=1, max_value=600, value=340)
        input_dps = st.number_input("DPS", min_value=0, value=150000000, step=10000000)
        input_total = st.number_input("총 누적 대미지", min_value=0, value=51000000000, step=1000000000)

        st.subheader("3. 상세 기록 (JSONB)")
        st.markdown("**주요 스킬 시전 횟수**")
        col_s1, col_s2, col_s3 = st.columns(3)
        skill_1 = col_s1.number_input("주력 스킬1", min_value=0, value=120)
        skill_2 = col_s2.number_input("주력 스킬2", min_value=0, value=12)
        skill_3 = col_s3.number_input("주력 스킬3", min_value=0, value=45)

        st.markdown("**보스 패턴 피격 횟수**")
        hit_total = st.number_input("총 피격 횟수", min_value=0, value=4)

        submit_button = st.form_submit_button("DB에 실시간 기록 전송하기")

    if submit_button:
        custom_mock_data = {
            "user_id": input_user_id,
            "job_id": MAPLE_JOBS[input_job_name], # 선택한 직업 ID 매핑
            "boss_id": input_boss,
            "play_mode": "RANKING",
            "is_public": True,
            "dps": input_dps,
            "total_damage": input_total,
            "play_duration": input_duration,
            # 규격 통일: 주력 스킬 및 단일 피격 횟수
            "skill_counts": {"주력 스킬1": skill_1, "주력 스킬2": skill_2, "주력 스킬3": skill_3},
            "hit_details": {"피격 횟수": hit_total}
        }
        
        with st.spinner("데이터 적재 및 뷰 갱신 중..."):
            try:
                supabase.table("play_logs").insert(custom_mock_data).execute()
                supabase.rpc('refresh_rankings_view').execute()
                st.success(f"{input_user_id}의 테스트 데이터가 적재되었습니다!")
            except Exception as e:
                st.error(f"데이터 삽입 중 오류 발생: {e}")

st.title("🏆 메이플스토리 보스 시뮬레이션")

# --- 메인 탭 구성 ---
tab1, tab2 = st.tabs(["전체 랭킹 보드", "내 기록 상세 분석 (예시)"])

with tab1:
    st.subheader("보스 및 직업별 딜 효율 랭킹")
    
    # 동적 필터링 UI
    col_boss, col_job = st.columns(2)
    with col_boss:
        selected_boss = st.selectbox("보스를 선택하세요", ["SEREN_P1", "BLACKMAGE_P3"], key="boss_select")
    with col_job:
        job_list = load_job_list()
        selected_job = st.selectbox("직업을 선택하세요", job_list, key="job_select")

    if st.button("랭킹 조회하기"):
        data = load_ranking_data(selected_boss, selected_job)
        
        if data:
            st.success("데이터를 0.1초 만에 불러왔습니다! (Materialized View 캐싱 적용)")
            df = pd.DataFrame(data)
            df.index = df.index + 1 
            df.columns = ["닉네임", "직업", "DPS", "총 누적 대미지", "플레이 타임(초)"]
            
            # 숫자 포맷팅 (가독성 향상)
            df['DPS'] = df['DPS'].apply(lambda x: f"{x:,}")
            df['총 누적 대미지'] = df['총 누적 대미지'].apply(lambda x: f"{x:,}")
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("조건에 맞는 랭킹 데이터가 존재하지 않습니다.")

with tab2:
    st.subheader("마이페이지 정밀 분석 (딜 누수 리포트)")
    
    # 변경 사항: 고정 ID 대신 동적 ID 검색창 배치
    target_user = st.text_input("조회할 유저 ID(ocid)를 입력하세요", value="ocid_dummy_001_01")
    st.markdown(f"**대상 유저:** `{target_user}`의 가장 최근 기록을 분석합니다.")
    
    if st.button("상세 기록 분석하기"):
        detail_data = load_user_detail_log(target_user)
        
        if detail_data:
            log = detail_data[0]
            play_duration = log.get('play_duration', 0)
            skills = log.get('skill_counts', {})
            hits = log.get('hit_details', {})
            
            # --- 통일된 딜 누수 분석 로직 ---
            # 주력 스킬 1, 2, 3의 기본 프레임 딜레이 지정 (임의의 ms 단위)
            VALID_SKILL_DELAYS = {"주력 스킬1": 660, "주력 스킬2": 540, "주력 스킬3": 700} 
            total_cast_time_ms = 0
            
            for skill_name, count in skills.items():
                if skill_name in VALID_SKILL_DELAYS:
                    total_cast_time_ms += (count * VALID_SKILL_DELAYS[skill_name])
            
            total_cast_time_sec = total_cast_time_ms / 1000
            leak_time_sec = max(0, play_duration - total_cast_time_sec)
            
            # 누수 시간을 주력 스킬1(660ms) 기준으로 환산
            missed_actions = int((leak_time_sec * 1000) / 660) if leak_time_sec > 0 else 0
            
            # --- 결과 시각화 ---
            col_metric1, col_metric2, col_metric3 = st.columns(3)
            col_metric1.metric("총 생존 시간", f"{play_duration}초")
            col_metric2.metric("유효 스킬 시전 시간", f"{total_cast_time_sec:.1f}초")
            col_metric3.metric("딜 누수 시간 (대기 상태)", f"{leak_time_sec:.1f}초", delta=f"- 주력 스킬1 {missed_actions}회 손실", delta_color="inverse")
            
            st.divider()
            
            col_detail1, col_detail2 = st.columns(2)
            with col_detail1:
                st.markdown("#### ⚔️ 주요 스킬 사용 내역")
                
                skill_df = pd.DataFrame(list(skills.items()), columns=["스킬명", "사용 횟수"])
                st.dataframe(skill_df, hide_index=True, use_container_width=True)
                    
            with col_detail2:
                st.markdown("#### 💥 보스 패턴 피격 통계")
                # 통합된 피격 통계 수치 출력
                total_hits = hits.get("피격 횟수", 0)
                
                if total_hits > 0:
                    st.metric("총 피격 횟수", f"{total_hits}회")
                    st.warning("생존 관리가 필요합니다.")
                else:
                    st.metric("총 피격 횟수", "0회")
                    st.success("완벽한 컨트롤입니다!")
        else:
            st.warning(f"'{target_user}' 유저의 분석할 기록이 존재하지 않습니다. 먼저 왼쪽 사이드바에서 해당 ID로 테스트 데이터를 전송해 주세요.")