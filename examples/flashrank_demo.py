"""
FlashRank Reranking Demonstration

This example demonstrates how FlashRank is used to rerank papers based on 
relevance to a user's research corpus. It shows:

1. How FlashRank compares paper abstracts against a corpus
2. The effect of time-decay weighting on older papers
3. How the reranking identifies the most relevant papers

The method used here mirrors the approach in alithia/arxrec/recommender.py
"""

from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
from flashrank import Ranker, RerankRequest


def create_sample_corpus() -> List[Dict[str, any]]:
    """
    Create a sample research corpus simulating Zotero papers.
    These papers are about machine learning and computer vision.
    """
    base_date = datetime.now()
    
    corpus = [
        {
            "data": {
                "title": "Attention Is All You Need",
                "abstractNote": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
                "dateAdded": (base_date - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        },
        {
            "data": {
                "title": "Deep Residual Learning for Image Recognition",
                "abstractNote": "We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions.",
                "dateAdded": (base_date - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        },
        {
            "data": {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "abstractNote": "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context.",
                "dateAdded": (base_date - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        },
        {
            "data": {
                "title": "Generative Adversarial Networks",
                "abstractNote": "We propose a new framework for estimating generative models via an adversarial process, in which we simultaneously train two models: a generative model G that captures the data distribution, and a discriminative model D that estimates the probability that a sample came from the training data rather than G.",
                "dateAdded": (base_date - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        },
        {
            "data": {
                "title": "Vision Transformer (ViT)",
                "abstractNote": "While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited. In vision, attention is either applied in conjunction with convolutional networks, or used to replace certain components of convolutional networks while keeping their overall structure in place.",
                "dateAdded": (base_date - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
    ]
    
    return corpus


def create_candidate_papers() -> List[Dict[str, str]]:
    """
    Create candidate papers to be reranked.
    Some are relevant to the corpus, others are not.
    """
    papers = [
        {
            "title": "Swin Transformer: Hierarchical Vision Transformer using Shifted Windows",
            "summary": "This paper presents a new vision Transformer, called Swin Transformer, that capably serves as a general-purpose backbone for computer vision. Challenges in adapting Transformer from language to vision arise from differences between the two domains, such as large variations in the scale of visual entities and the high resolution of pixels in images compared to words in text."
        },
        {
            "title": "Quantum Computing Applications in Drug Discovery",
            "summary": "We explore the potential of quantum computing for accelerating drug discovery processes. Our framework leverages quantum algorithms for molecular simulation and protein folding prediction, demonstrating significant speedups over classical approaches in specific pharmaceutical applications."
        },
        {
            "title": "Transformer-XL: Attentive Language Models Beyond a Fixed-Length Context",
            "summary": "Transformers have a potential of learning longer-term dependency, but are limited by a fixed-length context in the setting of language modeling. We propose a novel neural architecture Transformer-XL that enables learning dependency beyond a fixed length without disrupting temporal coherence."
        },
        {
            "title": "Agricultural Soil Analysis Using Traditional Methods",
            "summary": "This study investigates traditional soil analysis techniques for agricultural applications. We compare pH measurement methods, nutrient content assessment, and moisture retention properties across different soil types in various geographical regions, providing recommendations for sustainable farming practices."
        },
        {
            "title": "ConvNeXt: A ConvNet for the 2020s",
            "summary": "The 'Roaring 20s' of visual recognition began with the introduction of Vision Transformers (ViTs), which quickly superseded ConvNets as the state-of-the-art image classification model. We reexamine the design spaces and test the limits of what a pure ConvNet can achieve, gradually modernizing a standard ResNet toward the design of a vision Transformer."
        }
    ]
    
    return papers


def rerank_with_flashrank(
    candidate_papers: List[Dict[str, str]],
    corpus: List[Dict[str, any]],
    model_name: str = "ms-marco-MiniLM-L-12-v2"
) -> List[Dict[str, any]]:
    """
    Rerank candidate papers based on relevance to corpus.
    This mirrors the logic in alithia/arxrec/recommender.py
    
    Args:
        candidate_papers: Papers to be ranked
        corpus: User's research corpus
        model_name: FlashRank model to use
        
    Returns:
        List of papers with scores, sorted by relevance
    """
    if not candidate_papers or not corpus:
        return [{"paper": p, "score": 0.0} for p in candidate_papers]
    
    # Initialize FlashRank ranker
    print(f"Initializing FlashRank with model: {model_name}")
    ranker = Ranker(model_name=model_name, cache_dir="/tmp/flashrank_cache")
    
    # Sort corpus by date (newest first)
    sorted_corpus = sorted(
        corpus,
        key=lambda x: datetime.strptime(x["data"]["dateAdded"], "%Y-%m-%dT%H:%M:%SZ"),
        reverse=True
    )
    
    print(f"\nCorpus sorted by date (newest first):")
    for i, paper in enumerate(sorted_corpus):
        print(f"  {i+1}. {paper['data']['title']} ({paper['data']['dateAdded'][:10]})")
    
    # Calculate time decay weights
    time_decay_weight = 1 / (1 + np.log10(np.arange(len(sorted_corpus)) + 1))
    time_decay_weight = time_decay_weight / time_decay_weight.sum()
    
    print(f"\nTime decay weights (sum={time_decay_weight.sum():.4f}):")
    for i, weight in enumerate(time_decay_weight):
        print(f"  Position {i+1}: {weight:.4f}")
    
    # Prepare corpus abstracts as passages
    corpus_passages = [{"text": paper["data"]["abstractNote"]} for paper in sorted_corpus]
    
    # Score each candidate paper
    scored_papers = []
    
    print("\n" + "="*80)
    print("RERANKING CANDIDATE PAPERS")
    print("="*80)
    
    for idx, paper in enumerate(candidate_papers):
        print(f"\n[{idx+1}/{len(candidate_papers)}] Analyzing: {paper['title']}")
        print(f"Summary: {paper['summary'][:100]}...")
        
        # Create rerank request
        rerank_request = RerankRequest(
            query=paper["summary"],
            passages=corpus_passages
        )
        
        # Get reranking results
        results = ranker.rerank(rerank_request)
        
        # Calculate weighted scores
        weighted_scores = []
        print(f"\nRelevance to corpus papers:")
        
        for result in results:
            corpus_idx = result["corpus_id"]
            relevance_score = result["score"]
            weighted_score = relevance_score * time_decay_weight[corpus_idx]
            weighted_scores.append(weighted_score)
            
            corpus_title = sorted_corpus[corpus_idx]["data"]["title"]
            print(f"  - {corpus_title[:50]:50s} | "
                  f"Relevance: {relevance_score:6.4f} | "
                  f"Weight: {time_decay_weight[corpus_idx]:.4f} | "
                  f"Weighted: {weighted_score:.4f}")
        
        # Sum weighted scores and scale
        final_score = sum(weighted_scores) * 10
        
        print(f"\n  Total weighted score: {sum(weighted_scores):.4f}")
        print(f"  Final score (×10): {final_score:.4f}")
        
        scored_papers.append({
            "paper": paper,
            "score": float(final_score),
            "corpus_similarity": float(final_score),
            "corpus_size": len(corpus),
            "top_match": sorted_corpus[results[0]["corpus_id"]]["data"]["title"],
            "top_match_score": results[0]["score"]
        })
    
    # Sort by score (highest first)
    scored_papers.sort(key=lambda x: x["score"], reverse=True)
    
    return scored_papers


def main():
    """Run the FlashRank demonstration."""
    print("="*80)
    print("FLASHRANK RERANKING DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows how FlashRank reranks papers based on relevance to a")
    print("user's research corpus, using time-decay weighting to favor recent papers.")
    print("\n" + "="*80)
    
    # Create sample data
    print("\nCreating sample research corpus...")
    corpus = create_sample_corpus()
    print(f"Corpus size: {len(corpus)} papers")
    
    print("\nCreating candidate papers to rank...")
    candidates = create_candidate_papers()
    print(f"Candidates: {len(candidates)} papers")
    
    # Perform reranking
    print("\n" + "="*80)
    print("STARTING RERANKING PROCESS")
    print("="*80)
    
    results = rerank_with_flashrank(candidates, corpus)
    
    # Display final results
    print("\n" + "="*80)
    print("FINAL RANKING RESULTS")
    print("="*80)
    print("\nPapers ranked by relevance to your research corpus:\n")
    
    for i, result in enumerate(results):
        print(f"{i+1}. [{result['score']:.4f}] {result['paper']['title']}")
        print(f"   Top match: {result['top_match']}")
        print(f"   Match score: {result['top_match_score']:.4f}")
        print()
    
    # Analysis
    print("="*80)
    print("ANALYSIS & VALIDITY")
    print("="*80)
    print("\nKey observations:")
    print()
    print("1. RELEVANCE DETECTION:")
    print("   Papers about transformers and vision models score highest because")
    print("   they match the corpus theme (ML/CV).")
    print()
    print("2. TIME DECAY WEIGHTING:")
    print("   More recent corpus papers get higher weights, ensuring that")
    print("   current research interests are prioritized.")
    print()
    print("3. IRRELEVANT PAPERS FILTERED:")
    print("   Papers on unrelated topics (quantum computing, agriculture)")
    print("   receive lower scores, showing the method's discriminative power.")
    print()
    print("4. SEMANTIC UNDERSTANDING:")
    print("   FlashRank uses semantic similarity, not just keyword matching,")
    print("   identifying conceptual relevance (e.g., ViT variations, attention).")
    print()
    print("="*80)
    print("\nThis demonstrates that the reranking method effectively identifies")
    print("papers most relevant to a user's research interests based on their")
    print("existing corpus, with appropriate weighting for recency.")
    print("="*80)


if __name__ == "__main__":
    main()

