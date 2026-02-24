# Deployment Guide

## Important limitation
Cloud/serverless platforms are generally not suitable for bundled local GGUF models. For production, use:
- Hosted API model (`ANTHROPIC_API_KEY`), or
- A dedicated VM/GPU box for `LOCAL_LLM_MODEL_PATH`.

## Pre-deploy checklist
1. Rotate any previously exposed keys.
2. Do not commit `.env` (keep secrets in provider environment variables).
3. Set `ENVIRONMENT=production`.
4. Set strict CORS:
   - `CORS_ORIGINS=https://your-frontend-domain.com`
5. Decide vector backend:
   - Production: Pinecone configured.
   - Local-memory fallback is only for dev/smoke testing.

## Render (recommended for backend)
1. Create a new Render Blueprint deploy from this repo (`render.yaml` is included).
2. Set required env vars:
   - `PINECONE_API_KEY`
   - `PINECONE_ENVIRONMENT`
   - `PINECONE_INDEX_NAME`
3. Set one LLM path:
   - `ANTHROPIC_API_KEY`, or
   - `LOCAL_LLM_MODEL_PATH` (only if your Render instance has the model file mounted).
4. Set CORS:
   - `CORS_ORIGINS=https://your-frontend-domain.com`
5. Optional: deploy static frontend from same blueprint (`intelligent-document-assistant-web` service).
   - Set `VITE_API_BASE=https://your-api.onrender.com`

## Vercel (frontend)
1. Deploy the `frontend/` directory as a Vite project.
2. Set `VITE_API_BASE` to your backend URL, for example:
   - `https://your-api.onrender.com`
3. Build command: `npm run build`
4. Output directory: `dist`
5. SPA routing config is included at `frontend/vercel.json`.

## Local production-like run
```bash
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

## Optional local model install
```bash
pip install -r requirements.txt -r requirements-local-llm.txt
```
