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
        if pwd == "1234":
            st.session_state["authenticated"] = True
            st.rerun() 
        else:
            st.error("⚠️ 비밀번호가 틀렸습니다.")
    st.stop()

# --- 2. 매칭 알고리즘 ---
def generate_full_schedule(people_list, num_tables, total_rounds=3, max_attempts=100):
    n = len(people_list)
    if n == 0: return [], 0
    
    base_size = n // num_tables
    remainder = n % num_tables
    table_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_tables)]

    best_all_rounds = []
    min_overall_penalty = float('inf')

    for attempt in range(max_attempts):
        current_all_rounds = []
        person_visited = {p['매칭키']: set() for p in people_list}
        total_penalty = 0

        for r in range(total_rounds):
            unseated = people_list.copy()
            random.shuffle(unseated)
            round_tables = [[] for _ in range(num_tables)]

            for t_idx, t_size in enumerate(table_sizes):
                for _ in range(t_size):
                    if not unseated: break
                    best_p = unseated.pop(0) 
                    round_tables[t_idx].append(best_p)
            
            for t_idx, table in enumerate(round_tables):
                for p in table:
                    if t_idx in person_visited[p['매칭키']]: 
                        total_penalty += 10
                    person_visited[p['매칭키']].add(t_idx)
            
            current_all_rounds.append(round_tables)
        
        if total_penalty < min_overall_penalty:
            min_overall_penalty = total_penalty
            best_all_rounds = current_all_rounds
        if min_overall_penalty == 0: break

    return best_all_rounds, min_overall_penalty

# --- 3. 메인 UI 및 로직 ---
st.title("🍻 청취담 연합파티 스케줄러")
st.sidebar.header("⚙️ 파티 설정")
party_capacity = st.sidebar.number_input("이번 파티 참가 정원 (명)", min_value=4, value=48, step=1)
table_count = st.sidebar.number_input("준비된 테이블 개수", min_value=1, value=12, step=1)

uploaded_file = st.file_uploader("📂 신청자 명단 업로드", type=['xlsx', 'csv'], key=st.session_state['uploader_key'], on_change=reset_matching_state)

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df.columns = [str(col).replace('(*)', '').replace(' ', '').strip() for col in df.columns]
