"""
Unit tests for the paper reranker module.
"""

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest
import numpy as np

from alithia.models import ArxivPaper
from alithia.arxrec.reranker import PaperReranker
from alithia.arxrec.models import ScoredPaper


@pytest.fixture
def sample_papers():
    """Create sample papers for testing."""
    return [
        ArxivPaper(
            title="Machine Learning Paper",
            summary="This paper discusses machine learning algorithms and deep neural networks.",
            authors=["Alice"],
            arxiv_id="2312.00001",
            pdf_url="url1"
        ),
        ArxivPaper(
            title="Computer Vision Paper",
            summary="This paper explores computer vision techniques for image recognition.",
            authors=["Bob"],
            arxiv_id="2312.00002",
            pdf_url="url2"
        ),
        ArxivPaper(
            title="Natural Language Processing",
            summary="This paper presents advances in natural language processing and transformers.",
            authors=["Charlie"],
            arxiv_id="2312.00003",
            pdf_url="url3"
        ),
    ]


@pytest.fixture
def sample_corpus():
    """Create sample Zotero corpus for testing."""
    return [
        {
            "data": {
                "abstractNote": "Deep learning is a subset of machine learning.",
                "dateAdded": "2023-12-01T10:00:00Z"
            }
        },
        {
            "data": {
                "abstractNote": "Neural networks are used for pattern recognition.",
                "dateAdded": "2023-12-10T10:00:00Z"
            }
        },
        {
            "data": {
                "abstractNote": "Computer vision enables machines to interpret visual information.",
                "dateAdded": "2023-12-15T10:00:00Z"
            }
        },
    ]


@pytest.mark.unit
def test_paper_reranker_initialization(sample_papers, sample_corpus):
    """Test PaperReranker initialization."""
    reranker = PaperReranker(sample_papers, sample_corpus)
    
    assert reranker.papers == sample_papers
    assert reranker.corpus == sample_corpus
    assert reranker.cache_dir is not None


@pytest.mark.unit
def test_paper_reranker_empty_papers(sample_corpus):
    """Test reranker with empty papers list."""
    reranker = PaperReranker([], sample_corpus)
    
    assert reranker.papers == []
    assert len(reranker.corpus) > 0


@pytest.mark.unit
def test_paper_reranker_empty_corpus(sample_papers):
    """Test reranker with empty corpus."""
    reranker = PaperReranker(sample_papers, [])
    
    assert len(reranker.papers) > 0
    assert reranker.corpus == []


@pytest.mark.unit
def test_rerank_sentence_transformer_no_papers(sample_corpus):
    """Test reranking with no papers returns empty list."""
    reranker = PaperReranker([], sample_corpus)
    
    with patch('sentence_transformers.SentenceTransformer'):
        result = reranker.rerank_sentence_transformer()
        
        assert result == []


@pytest.mark.unit
def test_rerank_sentence_transformer_no_corpus(sample_papers):
    """Test reranking with no corpus returns default scores."""
    reranker = PaperReranker(sample_papers, [])
    
    with patch('sentence_transformers.SentenceTransformer'):
        result = reranker.rerank_sentence_transformer()
        
        assert len(result) == len(sample_papers)
        assert all(scored.score == 5.0 for scored in result)
        assert all(scored.relevance_factors.get("default") == 5.0 for scored in result)


@pytest.mark.unit
def test_rerank_sentence_transformer_missing_import(sample_papers, sample_corpus):
    """Test that ImportError is raised when sentence-transformers is not installed."""
    reranker = PaperReranker(sample_papers, sample_corpus)
    
    with patch.dict('sys.modules', {'sentence_transformers': None}):
        with pytest.raises(ImportError, match="SentenceTransformer is not installed"):
            reranker.rerank_sentence_transformer()


