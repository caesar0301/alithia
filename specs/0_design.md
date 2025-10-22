# Alithia Research Agent Design Specification

## Overview

This document outlines the design for a LangGraph-based agent system that replicates the functionality of the zotero-arxiv-daily project using an agentic architecture. The system maintains all existing features while providing a more modular, extensible, and intelligent approach to academic paper recommendation.

## Current System Analysis

### Original zotero-arxiv-daily Architecture
The existing system follows a linear pipeline:
1. **Data Collection**: Fetch papers from Zotero corpus + ArXiv RSS feed
2. **Filtering**: Apply gitignore-style patterns to exclude collections
3. **Reranking**: Use sentence embeddings to score papers against user's corpus
4. **Content Generation**: Generate TLDR summaries using LLM
5. **Email Construction**: Format and send daily digest

### Key Components
- `main.py`: Orchestrates the entire workflow
- `paper.py`: ArxivPaper class with metadata extraction and TLDR generation
- `recommender.py`: Sentence embedding-based paper reranking
- `llm.py`: LLM interface (OpenAI API or local Llama)
- `construct_email.py`: Email formatting and delivery

## New Agent-Based Architecture

### Core Design Principles
- **Modularity**: Each functionality is encapsulated in separate agent nodes
- **State Management**: Centralized state management using LangGraph StateGraph
- **Extensibility**: Easy to add new agents or modify existing ones
- **LLM Integration**: Uses `cogents_core.llm` module instead of custom LLM implementation
- **Feature Parity**: Maintains all existing functionality without adding new features

### Agent State Structure

```python
@dataclass
class AgentState:
    # User Profile
    user_profile: ResearchProfile
    research_interests: List[str]
    expertise_level: str
    
    # Discovery State
    discovered_papers: List[ArxivPaper]
    discovery_sources: Dict[str, float]
    zotero_corpus: List[Dict[str, Any]]
    
    # Assessment State
    scored_papers: List[ScoredPaper]
    relevance_feedback: List[Feedback]
    
    # Content State
    generated_content: Optional[EmailContent]
    summarization_style: str
    
    # Communication State
    delivery_channels: List[str]
    user_engagement: Dict[str, float]
    
    # System State
    current_step: str
    error_log: List[str]
    performance_metrics: Dict[str, float]
    
    # Configuration
    config: Dict[str, Any]
```

### Data Models

#### ResearchProfile
- User ID and research interests
- Expertise level and language preferences
- Maximum papers per day and ignore patterns

#### ArxivPaper
- Title, summary, authors, ArXiv ID
- PDF URL, code URL, affiliations
- TLDR summary and relevance score

#### ScoredPaper
- Paper with relevance score
- Relevance factors breakdown

#### EmailContent
- HTML content and subject
- List of scored papers

### Agent Nodes Design

#### 1. Profile Analysis Node
**Purpose**: Initialize and analyze user research profile
**Input**: User configuration (Zotero ID, API key, preferences)
**Output**: Populated user profile and research interests
**Functionality**:
- Extract research interests from Zotero corpus
- Set up user preferences and ignore patterns
- Initialize research profile

#### 2. Data Collection Node
**Purpose**: Fetch papers from ArXiv and Zotero
**Input**: ArXiv query and Zotero credentials
**Output**: Discovered papers and Zotero corpus
**Functionality**:
- Fetch papers from ArXiv RSS feed
- Retrieve Zotero corpus
- Apply ignore patterns to filter collections

#### 3. Relevance Assessment Node
**Purpose**: Score papers based on relevance to user's research
**Input**: Discovered papers and Zotero corpus
**Output**: Scored papers with relevance scores
**Functionality**:
- Use sentence embeddings for similarity scoring
- Apply time decay weighting
- Rank papers by relevance score

#### 4. Content Generation Node
**Purpose**: Generate TLDR summaries and email content
**Input**: Scored papers
**Output**: Generated email content with TLDR summaries
**Functionality**:
- Generate TLDR summaries using cogents_core.llm
- Extract affiliations and code URLs
- Format email HTML content

#### 5. Communication Node
**Purpose**: Send email with recommendations
**Input**: Generated email content and SMTP configuration
**Output**: Email delivery confirmation
**Functionality**:
- Send HTML email via SMTP
- Handle email delivery errors
- Log delivery status

### Workflow Graph

```python
def create_research_agent_graph():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("profile_analysis", profile_analysis_node)
    workflow.add_node("data_collection", data_collection_node)
    workflow.add_node("relevance_assessment", relevance_assessment_node)
    workflow.add_node("content_generation", content_generation_node)
    workflow.add_node("communication", communication_node)
    
    # Define linear workflow
    workflow.add_edge("profile_analysis", "data_collection")
    workflow.add_edge("data_collection", "relevance_assessment")
    workflow.add_edge("relevance_assessment", "content_generation")
    workflow.add_edge("content_generation", "communication")
    
    return workflow.compile()
```

### Key Differences from Original

#### LLM Integration
- **Original**: Custom LLM wrapper in `llm.py`
- **New**: Uses `cogents_core.llm` module
- **Benefit**: Standardized LLM interface, better error handling

#### State Management
- **Original**: Global variables and function parameters
- **New**: Centralized state management with LangGraph
- **Benefit**: Better debugging, state persistence, workflow visualization

#### Modularity
- **Original**: Monolithic main function
- **New**: Separate agent nodes with clear responsibilities
- **Benefit**: Easier testing, maintenance, and extension

#### Error Handling
- **Original**: Basic try-catch blocks
- **New**: Structured error logging in state
- **Benefit**: Better error tracking and recovery

### Implementation Plan

#### Phase 1: Core Infrastructure
1. Set up project structure under `alithia/` folder
2. Implement state management and data models
3. Create basic agent nodes with mock implementations

#### Phase 2: Feature Implementation
1. Implement data collection node (ArXiv + Zotero)
2. Implement relevance assessment node (sentence embeddings)
3. Implement content generation node (TLDR + email formatting)
4. Implement communication node (SMTP email)

#### Phase 3: Integration
1. Connect all nodes in workflow graph
2. Add configuration management
3. Implement error handling and logging
4. Add tests and documentation

### Configuration

The system will accept the same configuration parameters as the original:
- Zotero credentials (ID, API key)
- ArXiv query string
- SMTP settings for email delivery
- LLM configuration (API key, model, language)
- Paper limits and ignore patterns

### Mock Features

The following features will be implemented as mock logic initially:
- User feedback processing
- Performance metrics tracking
- Multi-channel delivery
- Adaptive learning
- Research analytics

### Benefits of New Architecture

1. **Maintainability**: Clear separation of concerns
2. **Testability**: Each node can be tested independently
3. **Extensibility**: Easy to add new features or modify existing ones
4. **Debugging**: Better visibility into workflow execution
5. **Scalability**: Can easily add parallel processing or caching
6. **Standardization**: Uses established LangGraph patterns

### Migration Strategy

The new system will be implemented alongside the existing one, allowing for:
- Gradual migration of users
- A/B testing of new vs old system
- Rollback capability if issues arise
- Feature parity validation

This design maintains all existing functionality while providing a foundation for future enhancements and better system architecture.
