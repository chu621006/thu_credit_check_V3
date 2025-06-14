import pdfplumber
import pandas as pd
import json
import re

def load_category_map():
    with open("data/category_map.json", "r", encoding="utf-8") as f:
        return json.load(f)

def parse_pdf(uploaded_file):
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_courses(text):
    lines = text.splitlines()
    courses = []
    for line in lines:
        match = re.search(r"(.+?)\s+(\d+(?:\.\d+)?)學分\s+GPA[:：]?\s*(\S+)?", line)
        if match:
            name, credit, gpa = match.groups()
            credit = float(credit)
            gpa_val = float(gpa) if gpa and gpa.replace('.', '', 1).isdigit() else None
            courses.append({"課程名稱": name.strip(), "學分": credit, "GPA": gpa_val})
    return pd.DataFrame(courses)

def analyze_pdf(uploaded_file):
    text = parse_pdf(uploaded_file)
    df = extract_courses(text)
    category_map = load_category_map()

    if df.empty:
        return {
            "course_table": pd.DataFrame(),
            "summary_table": pd.DataFrame([{
                "分類": "必修", "已修學分": 0, "應修學分": 84
            }, {
                "分類": "I 類選修", "已修學分": 0, "應修學分": 10
            }, {
                "分類": "II 類選修", "已修學分": 0, "應修學分": 10
            }, {
                "分類": "選修總學分", "已修學分": 0, "應修學分": 44
            }])
        }

    # 類別初始化
    for col in ["必修", "I類選修", "II類選修", "一般選修"]:
        df[col] = False

    for i, row in df.iterrows():
        name = row["課程名稱"]
        for cat, names in category_map.items():
            if name in names:
                df.at[i, cat] = True

    # ✅ 正確縮排且安全的學分計算
    def compute_valid_credit(r):
        try:
            return r["學分"] if r["GPA"] is not None and r["GPA"] >= 1.7 else 0
        except:
            return 0

    df["有效學分"] = df.apply(compute_valid_credit, axis=1)

    summary = {
        "必修": df[df["必修"]]["有效學分"].sum(),
        "I類選修": df[df["I類選修"]]["有效學分"].sum(),
        "II類選修": df[df["II類選修"]]["有效學分"].sum(),
        "一般選修": df[df["一般選修"]]["有效學分"].sum(),
    }

    total_elective = summary["I類選修"] + summary["II類選修"] + summary["一般選修"]

    summary_table = pd.DataFrame([{
        "分類": "必修", "已修學分": summary["必修"], "應修學分": 84
    }, {
        "分類": "I 類選修", "已修學分": summary["I類選修"], "應修學分": 10
    }, {
        "分類": "II 類選修", "已修學分": summary["II類選修"], "應修學分": 10
    }, {
        "分類": "選修總學分", "已修學分": total_elective, "應修學分": 44
    }])

    return {
        "course_table": df,
        "summary_table": summary_table
    }
