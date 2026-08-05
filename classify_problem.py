import os
import json
import math
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

#1) API키 가져오기
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError (
        "OPENAI_API_KEY를 찾을 수 없습니다."
        ".env 파일 확인이 필요합니다."
        )
client = OpenAI(api_key=api_key)
EMBEDDING_MODEL = "text-embedding-3-small"

#2) 필요한 열 확인하는 함수 만들기
def check_columns(df, required_columns, file_name):
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError (f"{file_name}에 다음 열이 없습니다: {missing_columns}")

#3) 문제 하나를 임베딩하는 함수 만들기
def create_embedding(problem_text: str, model: str = EMBEDDING_MODEL) -> list[float]:
    if pd.isna(problem_text):
        raise ValueError("문제 내용이 비어 있습니다.")
    problem_text = str(problem_text).strip()
    if not problem_text:
        raise ValueError("문제 내용이 비어 있습니다. ")
    response = client.embeddings.create(
        model = model, 
        input=problem_text,
    )
    return response.data[0].embedding

#4) 코사인 유사도 함수 만들기(함수 만드는거끼리 모아두고 싶다.)
def cosine_similarity(vector_a, vector_b):
    if len(vector_a) != len(vector_b):
        raise ValueError("벡터 길이가 다릅니다.")
    dot_product = 0
    magnitude_a = 0
    magnitude_b = 0
    for a, b in zip(vector_a, vector_b):
        dot_product += a * b
        magnitude_a += a * a
        magnitude_b += b * b
    magnitude_a = math.sqrt(magnitude_a)
    magnitude_b = math.sqrt(magnitude_b)
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)

#5) 확인할 문제와 기준 문제들 비교하는 함수 만들기
def find_top_matches(problem_embedding, reference_df, top_n=5,):
    candidates_df=reference_df.copy()
    candidates_df["유사도"] = candidates_df["embedding"].apply(
        lambda reference_embedding: cosine_similarity(problem_embedding, reference_embedding, )
    )
    top_match_df = (
        candidates_df
        .sort_values(
        by = "유사도", ascending = False, 
        )
        .drop_duplicates(
            subset=["ID"], keep="first"
        )
        .head(top_n)
    )
    return top_match_df

#6) 지피티_후보들을 문자열로 만드는 함수
def make_candidate_text(top_matches_df):
    candidate_texts=[]
    for rank, (_, candidate_row) in enumerate(top_matches_df.iterrows(), start=1, ):
        candidate_text = f"""
후보 {rank}
ID: {int(candidate_row["ID"])}
차시명: {candidate_row["차시명"]}
분류기준: {candidate_row["분류기준"]}
제외기준: {candidate_row["제외기준"]}
가장 유사한 문제: {candidate_row["대표 문제"]}
코사인 유사도: {candidate_row["유사도"]:.6f}        
"""
        candidate_texts.append(candidate_text)
    return "\n".join(candidate_texts)

#7) 지피티_지피티에게 보내서 최종적으로 차시 하나 받기
def classify_with_gpt(problem_text, top_matches_df):
    candidate_text = make_candidate_text(top_matches_df)
    candidate_ids = [str(int(candidate_id)) for candidate_id in top_matches_df["ID"]]
    prompt = f"""
너는 고등학교 수학 문제를 교육과정의 차시별로 분류하는 분류기다. 
아래 수학 문제를 읽고, 주어진 후보 차시 중 가장 적절한 차시 하나를 선택해라. 
단순히 코사인 유사도가 가장 높은 후보를 그대로 선택하지 말고,
문제를 해결할 때 핵심적으로 사용하는 개념과 풀이 방법을 판단하라. 
각 후보의 분류기준과 제외기준을 모두 확인하라.

[분류할 문제]
{problem_text}

[후보 차시]
{candidate_text}

[출력 규칙]
1. 반드시 후보에 있는 ID 중 하나만 선택한다.
2. 차시명이나 설명은 출력하지 않는다. 
3. ID 숫자 하나만 출력한다.

답변:
"""
    response = client.responses.create(model="gpt-5-mini", input=prompt, )
    selected_id = response.output_text.strip()
    if selected_id not in candidate_ids:
        raise ValueError(
            "GPT가 후보에 없는 ID를 반환했습니다."
            f"GPT 응답: {selected_id}, "
            f"선택 가능한 ID: {candidate_ids}"
        )
    return selected_id

