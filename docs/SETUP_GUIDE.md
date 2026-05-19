# TravelChatBot: Environment Setup & Developer Tutorial

Welcome to the developer setup guide! This tutorial will walk you through setting up your environment variables, preparing the Python environment, installing standard dependencies, performing database vector indexing, and verifying both the pipeline and backend REST API.

---

## 📋 Environment Variables Reference

TravelChatBot loads its configuration dynamically from `.env` located inside the core models package (`ai_module/models/.env`).

Below is the list of parameters supported by the system:

| Variable | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| **`API_KEY`** | Google Gemini API credentials. (Required to call the GenAI pipeline). | `"AIzaSyAY4..."` |
| **`MODELS`** | The primary text reasoning and synthesis LLM. | `"models/gemma-4-31b-it"` |

> [!TIP]
> **Gemini API Key:** You can obtain your API key for free from the [Google AI Studio Console](https://aistudio.google.com/).

---

## 🛠️ Step-by-Step Environment Setup Tutorial

Follow these structured steps to set up and run the project locally on your system.

### Step 1: Create a Python Virtual Environment
Initialize a fresh Python virtual environment using Python 3.10+ to isolate package dependencies:
```powershell
# Create virtual environment in '.venv' folder
python -m venv .venv

# Activate the virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate
```

### Step 2: Install Project Dependencies
Install the required libraries (including the Google GenAI SDK, FastAPI server, SQLAlchemy, and ChromaDB):
```powershell
pip install -r requirements.txt
```

### Step 3: Configure your Environment File (`.env`)
Create or edit the environment configuration file inside `ai_module/models/.env`.
```ini
# ai_module/models/.env

# The primary reasoning model (Gemma 4 31B)
MODELS="models/gemma-4-31b-it"

# Paste your Gemini API key here
API_KEY="AIzaSyYourGeminiApiKeyHere"
```

---

## 🚀 Database Initial Ingestion

TravelChatBot uses a self-bootstrapping database mechanism. You do not need to run manual ingestion scripts!
* **How it works:** Upon the very first query execution (or backend startup), the orchestrator automatically detects if the ChromaDB vector collection is empty.
* **Auto-Ingestion:** If empty, it programmatically chunks and indexes the **13,275 crawled items** from `data/processed/preprocessed_data.jsonl` into the vector database.
* **Overwrites/Updates:** The database uses deterministic cryptographic hashing for document IDs to avoid duplicates across restarts.

---

## 🧪 Verifying the Setup

We have prepared automated verification scripts so you can test that your virtual environment and model connections are functional.

### 1. Verify a Single RAG Pipeline Query
Run the single query test to confirm the coordinator parses query text, searches ChromaDB, and successfully generates a travel itinerary:
```powershell
python qa_ba/test/verify_single.py
```
* **Success Indicator:** The script should output a structured markdown travel itinerary regarding *VinWonders Nha Trang* in Vietnamese, powered by the dynamic Gemma/Gemini fallback client.

### 2. Verify REST API Endpoint Functions
Run the API endpoint test suite to confirm that session creation, user authentication, and multi-agent coordination are intact:
```powershell
python qa_ba/test/test_chat_api.py
```
* **Success Indicator:** The script will output `API test module completed successfully.`

### 3. Verify Per-User Rate Limiting Auth
Verify that the sliding-window rate limiter blocks requests above the 15 requests/minute threshold:
```powershell
python qa_ba/test/test_rate_limiter.py
```
* **Success Indicator:** The script will confirm that the 16th request returns a clean `HTTP 429` status code and a dynamic `Retry-After` header.

---

## 🌐 Launching the REST API Backend Server

Once all tests pass, you can start the REST backend to serve frontend clients:
```powershell
# Run the FastAPI server in hot-reload mode
python backend/main.py
```
* **API Address:** The server starts locally at `http://localhost:8000`.
* **Swagger Interactive Docs:** Visit `http://localhost:8000/docs` in your browser to interactively test all endpoints (authentication, users, chat sessions, RAG messaging) directly!
