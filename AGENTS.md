# Alithia Researcher - Coding Agent Specification

## Project Overview

This project, `alithia`, is a personal academic research agent. It is designed to provide daily paper recommendations from ArXiv based on a user's research profile. The agent is built using Python and leverages the LangGraph framework to create a workflow for discovering, assessing, and delivering relevant academic papers.

The core technologies used in this project include:

*   **Python**: The primary programming language.
*   **Poetry**: For dependency management.
*   **LangGraph**: To structure the agent's workflow.
*   **ArXiv API**: To search for new academic papers.
*   **Zotero API**: To access the user's existing research library for context.
*   **scikit-learn & sentence-transformers**: For machine learning tasks, likely related to paper scoring and relevance assessment.
*   **OpenAI API**: For leveraging large language models, probably for summarization or content generation.
*   **Pinecone & Supabase**: For vector storage and database functionalities, respectively.

The agent's workflow is divided into the following main steps:

1.  **Profile Analysis**: The agent starts by analyzing the user's research profile to understand their interests.
2.  **Data Collection**: It then queries ArXiv for new papers and fetches the user's Zotero library for context.
3.  **Relevance Assessment**: The discovered papers are scored for relevance based on the user's profile.
4.  **Content Generation**: An email is crafted with the most relevant papers.
5.  **Communication**: The email is sent to the user.

## Engineering Rules and Constraints

### Global Constraints

- **PRD compliance**: All designs and implementations must align with `specs/prd.md`.
- **Language**: Python only.
- **Orchestration**: Use LangGraph for agent workflows.
- **CLI**: Use Typer for CLI entrypoints.

### Agents and Scope

- **Agents**: `vigil`, `arxrec`, `lens` live under `alithia/agents/<agent_name>`.
- **Core**: Shared modules must reside under `alithia/core` and be reused by all agents.
- **Scope control**: Do not implement features outside the targeted agent unless explicitly requested. Avoid adding unrelated modules, services, or tests when not requested.

### PDF Processing

- **Library**: Use MinerU for PDF parsing/segmentation.
- **Abstraction**: Provide a wrapper in `alithia/core/pdf_processor.py` that returns structured text chunks (id, text, page, offset). Encapsulate import differences across MinerU versions.
- **Input**: Support local PDF paths at minimum; optional fetchers (arXiv/DOI/title) can be layered on top.

### Embeddings and Reranking

- **Embeddings**: Use `sentence-transformers` for all text embeddings.
- **Reranking**: Use `sentence-transformers` CrossEncoder-based rerankers for query-aware ranking.
- **Defaults**:
  - Embedding model default: `mixedbread-ai/mxbai-embed-large-v1` (configurable).
  - Reranker default: `cross-encoder/ms-marco-MiniLM-L-6-v2` (configurable).
- **Normalization**: Normalize embeddings to unit length before vector upsert and similarity search.

### Storage and Persistence

- **Vector storage**: Use Pinecone exclusively for vector similarity search.
  - Environment: `PINECONE_API_KEY` (required), `PINECONE_INDEX`, `PINECONE_NAMESPACE`.
  - Implement a reusable client in `alithia/core/vector_store.py` with upsert/query helpers.
- **Table storage**: Use Supabase exclusively for relational/metadata tables.
  - Environment: `SUPABASE_URL` (required), `SUPABASE_ANON_KEY` (required).
  - Provide helpers in `alithia/core/table_store.py` for document/chunk metadata CRUD.
- **No alternate stores**: Do not introduce other DBs/vector stores unless explicitly approved.

### LLMs and Tooling

- **LLM client**: Use `cogents_core.llm.get_llm_client` via a helper in `alithia/core/llm_utils.py`.
- **Provider**: Default to OpenAI provider; model configurable via profile/config.
- **Usage**: Generate answers/summaries using `llm.generate(messages=[...])` with system/user roles.
- **Tools**: Do not implement a custom tool base class. All tools must subclass `langchain_core.tools.BaseTool` and declare a `args_schema` pydantic model for inputs. Optional `execute()` helpers are allowed for internal usage.

### Configuration and Environment

- **Environment file**: Keep `env.example` authoritative for required variables.
- **New env vars (used across agents)**:
  - Pinecone: `PINECONE_API_KEY`, `PINECONE_INDEX`, `PINECONE_NAMESPACE` (optional)
  - Supabase: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_DOC_TABLE` (default `lens_documents`), `SUPABASE_CHUNK_TABLE` (default `lens_chunks`)
- **Profiles**: Reuse `alithia/core/profile.py` as the primary configuration model. Extend cautiously and keep backward compatible keys.

### Code Structure and Style

- **Directory layout**: Follow structure in `specs/prd.md`.
- **Common modules**: Place shared utilities in `alithia/core` and reuse across agents (PDF parsing, embeddings, vector/table stores, LLM utils).
- **Imports**: Agents should import from `alithia/core/*` for shared logic.
- **Code style**: Follow the repository's formatting and typing discipline (pydantic models, explicit types for public APIs, early returns, minimal nesting).
- **Data models**: Implement data models based on pydantic library instead of dataclasses.
- **Pydantic optimization**: Avoid creating redundant `from_config` or similar factory methods that simply pass dictionary values to the model constructor. Use Pydantic's built-in functionality: `ModelClass(**config)` instead of `ModelClass.from_config(config)`. This eliminates code duplication and leverages Pydantic's native validation and type conversion.

### Testing and Ops

- **Tests**: Do not add or run tests unless explicitly requested. Place unittests under folder `tests/unit` and integration under `tests/integration`.
- **Runtime**: Assume non-interactive execution for internal steps; CLI must be user-friendly.
- **Run tests**: `make test-unit` for unit tests. `make test-integration` for integration tests which are marked by `pytest.mark.integration`.

### Compatibility and Backwards Safety

- **Non-breaking edits**: Maintain compatibility with existing CLI commands and public method signatures unless the change is explicitly approved.
- **Resilience**: Handle missing/invalid configs with clear errors; avoid silent failures.
- **Performance**: Batch embeddings and vector upserts where possible; avoid excessive network round-trips.

## Building and Running

This project uses a `Makefile` that provides a convenient way to manage common tasks.

### Installation

To install the project dependencies, run:

```bash
make install
```

For development, you can install the development dependencies with:

```bash
make install-dev
```

### Running the Agent

The project defines three entry points in the `pyproject.toml` file: `arxrec`, `vigil`, and `lens`. To run the main agent, you can use the `arxrec` script:

```bash
poetry run arxrec
```

You will likely need to set up your environment variables in a `.env` file (based on `env.example`) to configure the agent with your API keys and preferences.

### Running Tests

To run the test suite, use the following command:

```bash
make test
```

You can also run unit and integration tests separately:

```bash
make test-unit
make test-integration
```

## Development Conventions

### Code Formatting

This project uses `black`, `isort`, and `autoflake` for code formatting. To format the code, run:

```bash
make format
```

To check if the code is properly formatted, run:

```bash
make format-check
```

### Linting

The project uses `flake8` for linting. To lint the code, run:

```bash
make lint
```

### Documentation

The documentation is built using Sphinx. To build the documentation, run:

```bash
make docs
```
