import streamlit as st
import pandas as pd
from datetime import date
from database import create_tables, get_connection
from resume_parser import (
    extract_text,
    extract_email,
    extract_phone,
    extract_skills,
    extract_name
)

# -------------------------------------------------
# Setup
# -------------------------------------------------
st.set_page_config(page_title="ATS MVP", layout="wide")
st.title("🧩 Applicant Tracking System")

create_tables()
conn = get_connection()

# -------------------------------------------------
# Helper: Skill match + decision logic
# -------------------------------------------------
def auto_decide_candidate(parsed_skills, required_skills):
    if not required_skills:
        return "Screening", 0.0

    req = {s.strip() for s in required_skills.split(",") if s.strip()}
    parsed = {s.strip() for s in parsed_skills.split(",") if s.strip()}

    if not parsed or not req:
        return "Rejected", 0.0

    match_ratio = len(req & parsed) / len(req)
    match_pct = round(match_ratio * 100, 1)

    if match_ratio >= 0.5:
        return "Interview", match_pct
    elif match_ratio >= 0.3:
        return "Screening", match_pct
    else:
        return "Rejected", match_pct

# -------------------------------------------------
# Sidebar (ORDER AS REQUESTED)
# -------------------------------------------------
menu = st.sidebar.radio(
    "Navigation",
    [
        "1️⃣ Job Creation",
        "2️⃣ Manage Job",
        "3️⃣ Upload Resume",
        "4️⃣ Interview Selection",
        "5️⃣ Upload Excel",
        "6️⃣ Dashboard / View Candidates"
    ]
)

# =================================================
# 1️⃣ JOB CREATION
# =================================================
if menu == "1️⃣ Job Creation":
    st.header("Job Creation")

    job_code = st.text_input("Job ID / Code")
    title = st.text_input("Job Title")
    department = st.text_input("Department")

    created_date = st.date_input("Job Created Date", date.today())
    closed_date = st.date_input("Job Close Date")

    required_skills = st.text_area(
        "Required Skills (comma-separated)",
        placeholder="e.g. recruitment, onboarding, hr analytics"
    )

    if st.button("Create Job"):
        if job_code and title:
            conn.execute(
                """
                INSERT INTO jobs
                (job_code, title, department, created_date, closed_date, required_skills, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_code.strip(),
                    title.strip(),
                    department.strip(),
                    str(created_date),
                    str(closed_date),
                    required_skills.lower(),
                    "Open"
                )
            )
            conn.commit()
            st.success("✅ Job created successfully")
        else:
            st.warning("Job ID and Title are mandatory")

# =================================================
# 2️⃣ MANAGE JOB
# =================================================
elif menu == "2️⃣ Manage Job":
    st.header("Manage Jobs")

    jobs = pd.read_sql("SELECT * FROM jobs", conn)
    if jobs.empty:
        st.info("No jobs available")
        st.stop()

    jobs["job_display"] = jobs["id"].astype(str) + " | " + jobs["job_code"] + " | " + jobs["title"]
    selected_job = st.selectbox("Select Job", jobs["job_display"])
    job_id = int(selected_job.split(" | ")[0])

    count_df = pd.read_sql(
        "SELECT COUNT(*) AS cnt FROM candidates WHERE job_id = ?",
        conn,
        params=(job_id,)
    )

    if count_df["cnt"][0] > 0:
        st.warning("❌ Cannot delete job with candidates attached")
    else:
        if st.button("🗑️ Delete Job"):
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            st.success("Job deleted")
            st.rerun()

# =================================================
# 3️⃣ UPLOAD RESUME (SHOW MATCH + DECISION)
# =================================================
elif menu == "3️⃣ Upload Resume":
    st.header("Bulk Resume Upload (with Skill Match)")

    jobs = pd.read_sql("SELECT * FROM jobs", conn)
    jobs["job_display"] = jobs["id"].astype(str) + " | " + jobs["job_code"]
    selected_job = st.selectbox("Select Job", jobs["job_display"])
    job_id = int(selected_job.split(" | ")[0])

    required_skills = jobs[jobs["id"] == job_id]["required_skills"].values[0]

    files = st.file_uploader(
        "Upload resumes (PDF / DOCX)",
        type=["pdf", "docx"],
        accept_multiple_files=True
    )

    parsed_rows = []

    if files:
        for f in files:
            text = extract_text(f, f.name.split(".")[-1])
            skills = extract_skills(text)
            stage, match_pct = auto_decide_candidate(skills, required_skills)

            parsed_rows.append({
                "Name": extract_name(text),
                "Email": extract_email(text),
                "Phone": extract_phone(text),
                "Skills": skills,
                "Match %": match_pct,
                "Decision": stage
            })

        preview_df = pd.DataFrame(parsed_rows)
        st.subheader("Preview (System Decision Shown)")
        st.dataframe(preview_df, use_container_width=True)

        if st.button("Save Candidates"):
            for _, r in preview_df.iterrows():
                if not r["Email"]:
                    continue

                conn.execute(
                    """
                    INSERT INTO candidates
                    (name, email, phone, skills, stage, match_pct, job_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["Name"],
                        r["Email"],
                        r["Phone"],
                        r["Skills"],
                        r["Decision"],
                        r["Match %"],
                        job_id
                    )
                )

            conn.commit()
            st.success("✅ Candidates saved with decisions")
            st.rerun()

