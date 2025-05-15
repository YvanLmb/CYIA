import os
import streamlit as st
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from postgres import connect_db
from launch import authenticate_gmail,monitor_inbox


# Configurer Streamlit
st.set_page_config(page_title="CYIA Email RAG", page_icon="📧", layout="centered")
st.title("📧 CYIA Assistant Mail")
st.markdown("Pose ta question sur tes emails 📬")

# LLM
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-3.5-turbo",
    temperature=0.5
)

# --- Chargement des emails depuis PostgreSQL ---
def fetch_documents():
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT subject, body, sender, received_at, category FROM emails;")
        rows = cur.fetchall()
        docs = []
        for subject, body, sender, received_at, category in rows:
            content = f"Sujet : {subject or 'Sans sujet'}\nCorps : {body or ''}"
            metadata = {
                "subject": subject or "Sans sujet",
                "sender": sender or "Inconnu",
                "received_at": str(received_at),
                "category": category or "autres"
            }
            docs.append(Document(page_content=content, metadata=metadata))
        cur.close()
        conn.close()
        return docs
    except Exception as e:
        st.error(f"❌ Erreur récupération emails : {str(e)}")
        return []

# --- Création du vectorstore avec cache ---
@st.cache_resource
def load_vectorstore():
    docs = fetch_documents()
    if not docs:
        return None
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", ".", " "])
    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    vectorstore.persist()
    return vectorstore

# --- Initialiser vectorstore ---
vectorstore = load_vectorstore()
if vectorstore is None:
    st.stop()

# --- Chaîne RAG avec Retrieval MMR ---
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 8, "lambda_mult": 0.7}
    ),
    return_source_documents=True
)


# Interface utilisateur avec historique de chat
if "history" not in st.session_state:
    st.session_state.history = []

question = st.text_input(
    "Posez une question sur vos emails :",
    placeholder="Ex. Quels sont les thèmes principaux abordés dans mes e-mails ?"
)

if st.button("Obtenir la réponse") and question.strip():
    with st.spinner("Analyse en cours..."):
        try:
            response = qa_chain({"query": question})
            st.session_state.history.append({
                "question": question,
                "answer": response["result"]
            })
        except Exception as e:
            st.error(f"Erreur lors du traitement de la question : {str(e)}")

# Affichage de l'historique
for i, entry in enumerate(st.session_state.history[::-1], 1):
    st.markdown(f"**Vous :** {entry['question']}")
    st.markdown(f"**🤖 CYIA :** {entry['answer']}")

service = authenticate_gmail(user_id="yvan")
monitor_inbox(service, check_interval=60)  # Vérifie toutes les 60 secondes