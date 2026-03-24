# Mushu Kwok AI - Local RAG Chatbot (Ollama + FastAPI + Next.js)

This repository runs a local, end-to-end GenAI chatbot

---

## Requirements 

Install these before starting:

- **Docker + Docker Compose**
- **Node.js 18+**

---

Your folder structure should look like this:

├── backend/

│ ├── app.py

│ ├── ingest.py

│ ├── requirements.txt

│ ├── docker-compose.yml

│ └── source.txt

│

├── frontend/

│ ├── app/

│ ├── ├── layout.tsx

│ ├── ├── page.js

│ ├── ├── globals.css

│ ├── └── favicon.ico

│ ├── package.json

│ ├── package-lock.json

│ └── .env.example

│

├── .gitignore

└── README.md


---

## What the App Does

1. Text from `backend/source.txt` is ingested into a vector database (Chroma).
2. User messages are sent from the frontend to the FastAPI backend.
3. The backend retrieves relevant chunks (RAG).
4. Context + chat history are sent to a local Ollama model.
5. The response is **streamed token-by-token** back to the UI.

---

## Step 1 — Start the Backend (API + Ollama)

From the repository root:

```bash
cd backend
docker compose up -d

## FIRST TIME ONLY
docker compose exec ollama ollama pull phi3:mini
## FIRST TIME ONLY

Backend url:
http://localhost:8000


## Start the frontend
In a new terminal, from the repo root:
cd frontend
cp .env.example .env.local
npm install
npm run dev

Frontend URL: 
http://localhost:3000

To use the chatbot, open your browser to http://localhost:3000
