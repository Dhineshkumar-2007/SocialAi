# Societal Challenge Intelligence Platform — AI MVP

End-to-end Flask MVP based on the SIH concept:

Submit → Evidence → Classify → Embed → Duplicate → Skills → Priority → University Match → Project Tracking → Dashboard

## Stack
- Flask + Flask-CORS
- PostgreSQL + PostGIS + pgvector (production)
- SQLite fallback (local demo; vector search uses NumPy)
- BGE-small-en-v1.5 embeddings
- DeBERTa-v3-base zero-shot classification
- BLIP image captioning for evidence
- HDBSCAN optional clustering
- XGBoost optional priority model; rules are used until a trained model exists

## Run

### 1. Create environment
Windows:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Demo mode
No database is required:
```bash
python app.py
```

Open http://localhost:5000

The app automatically creates SQLite tables and seeds sample universities.

### 3. PostgreSQL mode
Set DATABASE_URL:
```text
DATABASE_URL=postgresql://postgres:password@localhost:5432/societal_ai
```
Then install PostgreSQL extensions:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
```

## AI models
Models are loaded lazily on first use. The first AI request downloads model weights from Hugging Face and needs internet.

- Embedding: BAAI/bge-small-en-v1.5
- Classification: MoritzLaurer/deberta-v3-base-zeroshot-v2.0
- Evidence captioning: Salesforce/blip-image-captioning-base

Set `AI_ENABLED=false` to run API/database without loading models.

## Main API
POST `/api/problems`
GET `/api/problems`
GET `/api/problems/<id>`
POST `/api/problems/<id>/analyze`
GET `/api/problems/<id>/matches`
POST `/api/universities`
GET `/api/universities`
POST `/api/projects`
PATCH `/api/projects/<id>`

See `docs/API.md`.
