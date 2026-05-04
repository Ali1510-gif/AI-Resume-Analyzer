import streamlit as st
import tempfile

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate

# -------------------- CONFIG --------------------
st.set_page_config(page_title="AI PDF Assistant", layout="wide")

# -------------------- VECTOR DB --------------------
@st.cache_resource
def create_vector_db(pdf_path):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(
        api_key=st.secrets["OPENAI_API_KEY"]
    )

    vectorstore = FAISS.from_documents(chunks, embeddings)
    return vectorstore


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def get_prompt():
    return ChatPromptTemplate.from_template("""
Answer only from the context below.

Context:
{context}

Question: {question}
""")

# -------------------- SESSION --------------------
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -------------------- SIDEBAR --------------------
with st.sidebar:
    st.title("Upload PDF")

    uploaded_file = st.file_uploader("Choose PDF", type="pdf")

    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            path = tmp.name

        with st.spinner("Processing..."):
            st.session_state.vectorstore = create_vector_db(path)

        st.success("PDF Ready")

    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

# -------------------- MAIN --------------------
st.title("📄 AI PDF Assistant")

if not st.session_state.vectorstore:
    st.info("Upload a PDF to start")

query = st.chat_input("Ask something...")

if query:
    if not st.session_state.vectorstore:
        st.warning("Upload PDF first")
    else:
        st.session_state.chat_history.append(("user", query))

        retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(query)

        context = format_docs(docs)
        prompt = get_prompt()

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=st.secrets["OPENAI_API_KEY"]
        )

        with st.spinner("Thinking..."):
            response = llm.invoke(prompt.format(context=context, question=query))
            answer = response.content

        st.session_state.chat_history.append(("bot", answer))

# -------------------- DISPLAY --------------------
for role, msg in st.session_state.chat_history:
    if role == "user":
        st.write(f"🧑 {msg}")
    else:
        st.write(f"🤖 {msg}")
