# Mushu Kwok AI

A full-stack RAG chatbot that brings my real-life dog, Mushu, to life through AI. Built end-to-end from the vector database to the deployed frontend.

## What it does

Chat with Mushu, my real life Schnoodle dog! The chatbot uses Retrieval-Augmented Generation (RAG) to ground responses in real facts about Mushu, while a custom system prompt gives him a consistent personality.

## Tech Stack

- **Frontend:** Next.js, Tailwind CSS
- **Backend:** FastAPI (Python), streaming responses via SSE
- **LLM:** Groq API (Llama 3.1 8B)
- **RAG:** ChromaDB with ONNX embeddings (all-MiniLM-L6-v2)
- **Deployment:** Vercel (frontend) + Railway (backend)

## Architecture

1. Source documents about Mushu are chunked and embedded into a ChromaDB vector store via `ingest.py`
2. On each user message, the backend retrieves the most relevant chunks via similarity search
3. Retrieved context + a persona-engineered system prompt are passed to the Groq LLM
4. Tokens stream back to the frontend in real time via Server-Sent Events

## Key Decisions

- **ONNX over HuggingFace/torch** for embeddings, reducing Docker image size from 5.7GB to under 1GB for Railway deployment
- **Groq over local Ollama** to enable cloud deployment without GPU hosting costs
- **Streaming SSE** for better UX over waiting for full responses on a slow model
