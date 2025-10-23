"""
Main research agent implementation using LangGraph.
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph

from .nodes import (
    communication_node,
    content_generation_node,
    data_collection_node,
    profile_analysis_node,
    relevance_assessment_node,
)
from .state import AgentState, ArxrecConfig

logger = logging.getLogger(__name__)


class ArxrecAgent:
    """
    LangGraph-based research agent that replicates zotero-arxiv-daily functionality.
    """

    def __init__(self):
        """Initialize the research agent."""
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        """Create the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("profile_analysis", profile_analysis_node)
        workflow.add_node("data_collection", data_collection_node)
        workflow.add_node("relevance_assessment", relevance_assessment_node)
        workflow.add_node("content_generation", content_generation_node)
        workflow.add_node("communication", communication_node)

        # Define edges (linear workflow)
        workflow.add_edge("profile_analysis", "data_collection")
        workflow.add_edge("data_collection", "relevance_assessment")
        workflow.add_edge("relevance_assessment", "content_generation")
        workflow.add_edge("content_generation", "communication")

        # Set entry and exit points
        workflow.set_entry_point("profile_analysis")
        workflow.set_finish_point("communication")

        # Compile with state configuration to ensure proper state handling
        return workflow.compile()

    def run(self, config: ArxrecConfig) -> Dict[str, Any]:
        """
        Run the research agent with given configuration.

        Args:
            config: ArxrecConfig object with all necessary parameters

        Returns:
            Final state dictionary with results
        """
        logger.info("Starting research agent workflow...")

        # Create initial state
        initial_state = AgentState(config=config, debug_mode=getattr(config, "debug", False))

        try:
            # Run workflow
            final_state = self.workflow.invoke(initial_state)

            # Handle both AgentState and dict returns from LangGraph
            if hasattr(final_state, "get_summary"):
                # It's an AgentState object
                summary = final_state.get_summary()
                papers_sent = len(final_state.scored_papers)
                errors = final_state.error_log
            else:
                # It's a dictionary (LangGraph sometimes returns dict)
                summary = {
                    "current_step": final_state.get("current_step", "unknown"),
                    "papers_discovered": len(final_state.get("discovered_papers", [])),
                    "papers_scored": len(final_state.get("scored_papers", [])),
                    "errors": len(final_state.get("error_log", [])),
                    "metrics": final_state.get("performance_metrics", {}),
                }
                papers_sent = len(final_state.get("scored_papers", []))
                errors = final_state.get("error_log", [])

            logger.info(f"Workflow completed: {summary}")

            return {
                "success": True,
                "summary": summary,
                "papers_sent": papers_sent,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            return {"success": False, "error": str(e), "errors": initial_state.error_log}

    def get_workflow_info(self) -> Dict[str, Any]:
        """
        Get information about the workflow structure.

        Returns:
            Dictionary with workflow information
        """
        return {
            "name": "Alithia Research Agent",
            "description": "A personalized arXiv recommendation agent.",
            "nodes": [
                "profile_analysis",
                "data_collection",
                "relevance_assessment",
                "content_generation",
                "communication",
            ],
            "entry_point": "profile_analysis",
            "exit_point": "communication",
        }
