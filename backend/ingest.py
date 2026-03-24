import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

os.environ["ANONYMIZED_TELEMETRY"] = "False"

DOC_PATH = "./docs/avikwok.txt"
DB_DIR = "./chroma_db"
COLLECTION = "avikwok"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def ingest_txt():
    if not os.path.exists(DOC_PATH):
        raise FileNotFoundError(f"Could not find {DOC_PATH}. Make sure it exists.")

    with open(DOC_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        raise ValueError(f"{DOC_PATH} is empty.")

    doc = Document(page_content=text, metadata={"source": "avikwok.txt"})

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents([doc])

    for i, c in enumerate(chunks):
        c.metadata["chunk"] = i

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    os.makedirs(DB_DIR, exist_ok=True)


    db = Chroma(
        collection_name=COLLECTION,
        persist_directory=DB_DIR,
        embedding_function=embeddings,
    )


    try:
        db.delete(where={})
    except Exception:
        pass

    db.add_documents(chunks)

    if hasattr(db, "persist"):
        db.persist()

    print(f"Ingested {len(chunks)} chunks from {DOC_PATH} into {DB_DIR} (collection={COLLECTION})")

if __name__ == "__main__":
    ingest_txt()
