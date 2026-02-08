import re
import pdfplumber
import docx2txt

SKILLS = [
    "talent acquisition", "recruitment", "interviewing",
    "hr analytics", "onboarding", "compensation",
    "excel", "sql", "power bi", "python",
    "stakeholder management", "communication",
    "marketing", "seo", "content strategy",
    "procurement", "vendor management",
    "project management", "data analysis"
]

def extract_text(file, file_type):
    text = ""
    if file_type == "pdf":
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    elif file_type == "docx":
        text = docx2txt.process(file)
    return text.lower()

def extract_email(text):
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return match.group(0) if match else ""

def extract_phone(text):
    match = re.search(r"\+?\d{1,3}[\s\-]?\d{10}|\b\d{10}\b", text)
    return match.group(0) if match else ""

def extract_name(text):
    lines = text.split("\n")[:5]
    for line in lines:
        if len(line.split()) in [2, 3] and "@" not in line:
            return line.title()
    return ""

def extract_skills(text):
    found = [s for s in SKILLS if s in text]
    return ", ".join(sorted(set(found)))
