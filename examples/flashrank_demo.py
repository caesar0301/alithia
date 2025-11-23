"""FlashRank reranking demo: paper relevance scoring with time-decay weighting.

Mirrors the approach in alithia/arxrec/recommender.py
"""

from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
from flashrank import Ranker, RerankRequest


def create_sample_corpus() -> List[Dict[str, any]]:
    """Create sample research corpus (ML/CV papers)."""
    base_date = datetime.now()

    corpus = [
        {
            "data": {
                "title": "Attention Is All You Need",
                "abstractNote": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
                "dateAdded": (base_date - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
        {
            "data": {
                "title": "Deep Residual Learning for Image Recognition",
                "abstractNote": "We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions.",
                "dateAdded": (base_date - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
        {
            "data": {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "abstractNote": "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context.",
                "dateAdded": (base_date - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
        {
            "data": {
                "title": "Generative Adversarial Networks",
                "abstractNote": "We propose a new framework for estimating generative models via an adversarial process, in which we simultaneously train two models: a generative model G that captures the data distribution, and a discriminative model D that estimates the probability that a sample came from the training data rather than G.",
                "dateAdded": (base_date - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
        {
            "data": {
                "title": "Vision Transformer (ViT)",
                "abstractNote": "While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited. In vision, attention is either applied in conjunction with convolutional networks, or used to replace certain components of convolutional networks while keeping their overall structure in place.",
                "dateAdded": (base_date - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
    ]

    return corpus


def create_candidate_papers() -> List[Dict[str, str]]:
    """Create candidate papers for reranking (mixed relevance)."""
    papers = [
        {
            "title": "Swin Transformer: Hierarchical Vision Transformer using Shifted Windows",
            "summary": "This paper presents a new vision Transformer, called Swin Transformer, that capably serves as a general-purpose backbone for computer vision. Challenges in adapting Transformer from language to vision arise from differences between the two domains, such as large variations in the scale of visual entities and the high resolution of pixels in images compared to words in text.",
        },
        {
            "title": "Quantum Computing Applications in Drug Discovery",
            "summary": "We explore the potential of quantum computing for accelerating drug discovery processes. Our framework leverages quantum algorithms for molecular simulation and protein folding prediction, demonstrating significant speedups over classical approaches in specific pharmaceutical applications.",
        },
        {
            "title": "Transformer-XL: Attentive Language Models Beyond a Fixed-Length Context",
            "summary": "Transformers have a potential of learning longer-term dependency, but are limited by a fixed-length context in the setting of language modeling. We propose a novel neural architecture Transformer-XL that enables learning dependency beyond a fixed length without disrupting temporal coherence.",
        },
        {
            "title": "Agricultural Soil Analysis Using Traditional Methods",
            "summary": "This study investigates traditional soil analysis techniques for agricultural applications. We compare pH measurement methods, nutrient content assessment, and moisture retention properties across different soil types in various geographical regions, providing recommendations for sustainable farming practices.",
        },
        {
            "title": "ConvNeXt: A ConvNet for the 2020s",
            "summary": "The 'Roaring 20s' of visual recognition began with the introduction of Vision Transformers (ViTs), which quickly superseded ConvNets as the state-of-the-art image classification model. We reexamine the design spaces and test the limits of what a pure ConvNet can achieve, gradually modernizing a standard ResNet toward the design of a vision Transformer.",
        },
    ]

    return papers


def rerank_with_flashrank(
    candidate_papers: List[Dict[str, str]], corpus: List[Dict[str, any]], model_name: str = "ms-marco-MiniLM-L-12-v2"
) -> List[Dict[str, any]]:
    """Rerank papers by corpus relevance (mirrors alithia/arxrec/recommender.py).

    Args:
        candidate_papers: Papers to rank
        corpus: User's research corpus
        model_name: FlashRank model

    Returns:
        Papers with scores, sorted by relevance
    """
    if not candidate_papers or not corpus:
        return [{"paper": p, "score": 0.0} for p in candidate_papers]

    print(f"Initializing FlashRank: {model_name}")
    ranker = Ranker(model_name=model_name, cache_dir="/tmp/flashrank_cache")

    sorted_corpus = sorted(
        corpus, key=lambda x: datetime.strptime(x["data"]["dateAdded"], "%Y-%m-%dT%H:%M:%SZ"), reverse=True
    )

    print(f"\nCorpus (newest first):")
    for i, paper in enumerate(sorted_corpus):
        print(f"  {i+1}. {paper['data']['title']} ({paper['data']['dateAdded'][:10]})")

    time_decay_weight = 1 / (1 + np.log10(np.arange(len(sorted_corpus)) + 1))
    time_decay_weight = time_decay_weight / time_decay_weight.sum()

    print(f"\nTime decay weights (sum={time_decay_weight.sum():.4f}):")
    for i, weight in enumerate(time_decay_weight):
        print(f"  Position {i+1}: {weight:.4f}")

    corpus_passages = [{"text": paper["data"]["abstractNote"]} for paper in sorted_corpus]
    scored_papers = []

    print("\n" + "=" * 80)
    print("RERANKING CANDIDATE PAPERS")
    print("=" * 80)

    for idx, paper in enumerate(candidate_papers):
        print(f"\n[{idx+1}/{len(candidate_papers)}] {paper['title']}")
        print(f"Summary: {paper['summary'][:100]}...")

        rerank_request = RerankRequest(query=paper["summary"], passages=corpus_passages)
        results = ranker.rerank(rerank_request)

        weighted_scores = []
        print(f"\nCorpus relevance:")

        text_to_idx = {paper["data"]["abstractNote"]: idx for idx, paper in enumerate(sorted_corpus)}

        for result in results:
            relevance_score = result["score"]
            corpus_idx = text_to_idx[result["text"]]
            weighted_score = relevance_score * time_decay_weight[corpus_idx]
            weighted_scores.append(weighted_score)

            corpus_title = sorted_corpus[corpus_idx]["data"]["title"]
            print(
                f"  - {corpus_title[:50]:50s} | "
                f"Relevance: {relevance_score:6.4f} | "
                f"Weight: {time_decay_weight[corpus_idx]:.4f} | "
                f"Weighted: {weighted_score:.4f}"
            )

        final_score = sum(weighted_scores) * 10

        print(f"\n  Total weighted: {sum(weighted_scores):.4f}")
        print(f"  Final (×10): {final_score:.4f}")

        best_match_idx = text_to_idx[results[0]["text"]]

        scored_papers.append(
            {
                "paper": paper,
                "score": float(final_score),
                "corpus_similarity": float(final_score),
                "corpus_size": len(corpus),
                "top_match": sorted_corpus[best_match_idx]["data"]["title"],
                "top_match_score": results[0]["score"],
            }
        )

    scored_papers.sort(key=lambda x: x["score"], reverse=True)
    return scored_papers


def main():
    """Run FlashRank demo."""
    print("=" * 80)
    print("FLASHRANK RERANKING DEMONSTRATION")
    print("=" * 80)
    print("\nReranks papers by corpus relevance with time-decay weighting.")
    print("\n" + "=" * 80)

    print("\nCreating sample corpus...")
    corpus = create_sample_corpus()
    print(f"Corpus: {len(corpus)} papers")

    print("\nCreating candidates...")
    candidates = create_candidate_papers()
    print(f"Candidates: {len(candidates)} papers")

    print("\n" + "=" * 80)
    print("RERANKING PROCESS")
    print("=" * 80)

    results = rerank_with_flashrank(candidates, corpus)

    print("\n" + "=" * 80)
    print("FINAL RANKING")
    print("=" * 80)
    print("\nPapers by relevance:\n")

    for i, result in enumerate(results):
        print(f"{i+1}. [{result['score']:.4f}] {result['paper']['title']}")
        print(f"   Top match: {result['top_match']}")
        print(f"   Match score: {result['top_match_score']:.4f}")
        print()

    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("\nKey observations:")
    print()
    print("1. RELEVANCE: Transformer/vision papers score highest (match corpus theme)")
    print("2. TIME DECAY: Recent corpus papers weighted higher (prioritize current interests)")
    print("3. FILTERING: Unrelated topics (quantum, agriculture) score low")
    print("4. SEMANTIC: Uses conceptual similarity, not just keywords")
    print()
    print("=" * 80)
    print("Method effectively identifies relevant papers with recency weighting.")
    print("=" * 80)


if __name__ == "__main__":
    main()
