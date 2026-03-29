import streamlit as st
import pandas as pd
import random
import io
import uuid

# 페이지 설정
st.set_page_config(page_title="청취담 연합파티 매칭", page_icon="🍻", layout="wide")

# ==========================================
# [보안] 관리자 로그인 시스템 및 캐시 키 초기화
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = str(uuid.uuid4())

if not st.session_state["authenticated"]:
    st.title("🔒 관리자 로그인")
    st.info("스케줄러에 접근하려면 비밀번호를 입력해주세요.")
    
    pwd = st.text_input("비밀번호", type="password")
    
    if st.button("로그인"):
        if pwd == "1234": # 실제 운영 시 비밀번호 변경 권장
            st.session_state["authenticated"] = True
            st.rerun() 
        else:
            st.error("⚠️ 비밀번호가 틀렸습니다.")
            
    st.stop()

# ==========================================
# [코어] 배치 알고리즘 (패널티 기반 최적화)
# ==========================================
def generate_full_schedule(people_list, num_tables, past_met_pairs=None, total_rounds=3, max_attempts=300, progress_bar=None, status_text=None):
    n = len(people_list)
    base_size = n // num_tables
    remainder = n % num_tables
    table_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_tables)]

    # 목표 성비 및 대학 비율 계산
    total_m = sum(1 for p in people_list if p['성별'] == '남')
    total_w = sum(1 for p in people_list if p['성별'] == '여')
    min_w = total_w // num_tables
    max_w = (total_w + num_tables - 1) // num_tables if num_tables else 0
    min_m = total_m // num_tables
    max_m = (total_m + num_tables - 1) // num_tables if num_tables else 0
    
    unique_univs = set(p['재학중인대학'] for p in people_list)
    univ_counts = {u: sum(1 for p in people_list if p['재학중인대학'] == u) for u in unique_univs}
    min_u = {u: count // num_
