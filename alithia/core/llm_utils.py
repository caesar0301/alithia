"""
LLM utilities for content generation using cogents_core.llm.
"""

import logging

from cogents_core.llm import get_llm_client

from .researcher import LLMConnection

logger = logging.getLogger(__name__)


def get_llm(conn: LLMConnection):
    """
    Get LLM instance based on LLMConnection configuration.

    Args:
        conn: LLMConnection instance

    Returns:
        LLM client instance
    """
    try:
        llm = get_llm_client(
            provider="openai",
            api_key=conn.openai_api_key,
            base_url=conn.openai_api_base,
            chat_model=conn.model_name,
        )
        # Set the chat_model attribute for testing purposes
        llm.chat_model = conn.model_name
        return llm
    except Exception as e:
        logger.warning(f"Failed to initialize LLM client: {e}")
        raise e
