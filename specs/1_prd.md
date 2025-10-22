
Here’s the full PRD for the Alithia Multi-Agent Research Assistant 

# Alithia Multi-Agent Research Assistant — PRD

## 1. Product Vision
Alithia is a **multi-agent, AI-powered research companion** designed to cover the entire academic workflow — from **monitoring** new developments, to **recommending** relevant papers, to **deeply understanding** and interacting with them.

It is **modular, extensible, and future-proof**, with each agent performing a specialized role but sharing a common embedding-based knowledge store and user interest profile.

---

## 2. Agents Overview

### 2.1 AlithiaVigil — Proactive Topic Monitoring Agent
**Tagline:** *Never miss the signal.*

**Purpose:**  
Watches the research landscape for user-defined topics, tracking trends and surfacing relevant works.

**Key Features:**
- Multi-source scanning:
  - Academic: ArXiv, selected conferences, journal RSS feeds.
  - Media: Twitter/X, blogs, online magazines.
- Embedding-based relevance filtering for topic matching.
- Summarized trend reports (daily/weekly).
- Alerts via CLI, email, or Slack.
- (optional) Can automatically forward promising papers to **AlithiaLens** for deep reading.

### 2.2 AlithiaArxrec — Personalized ArXiv Recommendation Agent
**Tagline:** *Papers you actually want to read.*

**Purpose:**  
Recommends new ArXiv papers tailored to the user's research interests, inferred from their **Zotero library**.

**Key Features:**
- Syncs and parses Zotero library metadata.
- Builds and maintains a user interest embedding profile.
- Monitors selected ArXiv categories for new papers.
- Scores & ranks papers by similarity to the interest profile.
- Generates short summaries of top matches.
- Delivers results via email or CLI.
- (optional) Can send selected papers directly to **AlithiaLens** for in-depth analysis.

### 2.3 AlithiaLens — Deep Paper Interaction Agent
**Tagline:** *See through the paper.*

**Purpose:**  
Provides an interactive, semantic reading and analysis experience for academic papers.

**Key Features:**
- Input methods:
  - Local PDFs
  - DOI lookups
  - ArXiv IDs
  - Paper titles (auto-fetch via APIs)
- Semantic paragraph-level search and retrieval.
- Extracts references, builds citation graphs.
- Diagram/table analysis with OCR + vision LLM.
- Multi-paper comparison & synthesis.
- Metadata extraction: authors, affiliations, dataset/code links.
- Conversational Q&A in a **CLI interface**.

## 3. Shared Core Layer

### 3.1 Central Components
- **Config Manager**: Loads user API keys, preferences, scheduling options.
- **Vector Store**: Centralized database for embeddings of:
  - Papers processed by any agent.
  - User interest profile.
- **Interest Model**: Dynamically updated from:
  - Zotero sync (Arxrec)
  - Lens conversation history
  - Vigil topic interactions
- **LangGraph Orchestration**:
  - Manages modular workflows for each agent.
  - Allows optional chaining (e.g., Arxrec → Lens).
- **Common Utils**:
  - PDF parsing (PyMuPDF4LLM)
  - Diagram OCR (pytesseract + vision LLM)
  - Summarization
  - Rate-limit handling for APIs.
- **Cloud PaaS based for prototype**. use pinecone for vector store and supabase for table store.

## 4. Workflows

### 4.1 Discovery Layer
1. **AlithiaVigil**:
   - Runs scheduled topic scans.
   - Filters results based on embeddings.
   - Sends digest or triggers Lens for deep read.
2. **AlithiaArxrec**:
   - Fetches new ArXiv papers daily.
   - Scores based on Zotero-derived interest profile.
   - Sends ranked summaries.

### 4.2 Understanding Layer
- **AlithiaLens**:
  - Accepts papers from Vigil, Arxrec, or direct user input.
  - Enables deep, semantic conversation.
  - Updates interest model with usage patterns.

### 4.3 Feedback Loop
- Interactions with Lens and feedback on Vigil/Arxrec results are logged.
- Interest model embeddings are updated to improve future recommendations and monitoring accuracy.

## 5. Optimized Folder Structure
```plaintext
alithia/
├── core/           # Shared infrastructure (config, state, vector store, utils)
├── agents/         
│   ├── lens/       # AlithiaLens modules
│   ├── vigil/      # AlithiaVigil modules
│   ├── arxrec/     # AlithiaArxrec modules
│   └── common/     # Base agent, schedulers, shared helpers
├── cli/            # CLI entrypoints for each agent
├── tests/          # Unit/integration tests per module
└── docs/           # Architecture diagrams, user guides
```

## 6. Technical Stack

### Core Infrastructure
- **Orchestration:** LangGraph
- **Vector DB:** Pinecone / Weaviate
- **Embedding Models:** OpenAI `text-embedding-3-large` or local BGE models
- **LLMs:** OpenRouter Gemini Flash or Pro
- **PDF Parsing:** PyMuPDF, PyMuPDF4LLM
- **Diagram OCR:**  minerU + vision LLM
- **Scheduling:** APScheduler, Celery (for Vigil)
- **Alerting:** SMTP for email, Slack webhooks
- **CLI Framework:** Typer + Rich
- Impl in Python

## 7. Future Extensions
- **Collaborative Mode**: Share digests with research groups.
- **Integration with note-taking tools** (Obsidian, Notion).
- **Multi-language support** for papers and sources.
- **Offline mode** using local LLMs & embedding models.
