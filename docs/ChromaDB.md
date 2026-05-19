# ChromaDB Vector Database & Ingestion Engine

TravelChatBot utilizes **ChromaDB** as its high-performance vector search engine to implement the Retrieval-Augmented Generation (RAG) pipeline. This database stores semantic text embeddings of travel destinations, spots, and articles, supporting ultra-fast similarity searches.

---

## 📂 Ingestion Data Flow

The database is built dynamically from the raw dataset. On initialization, the system checks if the vector collection contains records. If empty, the ingestion process is triggered:

```mermaid
graph TD
    RAW[data/raw/raw.jsonl] --> PRE[Preprocess (clean + enrich)]
    PRE --> CLEAN[data/processed/preprocessed_data.jsonl]
    CLEAN --> Parser[Line-by-Line JSONL Parser]
    Parser --> Keypoints[Slices Keypoint Articles]
    Keypoints --> StripIMG[Strips '[img]...[img]' Tags for embedding]
    StripIMG --> Metadata[Enriches Metadata Fields]
    Metadata --> Vectorizer[Generates Semantic Embeddings]
    Vectorizer --> ChromaDB[(ChromaDB collection)]
```

For the preprocessing commands and dataset schema, see `docs/DataPipeline.md`.

---

## 📊 Database Schema & Metadata Enrichment

Every destination article in `data/raw/raw.jsonl` contains multiple travel spots (referred to as `keypoints`). Each spot is ingested as a separate database document with the following enriched metadata:

| Metadata Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Unique combination of article ID and keypoint index (`{article_idx}_keypoint_{keypoint_idx}`). |
| `title` | `str` | Name of the tourist spot or hotel. |
| `context` | `str` | Detailed descriptive text about the spot (excluding HTML image tags). |
| `destination` | `str` | Resolved parent city/destination (e.g., `"Nha Trang"`, `"Phú Quốc"`, `"Hạ Long"`). |
| `time` | `float` | Published epoch timestamp (e.g., `1779136000.0`). |
| `evaluate_mean` | `float` | Average traveler rating (on a scale of `1.0` to `5.0`). |
| `evaluate_count`| `int` | Total number of reviews submitted by travelers. |
| `images` | `str` | Stringified JSON array of all local absolute paths to images belonging to this spot. |

---

## ⚡ Custom Post-Retrieval Sorting

While vector search retrieves matching spots based on semantic cosine similarity, user queries often request specific orderings (e.g., *"newest spots"*, *"best-rated resorts"*, or *"most reviewed attractions"*). 

To achieve this, `RetrievalAgent` supports **programmatic search sorting**:

1.  **ChromaDB Search**: Performs a semantic L2 search to retrieve top candidate documents (e.g., `top_k=20`).
2.  **Metadata Slicing**: Slices and parses the returned metadata objects.
3.  **Programmatic Sorting**: Sorts the candidates in-memory based on the designated parameter:
    *   `sort_by="time"`: Sorts by published epoch timestamp.
    *   `sort_by="evaluate_mean"`: Sorts by average traveler rating.
    *   `sort_by="evaluate_count"`: Sorts by total review count.
4.  **Order Selection**: Organizes results in either descending (`"desc"`) or ascending (`"asc"`) orders.
5.  **Context Assembly**: Selects the top sorted candidates to compose the contextual recommendation prompt.
