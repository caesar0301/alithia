"""Test state persistence across LangGraph nodes."""

import pytest

from alithia.arxrec.state import AgentState, ArxrecConfig
from alithia.core.researcher import (
    EmailConnection,
    LLMConnection,
    ResearcherProfile,
    ZoteroConnection,
)


@pytest.fixture
def sample_config():
    """Create a sample ArxrecConfig for testing."""
    user_profile = ResearcherProfile(
        email="test@example.com",
        zotero=ZoteroConnection(
            zotero_id="test_id",
            zotero_key="test_key",
        ),
        email_notification=EmailConnection(
            smtp_server="smtp.test.com",
            smtp_port=587,
            sender="sender@test.com",
            receiver="receiver@test.com",
            sender_password="password",
        ),
        llm=LLMConnection(
            openai_api_key="test_key",
            openai_api_base="https://api.openai.com/v1",
            model_name="gpt-4",
        ),
    )

    return ArxrecConfig(
        user_profile=user_profile,
        query="cs.AI",
        max_papers=10,
    )


def test_error_log_accumulation(sample_config):
    """Test that error_log accumulates properly with Annotated type."""
    state = AgentState(config=sample_config)

    # Simulate adding errors
    state.add_error("Error 1")
    state.add_error("Error 2")

    assert len(state.error_log) == 2
    assert "Error 1" in state.error_log[0]
    assert "Error 2" in state.error_log[1]


def test_performance_metrics_accumulation(sample_config):
    """Test that performance_metrics accumulates properly with Annotated type."""
    state = AgentState(config=sample_config)

    # Simulate updating metrics
    state.update_metric("metric1", 1.5)
    state.update_metric("metric2", 2.5)

    assert len(state.performance_metrics) == 2
    assert state.performance_metrics["metric1"] == 1.5
    assert state.performance_metrics["metric2"] == 2.5


def test_state_dict_conversion(sample_config):
    """Test that state can be converted to dict and maintains all fields."""
    state = AgentState(config=sample_config)
    state.add_error("Test error")
    state.update_metric("test_metric", 1.0)

    # Convert to dict (mimicking what LangGraph does)
    state_dict = state.model_dump()

    assert "error_log" in state_dict
    assert "performance_metrics" in state_dict
    assert len(state_dict["error_log"]) == 1
    assert state_dict["performance_metrics"]["test_metric"] == 1.0


def test_node_return_format(sample_config):
    """Test that node return format includes error_log when errors are added."""
    state = AgentState(config=sample_config)

    # Simulate what a node does when it adds an error
    state.add_error("Node error")
    return_dict = {"current_step": "error", "error_log": state.error_log}

    # Verify the return format includes error_log
    assert "error_log" in return_dict
    assert len(return_dict["error_log"]) == 1
    assert "Node error" in return_dict["error_log"][0]


def test_state_summary(sample_config):
    """Test that state summary provides correct information."""
    state = AgentState(config=sample_config)

    # Add some data
    state.add_error("Test error")
    state.update_metric("papers_processed", 5.0)
    state.current_step = "testing"

    summary = state.get_summary()

    assert summary["current_step"] == "testing"
    assert summary["errors"] == 1
    assert "papers_processed" in summary["metrics"]
