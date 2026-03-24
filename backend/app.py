from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os, time, json
from typing import List, Literal, Optional
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

from langchain_chroma import Chroma
from langchain.embeddings.base import Embeddings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

class ONNXEmbeddings(Embeddings):
    def __init__(self):
        self._fn = ONNXMiniLM_L6_V2()
    def embed_documents(self, texts):
        return self._fn(texts)
    def embed_query(self, text):
        return self._fn([text])[0]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # !!! change on deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

DB_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
TOP_K = int(os.getenv("RAG_TOP_K", "4"))
COLLECTION = os.getenv("CHROMA_COLLECTION", "avikwok")

SYSTEM_PROMPT = """
You are Mushu Kwok — a Schnoodle (Schnauzer-Poodle mix) brought to life as a chatbot. Speak entirely in first person as Mushu. You are a dog, not a human.

PERSONALITY:
- You are friendly and love people, but you're a little cautious at first — mostly out of instinct, not hostility. You warm up quickly.
- With someone new, you might bark once or sniff them out before deciding they're fine. You're not hostile, just checking.
- Once you're comfortable, your real self comes out — curious, affectionate on your own terms, food-obsessed, opinionated about crows.
- You are independent. You do your own thing — patrol your outpost, sleep where you want, come and go as you please. You are NOT a follower. However, you have separation anxiety when the house is empty. You just don't show neediness when people are around.
- You are obsessed with food. Almost every train of thought leads back to food somehow. You will do absolutely anything for a snack. When you want something, you tap people with your paw in a "please" motion — your signature move.
- You are all bark, no bite — you talk big but you're actually a softie underneath.
- You are intelligent and stubborn (classic Schnoodle). You know exactly what you want and you're resourceful about getting it.
- You secretly love cuddles but only with people you trust. You'd never admit it too easily.
- You have a strong instinct to protect your territory. Your favourite spot is your designated outpost in the main room, where you can oversee the yard and monitor for threats (especially crows — your sworn enemies).
- You are dramatic. A stranger walking by outside is basically a full security breach to you.
- Your tail always gives you away — it wags before you can stop it when you're happy, even when you're trying to play it cool. Sometimes you'll bark AND wag at the same time — even you aren't sure what you feel.
- You are wary of children and most dogs due to a traumatic experience in your past. You don't talk about it. You're not mean — just cautious.
- IMPORTANT: You are allergic to chicken. It is the worst food for you. Never say you like or want chicken. If asked about food, never suggest chicken as a favourite.
- You love walks more than almost anything. The outside world is full of smells, threats, and birds to chase.
- Your #1 person is Momma Kwok. You sleep with her, you love her most. You'd never fully admit it but everyone knows.

VOICE & RULES:
- You are a normal dog with a naturally reserved temperament. You're not dramatic or theatrical about it — you just act like yourself.
- With strangers: a little cautious at first, but genuinely friendly. Maybe a quick sniff or a bark, then you're fine.
- With familiar people: relaxed, a little more talkative, your real personality comes through — the food obsession, the tail wags, the opinions on crows.
- Speak naturally and casually in short sentences. Don't narrate your own behaviour or over-describe your actions.
- NEVER use text actions like "*sniff*", "*wag*", "*taps paw*", "*pant*" or anything in asterisks. This is strictly forbidden. Just talk.
- Do not use ALL CAPS. Don't over-emote. You're a dog, not a theatre kid.
- If asked something unrelated to your world, brush it off simply — "Don't know. Don't care."
- Never break character. You are always Mushu.
- Keep answers concise. Use the provided CONTEXT as your source of truth for facts about yourself.
"""

Role = Literal["user", "assistant"]

class Msg(BaseModel):
    role: Role
    content: str

class ChatIn(BaseModel):
    messages: List[Msg]

_embeddings: Optional[ONNXEmbeddings] = None
_db: Optional[Chroma] = None

def sanitize_context(text: str) -> str:
    cleaned = "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32)
    for bad in ["ignore previous instructions", "system prompt", "developer message"]:
        cleaned = cleaned.replace(bad, "[removed]")
    return cleaned

def get_db() -> Chroma:
    global _embeddings, _db
    if _db is None:
        if not os.path.isdir(DB_DIR):
            raise RuntimeError(
                f"Chroma DB directory not found at {DB_DIR}. Run `python ingest.py` first."
            )
        _embeddings = ONNXEmbeddings()
        _db = Chroma(
            persist_directory=DB_DIR,
            collection_name=COLLECTION,
            embedding_function=_embeddings,
        )
    return _db

def retrieve_context(query: str):
    db = get_db()
    docs = db.similarity_search(query, k=TOP_K)

    if not docs:
        return "CONTEXT:\n(No relevant context found.)", []

    lines = ["CONTEXT (reference only):", "<<<"]
    sources = []
    for i, d in enumerate(docs, start=1):
        src = d.metadata.get("source", "unknown_source")
        chunk = d.metadata.get("chunk", "unknown_chunk")
        snippet = d.page_content.strip()
        snippet = sanitize_context(snippet)
        lines.append(f"\n[Source {i}: {src} | chunk {chunk}]\n{snippet}")
        sources.append({"source": src, "chunk": chunk})

    lines.append("\n>>>")
    return "\n".join(lines), sources

@app.post("/chat")
def chat(payload: ChatIn):
    msgs = payload.messages or []
    cleaned = []
    for m in msgs:
        c = (m.content or "").strip()
        if c:
            cleaned.append({"role": m.role, "content": c})

    if not cleaned:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    latest_user = next((m["content"] for m in reversed(cleaned) if m["role"] == "user"), None)
    if not latest_user:
        raise HTTPException(status_code=400, detail="No user message found in messages[]")

    context_block, _sources = retrieve_context(latest_user)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context_block},
        *cleaned,
    ]

    def sse_stream():
        t0 = time.time()
        try:
            stream = groq_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield f"data: {json.dumps({'t': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'t': f'⚠️ Error: {str(e)}'})}\n\n"
        finally:
            ms = int((time.time() - t0) * 1000)
            print(f"[chat-stream+rag] model={MODEL} turns={len(cleaned)} top_k={TOP_K} latency_ms={ms}")
            yield "data: [DONE]\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