# =================================================
# 4️⃣ INTERVIEW SELECTION (EXPLAINABLE)
# =================================================
elif menu == "4️⃣ Interview Selection":
    st.header("Shortlisted for Interview")

    df = pd.read_sql(
        """
        SELECT
            j.job_code,
            j.title,
            c.name,
            c.email,
            c.match_pct,
            c.skills
        FROM candidates c
        JOIN jobs j ON c.job_id = j.id
        WHERE c.stage = 'Interview'
        """,
        conn
    )

    if df.empty:
        st.info("No shortlisted candidates yet")
    else:
        st.dataframe(df, use_container_width=True)

# =================================================
# 5️⃣ UPLOAD EXCEL
# =================================================
elif menu == "5️⃣ Upload Excel":
    st.header("Bulk Excel Upload")

    jobs = pd.read_sql("SELECT * FROM jobs", conn)
    jobs["job_display"] = jobs["id"].astype(str) + " | " + jobs["job_code"]
    selected_job = st.selectbox("Assign to Job", jobs["job_display"])
    job_id = int(selected_job.split(" | ")[0])

    file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

    if file:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.lower()
        st.dataframe(df)

        if st.button("Upload to ATS"):
            for _, r in df.iterrows():
                conn.execute(
                    """
                    INSERT INTO candidates
                    (name, email, phone, skills, stage, match_pct, job_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.get("name", ""),
                        r.get("email", ""),
                        r.get("phone", ""),
                        r.get("skills", ""),
                        r.get("stage", "Applied"),
                        r.get("match_pct", 0),
                        job_id
                    )
                )
            conn.commit()
            st.success("Excel uploaded")
            st.rerun()

# =================================================
# 6️⃣ DASHBOARD / VIEW CANDIDATES
# =================================================
elif menu == "6️⃣ Dashboard / View Candidates":
    st.header("Hiring Dashboard")

    jobs = pd.read_sql("SELECT * FROM jobs", conn)
    jobs["job_display"] = jobs["id"].astype(str) + " | " + jobs["job_code"]
    selected_job = st.selectbox("Select Job", jobs["job_display"])
    job_id = int(selected_job.split(" | ")[0])

    df = pd.read_sql(
        """
        SELECT name, email, stage, match_pct, skills
        FROM candidates
        WHERE job_id = ?
        """,
        conn,
        params=(job_id,)
    )

    if df.empty:
        st.info("No candidates for this job")
        st.stop()

    # ---- Stats ----
    st.subheader("Key Statistics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Candidates", len(df))
    c2.metric("Interview", (df["stage"] == "Interview").sum())
    c3.metric("Rejected", (df["stage"] == "Rejected").sum())

    # ---- Funnel ----
    st.subheader("Hiring Funnel")
    funnel = df["stage"].value_counts().reset_index()
    funnel.columns = ["Stage", "Candidates"]
    st.bar_chart(funnel.set_index("Stage"))

    # ---- Table ----
    st.subheader("Candidate Details")
    st.dataframe(df, use_container_width=True)
