import streamlit as st
import pandas as pd
import random
import io
import uuid

# [설정] 앱 페이지 설정
st.set_page_config(page_title="청취담 연합파티 매칭", page_icon="🍻", layout="wide")

# [세션 상태 관리] 로그인 및 데이터 초기화
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = str(uuid.uuid4())

def reset_matching_state():
    """파일이 새로 올라오면 기존 매칭 결과 초기화"""
    keys_to_clear = ['selected_df', 'waitlist_df', 'all_rounds_data', 'final_score', 'stage2_done']
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

# [보안] 관리자 로그인 체크
if not st.session_state["authenticated"]:
    st.title("🔒 관리자 로그인")
    pwd = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pwd == "1234":  # 설정하신 비밀번호
            st.session_state["authenticated"] = True
            st.rerun() 
        else:
            st.error("⚠️ 비밀번호가 틀렸습니다.")
    st.stop()

# --- 2. 매칭 알고리즘 (Swap 최적화 포함) ---
def generate_full_schedule(people_list, num_tables, total_rounds=3, max_attempts=100):
    """
    선발된 인원을 바탕으로 중복을 최소화하여 1~3라운드 자리를 배치합니다.
    (이전의 고도화된 스왑 로직 적용)
    """
    n = len(people_list)
    if n == 0: return [], 0
    
    base_size = n // num_tables
    remainder = n % num_tables
    table_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_tables)]

    best_all_rounds = []
    min_overall_penalty = float('inf')

    for attempt in range(max_attempts):
        current_all_rounds = []
        current_met_pairs = set()
        person_visited = {p['매칭키']: set() for p in people_list}
        total_penalty = 0

        for r in range(total_rounds):
            unseated = people_list.copy()
            random.shuffle(unseated)
            round_tables = [[] for _ in range(num_tables)]

            for t_idx, t_size in enumerate(table_sizes):
                for _ in range(t_size):
                    if not unseated: break
                    # 단순 그리디 배치 (성비/대학/중복 등 고려)
                    best_p = unseated.
