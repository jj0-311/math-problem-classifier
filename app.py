import streamlit as st
import pandas as pd
from classify_problem import (EMBEDDING_MODEL, classify_excel, create_embedding)
from io import BytesIO


#데이터 프레임을 엑셀로
def dataframe_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl", ) as writer: 
        df.to_excel(writer, index = False, sheet_name="분류 결과", )
    output.seek(0)
    return output.getvalue()

#대표문제 임베딩을 캐시
@st.cache_data(show_spinner=False, persist="disk", )
def create_reference_embeddings_cached (reference_problems, embedding_model, ):
    embeddings=[]
    for reference_problem in reference_problems:
        embedding = create_embedding(reference_problem, model=embedding_model)
        embeddings.append(embedding)
    return embedding



st.title("수학 문제 AI 분류기")

if st.button("임베딩 캐시 초기화"):
    create_reference_embeddings_cached.clear()
    st.success("대표문제 임베딩 캐시를 초기화했습니다.")

st.write(
    "기준 대표문제 엑셀과 분류할 문제 엑셀을 업로드하면 "
    "AI가 문제를 차시별로 분류합니다."
)

#분류 결과를 기억하는 공간
if "similarity_df" not in st.session_state:
    st.session_state.similarity_df = None
if "final_df" not in st.session_state:
    st.session_state.final_df = None

#파일 업로드
reference_file = st.file_uploader("기준 엑셀 업로드", type="xlsx", )
problem_file = st.file_uploader("분류할 문제 엑셀 업로드", type="xlsx", )
if reference_file is not None:
    st.success("기준 엑셀 업로드 완료!")
if problem_file is not None:
    st.success("분류할 문제 업로드 완료!")

#둘 다 업로드 되었을 때 데이터프레임으로 변환
if reference_file is not None and problem_file is not None:
    refrence_df = pd.read_excel(reference_file, engine="openpyxl", )
    problem_df = pd.read_excel(problem_file, engine="openpyxl", )
    st.success("두 파일 모두 읽었습니다.")

    if st.button("분류 시작"):
        st.session_state.similarity_df = None
        st.session_state.final_df = None
        with st.status("문제 분류를 시작합니다.", expanded=True, )as status:
            st.write("대표 문제와 분류할 문제를 임베딩하고 있습니다.")
            progress_bar = st.progress(0)
            progress_text = st.empty()
            def update_progress(percent, message):
                progress_bar.progress(percent)
                progress_text.write(message)
            try:
                if "대표 문제" not in refrence_df.columns:
                    raise ValueError("기준 엑셀에 다음 열이 없습니다: ['대표 문제']")
                if refrence_df["대표 문제"].isna().any():
                    raise ValueError("기준 엑셀의 '대표 문제' 열에 비어 있는 셀이 있습니다.")
                reference_problems = tuple(refrence_df["대표 문제"].astype(str).str.strip().tolist())
                progress_text.write("기준 대표 문제 임베딩을 확인하고 있습니다.")
                reference_embeddings = (create_reference_embeddings_cached(reference_problems=reference_problems, embedding_model=EMBEDDING_MODEL, ))
                progress_text.write("기준 대표 문제 임베딩 준비가 완료되었습니다.")
                similarity_df, final_df = classify_excel(reference_df=refrence_df, problem_df=problem_df, progress_callback=update_progress, )
                progress_bar.progress(100)
                progress_text.write(("모든 문제 분류가 완료되었습니다."))
                #분류결과 기억
                st.session_state.similarity_df = similarity_df
                st.session_state.final_df = final_df
                status.update(label="문제 분류가 완료되었습니다.", state="complete", expanded=False, )
            except ValueError as error:
                status.update(label="입력 파일을 확인해주세요.", state="error", expanded=True, )
                st.error(str(error))
            except Exception as error:
                status.update(label="문제 분류 중 오류가 발생했습니다.", state="error", expanded=True, )
                st.error(
                    "예상하지 못한 오류가 발생했습니다."
                    "잠시 후 다시 시도해주세요."
                )
                st.write("오류 내용:", str(error))

#기억한 결과가 있을 때 표시
if st.session_state.final_df is not None:
    final_df = st.session_state.final_df
    similarity_df = st.session_state.final_df
    st.success("문제 분류가 완료되었습니다.")
    st.subheader("GPT 최종 분류 결과")
    st.dataframe(final_df, use_container_width=True, )
    final_excel_data = dataframe_to_excel_bytes(final_df)
    similarity_excel_data = dataframe_to_excel_bytes(similarity_df)
    st.download_button(label = "GPT 최종 결과 엑셀 다운로드", data=final_excel_data, file_name="final_classification_result.xlsx", mime=("application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"), )
    st.download_button(label="TOP 5 결과 엑셀 다운로드", data = similarity_excel_data, file_name="similarity_result.xlsx", mime=("application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"), )
