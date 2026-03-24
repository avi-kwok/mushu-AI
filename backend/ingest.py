import os
import shutil
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from langchain.embeddings.base import Embeddings

os.environ["ANONYMIZED_TELEMETRY"] = "False"

DOC_PATH = "./docs/avikwok.txt"
DB_DIR = "./chroma_db"
COLLECTION = "avikwok"

class ONNXEmbeddings(Embeddings):
    def __init__(self):
        self._fn = ONNXMiniLM_L6_V2()

    def embed_documents(self, texts):
        return self._fn(texts)

    def embed_query(self, text):
        return self._fn([text])[0]

def ingest_txt():
    if not os.path.exists(DOC_PATH):
        raise FileNotFoundError(f"Could not find {DOC_PATH}.")

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

    embeddings = ONNXEmbeddings()

    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)
    os.makedirs(DB_DIR, exist_ok=True)

    db = Chroma(
        collection_name=COLLECTION,
        persist_directory=DB_DIR,
        embedding_function=embeddings,
    )
    db.add_documents(chunks)

    print(f"Ingested {len(chunks)} chunks from {DOC_PATH} into {DB_DIR} (collection={COLLECTION})")

if __name__ == "__main__":
    ingest_txt()
