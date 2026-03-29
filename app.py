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

# --- 2. 매칭 알고리즘 (작동 가능한 전체 로직) ---
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
                    # [오류 해결] 마침표 제거 및 팝 로직 정상화
                    best_p = unseated.pop(0) 
                    round_tables[t_idx].append(best_p)
            
            # 패널티 계산: 같은 테이블 재방문 방지
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
    
    rename_dict = {}
    for col in df.columns:
        if '성별' in col: rename_dict[col] = '성별'
        elif any(x in col for x in ['대학', '학교', '소속']): rename_dict[col] = '재학중인대학'
        elif '이름' in col: rename_dict[col] = '이름'
        elif any(x in col for x in ['연락처', '전화번호', '번호']): rename_dict[col] = '전화번호'
        elif any(x in col for x in ['참여', '신규', '이력']): rename_dict[col] = '참여이력'
    df = df.rename(columns=rename_dict)

    df['성별'] = df['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
    df['재학중인대학'] = df['재학중인대학'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
    df['참여이력'] = df['참여이력'].astype(str).apply(lambda x: '크루' if any(i in x for i in ['크루', '기존', '참여']) else '신규')
    df['전화번호'] = df['전화번호'].astype(str).replace('nan', '0000')
    df['매칭키'] = df['이름'] + "_" + df['전화번호'].str[-4:]

    # 1. 현황 표시
    st.subheader("📊 전체 신청자 현황")
    c1, c2, c3 = st.columns(3)
    c1.metric("총 신청자", f"{len(df)}명")
    c2.metric("🌟 신규 신청자", f"{len(df[df['참여이력'] == '신규'])}명")
    c3.metric("🎖️ 크루(기존)", f"{len(df[df['참여이력'] == '크루'])}명")

    # 2. 소수 대학 우선 선발
    st.write("---")
    if st.button("🚀 1단계: 소수 대학 배려 선발 실행", use_container_width=True):
        m_df = df[df['성별'] == '남']
        w_df = df[df['성별'] == '여']
        target_half = party_capacity // 2

        def balance_selection(gender_df, target_n):
            final_sel = pd.DataFrame()
            curr_target = target_n
            univ_order = gender_df['재학중인대학'].value_counts().sort_values().index.tolist()
            for i, univ in enumerate(univ_order):
                pool = gender_df[gender_df['재학중인대학'] == univ]
                rem_univs = len(univ_order) - i
                quota = curr_target // rem_univs
                sel = pool if len(pool) <= quota else pool.sample(n=quota)
                final_sel = pd.concat([final_sel, sel])
                curr_target -= len(sel)
            if curr_target > 0:
                rem = gender_df.drop(final_sel.index)
                final_sel = pd.concat([final_sel, rem.sample(n=min(curr_target, len(rem)))])
            return final_sel

        st.session_state['selected_df'] = pd.concat([balance_selection(m_df, target_half), balance_selection(w_df, target_half)]).sample(frac=1).reset_index(drop=True)
        st.success("🎉 선발 완료!")

    if 'selected_df' in st.session_state:
        sel_df = st.session_state['selected_df']
        st.write("### ✅ 최종 선발 명단")
        st.dataframe(sel_df[['이름', '성별', '재학중인대학', '참여이력', '전화번호']], hide_index=True)

        if st.button("🔀 2단계: 전체 라운드 자리 배치 시작", use_container_width=True):
            people_list = sel_df.to_dict('records')
            all_rounds, score = generate_full_schedule(people_list, table_count)
            st.session_state['all_rounds_data'] = all_rounds
            st.session_state['stage2_done'] = True
            st.success("📍 배치 완료!")

        if st.session_state.get('stage2_done'):
            st.write("---")
            st.write("### 📝 개별 안내용 텍스트")
            guide_output = ""
            all_r = st.session_state['all_rounds_data']
            for idx, row in sel_df.iterrows():
                suffix = str(row['전화번호'])[-4:]
                r_info = [f"{r_idx+1}R: {next((t_i + 1 for t_i, table in enumerate(all_r[r_idx]) if any(p['매칭키'] == row['매칭키'] for p in table)), '?')}번" for r_idx in range(len(all_r))]
                guide_output += f"{idx+1}. {row['이름']}({suffix})\n   ㄴ {', '.join(r_