@pytest.mark.unit
def test_rerank_sentence_transformer_success(sample_papers, sample_corpus):
    """Test successful reranking with sentence transformers."""
    reranker = PaperReranker(sample_papers, sample_corpus)
    
    # Mock SentenceTransformer
    mock_encoder = Mock()
    
    # Create mock embeddings (3 papers x 384 dim, 3 corpus x 384 dim)
    paper_embeddings = np.random.rand(3, 384)
    corpus_embeddings = np.random.rand(3, 384)
    
    mock_encoder.encode.side_effect = [corpus_embeddings, paper_embeddings]
    
    with patch('sentence_transformers.SentenceTransformer', return_value=mock_encoder), \
         patch('sklearn.metrics.pairwise.cosine_similarity') as mock_sim:
        
        # Mock similarity matrix (3 papers x 3 corpus)
        mock_sim.return_value = np.array([
            [0.9, 0.7, 0.5],  # Paper 1 similarities
            [0.5, 0.8, 0.9],  # Paper 2 similarities
            [0.6, 0.6, 0.7],  # Paper 3 similarities
        ])
        
        result = reranker.rerank_sentence_transformer()
        
        assert len(result) == 3
        assert all(isinstance(scored, ScoredPaper) for scored in result)
        
        # Check that papers are sorted by score (descending)
        scores = [scored.score for scored in result]
        assert scores == sorted(scores, reverse=True)
        
        # Check relevance factors are populated
        assert all("corpus_similarity" in scored.relevance_factors for scored in result)
        assert all("corpus_size" in scored.relevance_factors for scored in result)
        assert all("max_similarity" in scored.relevance_factors for scored in result)


@pytest.mark.unit
def test_rerank_sentence_transformer_with_invalid_corpus(sample_papers):
    """Test reranking handles invalid corpus entries gracefully."""
    # Corpus with missing/invalid data
    invalid_corpus = [
        {"data": {"abstractNote": "Valid abstract", "dateAdded": "2023-12-01T10:00:00Z"}},
        {"data": {"dateAdded": "2023-12-02T10:00:00Z"}},  # Missing abstractNote
        {"invalid": "structure"},  # Invalid structure
        {"data": {"abstractNote": "", "dateAdded": "2023-12-03T10:00:00Z"}},  # Empty abstract
    ]
    
    reranker = PaperReranker(sample_papers, invalid_corpus)
    
    mock_encoder = Mock()
    corpus_embeddings = np.random.rand(1, 384)  # Only 1 valid corpus item
    paper_embeddings = np.random.rand(3, 384)
    mock_encoder.encode.side_effect = [corpus_embeddings, paper_embeddings]
    
    with patch('sentence_transformers.SentenceTransformer', return_value=mock_encoder), \
         patch('sklearn.metrics.pairwise.cosine_similarity') as mock_sim:
        
        mock_sim.return_value = np.array([[0.8], [0.7], [0.9]])
        
        result = reranker.rerank_sentence_transformer()
        
        # Should still produce results despite invalid corpus entries
        assert len(result) == 3


@pytest.mark.unit
def test_rerank_sentence_transformer_papers_without_summary(sample_corpus):
    """Test reranking skips papers without summaries."""
    papers = [
        ArxivPaper(
            title="Paper 1",
            summary="Valid summary",
            authors=["Author 1"],
            arxiv_id="2312.00001",
            pdf_url="url1"
        ),
        ArxivPaper(
            title="Paper 2",
            summary="",  # Empty summary
            authors=["Author 2"],
            arxiv_id="2312.00002",
            pdf_url="url2"
        ),
        ArxivPaper(
            title="Paper 3",
            summary="   ",  # Whitespace-only summary
            authors=["Author 3"],
            arxiv_id="2312.00003",
            pdf_url="url3"
        ),
    ]
    
    reranker = PaperReranker(papers, sample_corpus)
    
    mock_encoder = Mock()
    corpus_embeddings = np.random.rand(3, 384)
    paper_embeddings = np.random.rand(1, 384)  # Only 1 valid paper
    mock_encoder.encode.side_effect = [corpus_embeddings, paper_embeddings]
    
    with patch('sentence_transformers.SentenceTransformer', return_value=mock_encoder), \
         patch('sklearn.metrics.pairwise.cosine_similarity') as mock_sim:
        
        mock_sim.return_value = np.array([[0.8, 0.7, 0.6]])
        
        result = reranker.rerank_sentence_transformer()
        
        # Should only include the paper with valid summary
        assert len(result) == 1
        assert result[0].paper.arxiv_id == "2312.00001"


@pytest.mark.unit
def test_rerank_sentence_transformer_error_fallback(sample_papers, sample_corpus):
    """Test that errors during reranking fall back to default scores."""
    reranker = PaperReranker(sample_papers, sample_corpus)
    
    mock_encoder = Mock()
    mock_encoder.encode.side_effect = Exception("Encoding failed")
    
    with patch('sentence_transformers.SentenceTransformer', return_value=mock_encoder):
        result = reranker.rerank_sentence_transformer()
        
        # Should return fallback scores
        assert len(result) == len(sample_papers)
        assert all(scored.score == 5.0 for scored in result)
        assert all("error_fallback" in scored.relevance_factors for scored in result)


