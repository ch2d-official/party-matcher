import streamlit as st
import pandas as pd
import random
import io
import uuid

# [기존 설정 유지]
st.set_page_config(page_title="청취담 연합파티 매칭", page_icon="🍻", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = str(uuid.uuid4())

def reset_matching_state():
    keys_to_clear = ['selected_df', 'waitlist_df', 'all_rounds_data', 'final_score', 'stage2_done']
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

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

# --- 2. 알고리즘 함수 (이전 답변의 개선된 버전 유지) ---
def generate_full_schedule(people_list, num_tables, past_met_pairs=None, total_rounds=3):
    # (내부 로직은 이전과 동일하되 가독성을 위해 생략, 실제 코드 구현 시 위 swap 로직 포함)
    # ... [이전 답변의 generate_full_schedule 함수 내용이 들어가는 자리] ...
    pass 

# --- 3. 메인 화면 ---
st.title("🍻 청취담 연합파티 스케줄러")
st.sidebar.header("⚙️ 파티 설정")
party_capacity = st.sidebar.number_input("이번 파티 참가 정원 (명)", min_value=4, value=48, step=1)
table_count = st.sidebar.number_input("준비된 테이블 개수", min_value=1, value=12, step=1)

uploaded_file = st.file_uploader("📂 신청자 명단 업로드", type=['xlsx', 'csv'], key=st.session_state['uploader_key'], on_change=reset_matching_state)

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    # 컬럼 클리닝 및 표준화
    df.columns = [str(col).replace('(*)', '').replace(' ', '').strip() for col in df.columns]
    
    # 필수 컬럼 매핑
    rename_dict = {}
    for col in df.columns:
        if '성별' in col: rename_dict[col] = '성별'
        elif '대학' in col or '학교' in col: rename_dict[col] = '재학중인대학'
        elif '이름' in col: rename_dict[col] = '이름'
        elif '연락처' in col or '전화번호' in col: rename_dict[col] = '전화번호'
        elif '참여' in col or '신규' in col: rename_dict[col] = '참여이력'
        elif 'MBTI' in col.upper(): rename_dict[col] = 'MBTI'
    df = df.rename(columns=rename_dict)

    # 기본 전처리
    df['성별'] = df['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
    df['재학중인대학'] = df['재학중인대학'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
    df['참여이력'] = df['참여이력'].astype(str).apply(lambda x: '크루' if '크루' in x or '기존' in x else '신규')
    df['전화번호'] = df['전화번호'].astype(str).replace('nan', '0000')
    
    # 1. 신청자 현황 표시 (크루/신규 포함)
    total_count = len(df)
    crew_count = len(df[df['참여이력'] == '크루'])
    new_count = len(df[df['참여이력'] == '신규'])
    
    st.subheader("📊 전체 신청자 현황")
    c1, c2, c3 = st.columns(3)
    c1.metric("총 신청자", f"{total_count}명")
    c2.metric("🌟 신규 신청자", f"{new_count}명")
    c3.metric("🎖️ 크루(기존)", f"{crew_count}명")

    # 2. 소수 대학 우선 선발 로직
    if st.button("🚀 1단계: 소수 대학 배려 선발 실행"):
        with st.spinner("대학별 인원 비율을 계산하여 선발 중..."):
            # 대학별 신청 인원 계산
            univ_stats = df['재학중인대학'].value_counts().sort_values() # 인원 적은 순
            
            # 성별 분리 (성비 1:1 유지 목적)
            selected_list = []
            m_df = df[df['성별'] == '남']
            w_df = df[df['성별'] == '여']
            
            target_half = party_capacity // 2
            
            def balance_univ_selection(gender_df, target_n):
                final_gen_sel = pd.DataFrame()
                current_target = target_n
                
                # 신청 인원이 적은 대학부터 루프
                univ_list = gender_df['재학중인대학'].value_counts().sort_values().index.tolist()
                
                for i, univ in enumerate(univ_list):
                    univ_pool = gender_df[gender_df['재학중인대학'] == univ]
                    # 남은 대학 수에 따른 균등 배분 목표 (소수 대학은 전원 선발 경향)
                    remaining_univs = len(univ_list) - i
                    quota = current_target // remaining_univs
                    
                    if len(univ_pool) <= quota:
                        # 소수 대학 인원이 할당량보다 적으면 전원 합격
                        sel = univ_pool
                    else:
                        # 할당량만큼만 랜덤 선발
                        sel = univ_pool.sample(n=quota)
                    
                    final_gen_sel = pd.concat([final_gen_sel, sel])
                    current_target -= len(sel)
                
                # 정원이 남았다면 (소수 대학이 너무 적어서), 나머지 인원 중 랜덤 추가 선발
                if current_target > 0:
                    rem_pool = gender_df.drop(final_gen_sel.index)
                    add_sel = rem_pool.sample(n=min(current_target, len(rem_pool)))
                    final_gen_sel = pd.concat([final_gen_sel, add_sel])
                    
                return final_gen_sel

            sel_m = balance_univ_selection(m_df, target_half)
            sel_w = balance_univ_selection(w_df, target_half)
            
            final_sel_df = pd.concat([sel_m, sel_w]).sample(frac=1).reset_index(drop=True)
            final_wait_df = df.drop(final_sel_df.index).sample(frac=1).reset_index(drop=True)
            
            st.session_state['selected_df'] = final_sel_df
            st.session_state['waitlist_df'] = final_wait_df
            st.success(f"✅ 선발 완료 (참가: {len(final_sel_df)}명 / 대기: {len(final_wait_df)}명)")

    # 결과 표시 및 안내 텍스트 생성
    if 'selected_df' in st.session_state:
        sel_df = st.session_state['selected_df']
        st.write("### ✅ 최종 선발 명단 (대학 비율 반영)")
        st.dataframe(sel_df[['이름', '성별', '재학중인대학', '참여이력', '전화번호']], hide_index=True)

        # [안내용 텍스트 생성 섹션]
        st.write("---")
        st.write("### 📝 개별 안내용 텍스트 (카톡 전송용)")
        
        # 2단계 배치가 완료된 경우에만 테이블 번호 포함
        guide_text = ""
        for idx, row in sel_df.iterrows():
            # 전화번호 뒷자리 4자리 추출
            phone = str(row['전화번호'])
            suffix = phone[-4:] if len(phone) >= 4 else "0000"
            
            guide_text += f"{idx+1}. {row['이름']}({suffix})\n"
            # 배치 정보가 세션에 있다면 추가
            if 'all_rounds_data' in st.session_state:
                # 여기에 라운드별 테이블 찾는 로직 추가
                pass 
            guide_text += "\n"
            
        st.text_area("이름 옆에 전화번호 뒷자리가 추가되었습니다.", guide_text, height=300)
