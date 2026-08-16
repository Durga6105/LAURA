LAURA

Legal AI Understanding & Risk Analyzer

LAURA is an AI-powered legal document analysis system that analyzes Non-Disclosure Agreements (NDAs), identifies risks and rule violations, applies corrections, re-validates the document, and generates an analysis report.

It also provides Ask LAURA, a context-aware assistant for asking follow-up questions about the completed NDA analysis.

Features

NDA upload — PDF and DOCX

Clause extraction and document ingestion

Rule Book validation

Risk identification

Automated NDA corrections

Re-validation after correction

PDF analysis report generation

Live analysis progress

Ask LAURA follow-up assistant

Corrected NDA and report downloads

Dark / Light mode

Architecture

User
  ↓
HTML Frontend
  ↓
FastAPI
  ├── Analysis API
  ├── Q&A API
  └── Health API
       ↓
Correction Workflow
  ├── NDA Ingestion
  ├── Rule Book Retrieval
  ├── Validation
  ├── Correction
  ├── Re-validation
  └── Report Generation
       ↓
ChromaDB + Gemini

Tech Stack

Python

FastAPI

HTML / CSS / JavaScript

Google Gemini

ChromaDB

Uvicorn

Setup

Clone the repository:

git clone https://github.com/Durga6105/LAURA.git
cd LAURA

Create a virtual environment:

python -m venv venv

Activate it on Windows:

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Create a .env file using .env.example and add your Gemini API key.

Run

Backend

uvicorn api.main:app --reload

Backend:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

Frontend

Open ui/index.html using VS Code Live Server.

API

POST /analysis/run — Start NDA analysis

GET /analysis/status/{analysis_id} — Get analysis progress

GET /analysis/download/{analysis_id}/corrected — Download corrected NDA

GET /analysis/download/{analysis_id}/report — Download analysis report

POST /qa/ask — Ask LAURA a question

Disclaimer

LAURA is an AI-assisted legal document analysis system and does not replace professional legal advice.

Author

Durga Prasad Peddimeni