#8) 업로드된 두 엑셀을 이용하여 전체 분류 수행
def classify_excel(reference_df, problem_df, progress_callback=None, reference_embeddings = None, ):
    reference_df = reference_df.copy()
    problem_df = problem_df.copy()

    #1) 필요한 열 확인하기
    check_columns(reference_df, ["ID", "대단원", "중단원", "소단원", "차시명", "대표 문제", "분류기준", "제외기준"], "기준 엑셀")
    check_columns(problem_df, ["번호", "문제"], "분류할 문제 엑셀", )

    #+1) 진행률 계산용
    total_reference = len(reference_df)
    total_problems = len(problem_df)
    if reference_embeddings is None:
        reference_embeddings_steps = total_reference
    else: 
        reference_embeddings_steps = 0
    total_steps = (reference_embeddings_steps + total_problems + total_problems)
    completed_steps = 0


    #2) 기준 문제 임베딩 만들기
    if reference_embeddings is None:
        reference_embeddings = []
        for index, row in reference_df.iterrows():
            reference_problem = row["대표 문제"]
            print(f"{index+1}/{len(reference_df)}번째 "
                f"기준 대표 문제 임베딩 생성중: "
                f"{str(reference_problem)[:30]}...")
            embedding = create_embedding(reference_problem, model=EMBEDDING_MODEL)
            reference_embeddings.append(embedding)
            completed_steps += 1
            percent = int( completed_steps / total_steps *100 )
            if progress_callback:
                progress_callback ( percent, f"기준 대표 문제 임베딩 생성 중 ({index+1}/{len(reference_df)})", )
    else:
        if len(reference_embeddings) != total_reference:
            raise ValueError("기준 대표 문제 개수와 캐시된 임베딩 개수가 일치하지 않습니다.")
    reference_df["embedding"] = reference_embeddings

    #3) 문제 임베딩 만들기
    problem_embeddings = []
    for index, row in problem_df.iterrows():
        problem = row["문제"]
        print(
            f"{index+1}/{len(problem_df)}번째 문제 처리중:"
            f"{str(problem)[:30]}..."
        )
        embedding = create_embedding(problem)
        problem_embeddings.append(embedding)
        completed_steps += 1
        percent = int(completed_steps / total_steps *100)
        if progress_callback:
            progress_callback(
                percent, 
                f"분류할 문제 임베딩 완료"
                f"({index + 1}/{total_problems})", 
                )
    problem_df["embedding"] = problem_embeddings

    #4) 유사도 계산 및 gpt호출
    similarity_results = []
    final_results = []
    for problem_index, problem_row in problem_df.iterrows():
        problem_number = problem_row["번호"]
        problem_text = problem_row["문제"]
        problem_embedding = problem_row["embedding"]

        print(f"{problem_index +1 }/{len(problem_df)}번째 문제 유사도 계산 중")

        top_matches_df = find_top_matches(problem_embedding = problem_embedding, reference_df = reference_df, top_n=5, )

        print(f"{problem_index+1}/{len(problem_df)}번째 문제 GPT 분류 중")

        selected_id = classify_with_gpt(problem_text=problem_text, top_matches_df=top_matches_df, )
        selected_rows = top_matches_df[top_matches_df["ID"].astype(int) == int(selected_id)]
        if selected_rows.empty:
            raise ValueError(
                "GPT가 선택한 ID를 후보에서 찾지 못했습니다. "
                f"선택 ID: {selected_id}, "
                f"후보 ID: {top_matches_df['ID'].tolist()}"
            )
        selected_row = selected_rows.iloc[0]

        final_results.append({
            "번호": problem_number, 
            "문제": problem_text, 
            "예측 ID": int(selected_id), 
            "대단원": selected_row["대단원"], 
            "중단원": selected_row["중단원"], 
            "소단원": selected_row["소단원"], 
            "예측 차시명": selected_row["차시명"], 
            "선택 차시 유사도": selected_row["유사도"], 
        })

        completed_steps += 1
        percent = int(completed_steps/total_steps *100)
        if progress_callback:
            progress_callback(
                percent, 
                f"GPT 최종 분류 완료"
                f"({problem_index + 1}/{total_problems})"
            )


        for rank, (_, match_row) in enumerate(top_matches_df.iterrows(), start=1, ):
            similarity_results.append({
                "번호": problem_number, 
                "문제": problem_text, 
                "순위": rank, 
                "기준 ID": match_row["ID"], 
                "대단원": match_row["대단원"],
                "중단원": match_row["중단원"],
                "소단원": match_row["소단원"],
                "차시명": match_row["차시명"],
                "대표 문제": match_row["대표 문제"],
                "분류기준": match_row["분류기준"], 
                "제외기준": match_row["제외기준"], 
                "코사인 유사도": match_row["유사도"],
            })
    similarity_results_df = pd.DataFrame(similarity_results)
    final_results_df = pd.DataFrame(final_results)

    #5) 결과 저장
    similarity_results_df["코사인 유사도"] = similarity_results_df["코사인 유사도"].round(6)
    final_results_df["선택 차시 유사도"] = final_results_df["선택 차시 유사도"].round(6)

    return similarity_results_df, final_results_df



if __name__ == "__main__":
    #1) 사용할 파일 지정
    REFERENCE_FILE = "classification_reference_with_embeddings.xlsx"
    PROBLEM_FILE = "problems_to_classify.xlsx"
    SIMILARITY_OUTPUT_FILE = "similarity_result.xlsx"
    FINAL_OUTPUT_FILE = "final_classification_result.xlsx"

    #2) 엑셀 읽기
    reference_df = pd.read_excel(REFERENCE_FILE, engine="openpyxl")
    print("기준 엑셀 파일을 불러왔습니다.")
    problem_df = pd.read_excel(PROBLEM_FILE, engine="openpyxl")
    print("분류할 문제 엑셀 파일을 불러왔습니다.")

    #3) 함수 실행
    similarity_result_df, final_results_df = classify_excel(reference_df=reference_df, problem_df=problem_df, )

    #4) 결과 저장
    similarity_result_df.to_excel(SIMILARITY_OUTPUT_FILE, index=False, engine="openpyxl", )
    final_results_df.to_excel(FINAL_OUTPUT_FILE, index=False, engine="openpyxl", )

    print()
    print("문제 분류가 완료되었습니다.")
    print(f"Top 5 결과 파일: {SIMILARITY_OUTPUT_FILE}")
    print(f"GPT 최종 결과 파일: {FINAL_OUTPUT_FILE}")
