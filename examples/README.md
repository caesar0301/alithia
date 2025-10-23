# Alithia Examples

This directory contains examples demonstrating key components of the Alithia research recommendation system.

## FlashRank Reranking Demo

This example demonstrates how FlashRank is used to rerank papers based on semantic relevance to a user's research corpus.

### Running the Demo

```bash
python -m examples.flashrank_demo
```

Or with uv:
```bash
uv run python -m examples.flashrank_demo
```

This comprehensive example demonstrates:
- Complete reranking pipeline as used in `alithia/arxrec/recommender.py`
- Time-decay weighting for recent papers
- Scoring multiple candidate papers against a corpus
- Detailed relevance analysis

**Runtime:** ~30-60 seconds  
**Note:** Requires network connection to download the FlashRank model on first run

## How FlashRank Works in Alithia

### The Problem
When new papers appear on arXiv, we need to determine which ones are most relevant to a researcher's interests.

### The Solution
1. **Semantic Similarity:** FlashRank compares paper abstracts using transformer-based embeddings, capturing conceptual relevance beyond keyword matching
2. **Corpus-Based Ranking:** Each new paper is scored against the user's entire Zotero library
3. **Time Decay:** More recent papers in the corpus get higher weights, reflecting current research interests
4. **Aggregation:** Individual relevance scores are combined with time weights to produce a final ranking

### Why This Method is Valid

1. **Semantic Understanding:** Unlike keyword matching, FlashRank understands context and meaning
   - Example: "transformer architecture" and "self-attention mechanism" are semantically related even with different words

2. **Personalization:** Scoring against the user's actual corpus ensures recommendations match their specific research direction

3. **Recency Weighting:** Time decay prevents the system from over-emphasizing older, possibly outdated research interests

4. **Proven Model:** Uses `ms-marco-MiniLM-L-12-v2`, a model trained on Microsoft's MARCO dataset for passage ranking

## Code Reference

The production implementation is in:
```
alithia/arxrec/recommender.py → rerank_papers()
```

Key parameters:
- `model_name`: FlashRank model (default: "ms-marco-MiniLM-L-12-v2")
- `corpus`: User's Zotero library papers
- `papers`: Candidate papers from arXiv to rank

## Requirements

These examples are part of the Alithia package and use the same dependencies.

If you haven't installed Alithia yet:
```bash
pip install -e .
```

Or with uv:
```bash
uv pip install -e .
```

The examples will then work with the installed dependencies (`flashrank`, `numpy`, etc.)

## Further Reading

- [FlashRank Documentation](https://github.com/PrithivirajDamodaran/FlashRank)
- [MS MARCO Dataset](https://microsoft.github.io/msmarco/)
- Alithia design docs: `specs/0_design.md`, `specs/1_prd.md`
