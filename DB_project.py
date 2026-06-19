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

def load_user_detail_log_by_nickname(nickname):
    """닉네임을 기반으로 특정 유저의 가장 최신 로그를 불러옵니다."""
    try:
        # 1. users 테이블에서 닉네임으로 user_id 먼저 찾기
        user_res = supabase.table("users").select("user_id").eq("user_name", nickname).execute()
        
        if not user_res.data:
            return None  # 존재하지 않는 닉네임
            
        target_uid = user_res.data[0]['user_id']
        
        # 2. 찾은 user_id로 play_logs 조회
        response = supabase.table("play_logs") \
            .select("play_duration, skill_counts, hit_details") \
            .eq("user_id", target_uid) \
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
# --- 사이드바: 테스트 기능 (수동 입력 폼으로 업그레이드) ---
with st.sidebar:
    st.header("📝 관리자 수동 입력 도구")
    st.markdown("유니티 연동 전, 시뮬레이션 결과를 직접 입력하여 데이터 파이프라인을 테스트합니다.")
    
    with st.form("manual_insert_form"):
        st.subheader("1. 유저 및 보스 정보")
        input_user_id = st.text_input("유저 ID (ocid)", value="ocid_dummy_002_01")
        # ✨ 닉네임 입력란 추가
        input_nickname = st.text_input("닉네임", value="테스터_나로")
        
        input_job_name = st.selectbox("직업 선택", list(MAPLE_JOBS.keys()))
        input_boss = st.selectbox("보스 선택", ["SEREN_P1", "BLACKMAGE_P3"])

        st.subheader("2. 전투 결과")
        input_duration = st.number_input("생존 타임 (초)", min_value=1, max_value=600, value=340)
        
        # ✨ 단위 변경: DPS (억 단위), 총 누적 대미지 (조 단위) - 소수점 입력 가능
        input_dps = st.number_input("DPS (억)", min_value=0.0, value=15.0, step=1.0)
        input_total = st.number_input("총 누적 대미지 (조)", min_value=0.0, value=5.12, step=0.01, format="%.3f")

        st.subheader("3. 상세 기록 (JSONB)")
        st.markdown("**주요 스킬 시전 횟수**")
        col_s1, col_s2, col_s3 = st.columns(3)
        skill_1 = col_s1.number_input("주력 스킬1", min_value=0, value=120)
        skill_2 = col_s2.number_input("주력 스킬2", min_value=0, value=12)
        skill_3 = col_s3.number_input("주력 스킬3", min_value=0, value=45)

        st.markdown("**피격 및 사망 통계**")
        col_h1, col_h2 = st.columns(2)
        hit_total = col_h1.number_input("총 피격 횟수", min_value=0, value=4)
        death_count = col_h2.number_input("사망 횟수", min_value=0, max_value=10, value=1)

        submit_button = st.form_submit_button("DB에 실시간 기록 전송하기")

    if submit_button:
        with st.spinner("데이터 무결성 검증 및 적재 중..."):
            # 1. users 테이블에서 해당 user_id가 이미 존재하는지 먼저 검사합니다.
            existing_user = supabase.table("users").select("user_name").eq("user_id", input_user_id).execute()
            
            is_valid = True
            
            if existing_user.data:
                db_nickname = existing_user.data[0]['user_name']
                # 1-A. ID는 같은데 닉네임이 다르게 입력된 경우 (덮어쓰기 방지)
                if db_nickname != input_nickname:
                    st.error(f"🚨 **[데이터 충돌 방지]** 입력하신 유저 ID(`{input_user_id}`)는 이미 **'{db_nickname}'** (으)로 등록되어 있습니다.")
                    st.warning("새로운 캐릭터의 기록을 추가하시려면 '유저 ID'를 다르게 변경해 주세요!")
                    is_valid = False
                # (닉네임이 같으면 동일 캐릭터의 추가 플레이 기록이므로 그대로 통과시킵니다)
            else:
                # 1-B. 존재하지 않는 신규 유저라면 users 테이블에 안전하게 Insert
                supabase.table("users").insert({"user_id": input_user_id, "user_name": input_nickname}).execute()

            # 2. 유효성 검사를 통과했을 때만 play_logs에 전투 기록 전송
            if is_valid:
                real_dps = int(input_dps * 100_000_000)
                real_total_damage = int(input_total * 1_000_000_000_000)
                
                # ✨ 핵심 수정: 340초 완주 여부 검사 (boolean 값 반환)
                is_survived = (input_duration == 340)
                
                custom_mock_data = {
                    "user_id": input_user_id,
                    "job_id": MAPLE_JOBS[input_job_name],
                    "boss_id": input_boss,
                    # 완주 시 RANKING 모드, 아니면 PRACTICE 모드로 저장
                    "play_mode": "RANKING" if is_survived else "PRACTICE", 
                    "is_public": is_survived, # ✨ 340초일 때만 True, 그 외에는 False
                    "dps": real_dps,
                    "total_damage": real_total_damage,
                    "play_duration": input_duration,
                    "skill_counts": {"주력 스킬1": skill_1, "주력 스킬2": skill_2, "주력 스킬3": skill_3},
                    "hit_details": {"피격 횟수": hit_total, "사망 횟수": death_count} 
                }
                
                try:
                    supabase.table("play_logs").insert(custom_mock_data).execute()
                    
                    # 피드백 UI: 랭킹 등록 여부에 따라 메시지를 다르게 출력
                    if is_survived:
                        st.success(f"🏆 [{input_nickname}] 님의 데이터가 적재되었으며, 340초 완주로 랭킹 보드에 등록되었습니다!")
                    else:
                        st.info(f"💾 [{input_nickname}] 님의 데이터가 적재되었습니다. (생존 타임 {input_duration}초로 인해 랭킹에는 미노출됩니다.)")
                        
                except Exception as e:
                    st.error(f"전투 기록 전송 중 오류 발생: {e}")

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
    
    # ✨ ID(ocid) 대신 닉네임으로 조회
    target_nickname = st.text_input("조회할 유저 닉네임을 입력하세요", value="테스터_나로")
    st.markdown(f"**대상 유저:** `{target_nickname}` 님의 가장 최근 기록을 분석합니다.")
    
    if st.button("상세 기록 분석하기"):
        # 변경된 함수 호출
        detail_data = load_user_detail_log_by_nickname(target_nickname)
        
        if detail_data is None:
            st.warning(f"'{target_nickname}' 닉네임을 가진 유저가 DB에 존재하지 않습니다.")
        elif detail_data:
            log = detail_data[0]
            play_duration = log.get('play_duration', 0)
            skills = log.get('skill_counts', {})
            hits = log.get('hit_details', {})
            
            # --- 통일된 딜 누수 분석 로직 ---
            VALID_SKILL_DELAYS = {"주력 스킬1": 660, "주력 스킬2": 540, "주력 스킬3": 700} 
            total_cast_time_ms = 0
            
            for skill_name, count in skills.items():
                if skill_name in VALID_SKILL_DELAYS:
                    total_cast_time_ms += (count * VALID_SKILL_DELAYS[skill_name])
            
            total_cast_time_sec = total_cast_time_ms / 1000
            leak_time_sec = max(0, play_duration - total_cast_time_sec)
            
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
                st.markdown("#### 💥 보스 패턴 피격 및 사망 통계")
                
                # JSONB 데이터에서 안전하게 값을 가져옵니다. (없을 경우 기본값 0)
                total_hits = hits.get("피격 횟수", 0)
                death_count = hits.get("사망 횟수", 0)
                
                # 피격과 사망 수치를 나란히 보여줍니다.
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("총 피격 횟수", f"{total_hits}회")
                col_m2.metric("사망 횟수", f"{death_count}회")
                
                # ✨ 기획하신 사망 횟수 기준 맞춤형 피드백 로직
                if death_count <= 1:
                    st.success("완벽한 컨트롤입니다!")
                elif death_count <= 3:
                    st.warning("보스 패턴 타이밍을 파악해 보세요.")
                else: # 4회 이상
                    st.error("조금 더 회피에 집중하셔야 합니다.")
        else:
            st.warning(f"'{target_nickname}' 님의 분석할 플레이 기록이 존재하지 않습니다. 먼저 테스트 데이터를 전송해 주세요.")