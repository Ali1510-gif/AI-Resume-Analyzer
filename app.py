import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from pypdf import PdfReader
from docx import Document
import os

# -------------------- CONFIG --------------------
st.set_page_config(page_title="AI Resume Analyzer", layout="wide", page_icon="🤖")

# -------------------- STATE --------------------
class State(TypedDict):
    resume: str
    analysis: str
    feedback: str
    count: int

# -------------------- LLM --------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

# -------------------- NODES --------------------
def analyse_resume(state):
    prompt = f"""
Analyse the following resume and provide detailed improvement suggestions.

Focus on:
- Skills
- Experience
- Projects
- Structure
- Impact 

Resume:
{state['resume']}

Give at least 5 strong, actionable suggestions.
"""

    if state["feedback"]:
        prompt += f"\n\nPrevious Feedback: {state['feedback']}"

    response = llm.invoke(prompt)

    return {
        "analysis": response.content,
        "count": state["count"] + 1
    }


def review_analysis(state):
    text = state["analysis"]

    if len(text) < 200:
        return {"feedback": "Too short, add more details."}

    if "skills" not in text.lower():
        return {"feedback": "Missing skills section."}

    return {"feedback": "good"}


def should_continue(state):
    if state["feedback"] == "good" or state["count"] >= 3:
        return "end"
    return "retry"

# -------------------- GRAPH --------------------
builder = StateGraph(State)

builder.add_node("analyse", analyse_resume)
builder.add_node("review", review_analysis)

builder.add_edge(START, "analyse")
builder.add_edge("analyse", "review")

builder.add_conditional_edges(
    "review",
    should_continue,
    {
        "end": END,
        "retry": "analyse"
    }
)

graph = builder.compile()

# -------------------- UI --------------------
st.title("🤖 AI Resume Analyzer")
st.caption("LangGraph + LLM powered resume feedback system")

uploaded_file = st.file_uploader(
    "Upload Resume",
    type=["pdf", "docx", "txt"]
)

resume_text = ""

if uploaded_file:
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                resume_text += page.extract_text() or ""

        elif "word" in uploaded_file.type:
            doc = Document(uploaded_file)
            resume_text = "\n".join([p.text for p in doc.paragraphs])

        else:
            resume_text = uploaded_file.read().decode("utf-8")

        st.success("Resume uploaded successfully!")

    except Exception as e:
        st.error(f"Error reading file: {e}")

# -------------------- BUTTON --------------------
if st.button("Analyze Resume"):
    if not resume_text.strip():
        st.warning("Please upload a resume first.")
    else:
        with st.spinner("Analyzing..."):
            result = graph.invoke({
                "resume": resume_text,
                "analysis": "",
                "feedback": "",
                "count": 0
            })

        st.subheader("Suggestions")
        st.write(result["analysis"])

        st.subheader("Iterations Used")
        st.metric("Count", result["count"])