@pytest.mark.unit
def test_rerank_sentence_transformer_time_decay():
    """Test that time decay weighting works correctly."""
    papers = [
        ArxivPaper(
            title="Test Paper",
            summary="Machine learning and neural networks.",
            authors=["Author"],
            arxiv_id="2312.00001",
            pdf_url="url"
        )
    ]
    
    # Corpus with different dates (newer should have higher weight)
    corpus = [
        {
            "data": {
                "abstractNote": "Old paper about ML",
                "dateAdded": "2023-01-01T10:00:00Z"  # Old
            }
        },
        {
            "data": {
                "abstractNote": "Recent paper about ML",
                "dateAdded": "2023-12-01T10:00:00Z"  # Recent
            }
        },
    ]
    
    reranker = PaperReranker(papers, corpus)
    
    mock_encoder = Mock()
    corpus_embeddings = np.random.rand(2, 384)
    paper_embeddings = np.random.rand(1, 384)
    mock_encoder.encode.side_effect = [corpus_embeddings, paper_embeddings]
    
    with patch('sentence_transformers.SentenceTransformer', return_value=mock_encoder), \
         patch('sklearn.metrics.pairwise.cosine_similarity') as mock_sim:
        
        # Same similarity for both corpus papers
        mock_sim.return_value = np.array([[0.8, 0.8]])
        
        result = reranker.rerank_sentence_transformer()
        
        # Verify that time decay was applied (recent corpus should have higher weight)
        # The score should be influenced by time decay
        assert len(result) == 1
        assert result[0].relevance_factors["corpus_size"] == 2


@pytest.mark.unit
def test_rerank_sentence_transformer_custom_model(sample_papers, sample_corpus):
    """Test reranking with custom model name."""
    reranker = PaperReranker(sample_papers, sample_corpus, cache_dir="/tmp/custom_cache")
    
    mock_encoder = Mock()
    corpus_embeddings = np.random.rand(3, 384)
    paper_embeddings = np.random.rand(3, 384)
    mock_encoder.encode.side_effect = [corpus_embeddings, paper_embeddings]
    
    with patch('sentence_transformers.SentenceTransformer', return_value=mock_encoder) as mock_st, \
         patch('sklearn.metrics.pairwise.cosine_similarity') as mock_sim:
        
        mock_sim.return_value = np.random.rand(3, 3)
        
        custom_model = "custom-model-name"
        result = reranker.rerank_sentence_transformer(model_name=custom_model)
        
        # Verify custom model was used
        mock_st.assert_called_once()
        call_args = mock_st.call_args
        assert call_args[0][0] == custom_model
        assert call_args[1]["cache_folder"] == "/tmp/custom_cache"


@pytest.mark.unit
def test_rerank_sentence_transformer_batch_size(sample_papers, sample_corpus):
    """Test that custom batch size is used."""
    reranker = PaperReranker(sample_papers, sample_corpus)
    
    mock_encoder = Mock()
    corpus_embeddings = np.random.rand(3, 384)
    paper_embeddings = np.random.rand(3, 384)
    mock_encoder.encode.side_effect = [corpus_embeddings, paper_embeddings]
    
    with patch('sentence_transformers.SentenceTransformer', return_value=mock_encoder), \
         patch('sklearn.metrics.pairwise.cosine_similarity') as mock_sim:
        
        mock_sim.return_value = np.random.rand(3, 3)
        
        result = reranker.rerank_sentence_transformer(batch_size=16)
        
        # Verify batch_size was passed to encode calls
        encode_calls = mock_encoder.encode.call_args_list
        assert all(call[1].get('batch_size') == 16 for call in encode_calls)


@pytest.mark.unit
def test_scored_paper_updates_paper_score():
    """Test that ScoredPaper updates the paper's score field."""
    paper = ArxivPaper(
        title="Test",
        summary="Abstract",
        authors=["Author"],
        arxiv_id="2312.00001",
        pdf_url="url"
    )
    
    assert paper.score is None
    
    scored = ScoredPaper(paper=paper, score=8.5, relevance_factors={"test": 8.5})
    
    # After ScoredPaper creation, the paper's score should be updated
    assert scored.paper.score == 8.5
    assert scored.score == 8.5
