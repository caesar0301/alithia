"""
AlithiaLens: Deep Paper Interaction Agent
"""

import logging
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from .nodes import get_user_input_node, load_paper_node, process_query_node, route_query_node
from .state import AgentState

logger = logging.getLogger(__name__)


class LensAgent:
    """
    Provides an interactive, semantic reading and analysis
    experience for academic papers.
    """

    def __init__(self):
        """Initialize the Lens agent."""
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        """Create the LangGraph workflow for AlithiaLens."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("get_user_input", get_user_input_node)
        workflow.add_node("load_paper", load_paper_node)
        workflow.add_node("process_query", process_query_node)

        # Define conditional routing
        workflow.add_conditional_edges(
            "get_user_input",
            route_query_node,
            {
                "load": "load_paper",
                "interact": "process_query",
                "exit": END,
            },
        )

        # Define loop
        workflow.add_edge("load_paper", "get_user_input")
        workflow.add_edge("process_query", "get_user_input")

        # Set entry point
        workflow.set_entry_point("get_user_input")

        return workflow.compile()

    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the Lens agent in an interactive session.

        Args:
            config: Configuration dictionary, e.g., with a paper ID to start.

        Returns:
            Final state dictionary.
        """
        logger.info("Starting AlithiaLens interactive session...")
        initial_state = AgentState(
            profile=None,
            debug_mode=config.get("debug", False),
            # Pass initial user input if provided
            user_input=config.get("initial_query"),
        )

        try:
            # The `invoke` method will cycle through the graph until an END state is reached.
            final_state = self.workflow.invoke(initial_state, config={"recursion_limit": 50})
            logger.info("AlithiaLens session ended.")
            return {"success": True, "summary": final_state}
        except Exception as e:
            logger.error(f"AlithiaLens session failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
