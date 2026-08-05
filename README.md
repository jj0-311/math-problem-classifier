# 📚 AI Math Problem Classifier

> Embedding + Cosine Similarity + GPT를 활용한 고등학교 수학 문제 자동 분류 프로그램

---

## 📖 프로젝트 소개

새로운 수학 문제가 입력되면 교육과정의 차시를 자동으로 분류하는 AI 프로그램입니다.

이 프로젝트는 임베딩과 코사인 유사도를 이용해 가장 유사한 차시 후보를 먼저 추출한 뒤,
GPT가 최종적으로 가장 적절한 차시를 선택하는 2단계 분류 방식을 사용합니다.

---

## 🔄 분류 과정

```text
기준 대표 문제 엑셀 업로드
        ↓
기준 대표 문제 임베딩 생성
        ↓
분류할 문제 엑셀 업로드
        ↓
분류할 문제 임베딩 생성
        ↓
코사인 유사도 계산
        ↓
차시별 Top 5 후보 추출
        ↓
GPT 최종 판단
        ↓
최종 차시 선택
        ↓
결과 엑셀 다운로드
```

---

## 🚀 주요 기능

- 🧠 OpenAI Embedding API를 이용한 문제 임베딩 생성
- 📐 코사인 유사도 계산
- 🏆 차시별 Top 5 후보 추출
- 🤖 GPT를 이용한 최종 차시 선택
- 🌐 Streamlit 기반 웹 인터페이스
- 📥 결과 엑셀 다운로드
- ⚡ 대표 문제 임베딩 Disk Cache 지원
- 📊 진행률 표시
- ✅ 입력 파일 검증 및 오류 처리

---

## 🛠 기술 스택

- Python
- OpenAI API
- Streamlit
- Pandas
- Openpyxl
- python-dotenv

---

## 📁 프로젝트 구조

```text
math-problem-classifier/
├── app.py
├── classify_problem.py
├── classification_reference.xlsx
├── problems_to_classify.xlsx
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md