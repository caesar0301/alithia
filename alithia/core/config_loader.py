import logging
import os
import sys
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def get_env(key: str, default=None):
    """
    Get environment variable, handling empty strings as None.

    Args:
        key: Environment variable key
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    value = os.environ.get(key)
    if value == "" or value is None:
        return default
    return value


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from JSON file or environment variables.
    """
    if config_path and not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Build configuration
    env_config = _build_config_from_envs()

    config_file = config_path or os.path.join(os.path.dirname(__file__), "alithia_config.json")
    if os.path.exists(config_file):
        file_dict = _load_config_from_file(config_file)
        # merge file config and env config with env config taking precedence
        config_dict = _merge_configs(file_dict, env_config)
    else:
        config_dict = env_config

    # Enable debug logging if specified
    if config_dict.get("debug", False):
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug(f"Final configuration: {config_dict}")

    return config_dict


def _load_config_from_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    import json

    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file {config_path}: {e}")
        sys.exit(1)


def _build_config_from_envs() -> Dict[str, Any]:
    """
    Build configuration dictionary from environment variables.

    Returns:
        Configuration dictionary in nested format
    """
    config = {}

    # Map environment variables to nested config structure
    env_mapping = {
        # General settings
        "research_interests": "ALITHIA_RESEARCH_INTERESTS",
        "expertise_level": "ALITHIA_EXPERTISE_LEVEL",
        "language": "ALITHIA_LANGUAGE",
        "email": "ALITHIA_EMAIL",
        "debug": "ALITHIA_DEBUG",
        # LLM settings
        "llm.openai_api_key": "ALITHIA_OPENAI_API_KEY",
        "llm.openai_api_base": "ALITHIA_OPENAI_API_BASE",
        "llm.model_name": "ALITHIA_MODEL_NAME",
        # Zotero settings
        "zotero.zotero_id": "ALITHIA_ZOTERO_ID",
        "zotero.zotero_key": "ALITHIA_ZOTERO_KEY",
        # Email notification settings
        "email_notification.smtp_server": "ALITHIA_SMTP_SERVER",
        "email_notification.smtp_port": "ALITHIA_SMTP_PORT",
        "email_notification.sender": "ALITHIA_SENDER",
        "email_notification.sender_password": "ALITHIA_SENDER_PASSWORD",
        "email_notification.receiver": "ALITHIA_RECEIVER",
        # Arxrec specific settings
        "arxrec.query": "ALITHIA_ARXIV_QUERY",
        "arxrec.max_papers": "ALITHIA_MAX_PAPER_NUM",
        "arxrec.send_empty": "ALITHIA_SEND_EMPTY",
        "arxrec.ignore_patterns": "ALITHIA_ZOTERO_IGNORE",
    }

    for config_key, env_key in env_mapping.items():
        value = get_env(env_key)
        if value is not None:
            # Convert string values to appropriate types
            if config_key in ["email_notification.smtp_port", "arxrec.max_papers"]:
                try:
                    value = int(value)
                except ValueError:
                    continue
            elif config_key in ["arxrec.send_empty", "debug"]:
                value = str(value).lower() in ["true", "1", "yes"]
            elif config_key == "arxrec.ignore_patterns" and value:
                # Convert comma-separated string to list
                value = [pattern.strip() for pattern in value.split(",") if pattern.strip()]
            elif config_key == "research_interests" and value:
                # Convert comma-separated string to list
                value = [interest.strip() for interest in value.split(",") if interest.strip()]

            # Set nested value
            _set_nested_value(config, config_key, value)

    return config


def _set_nested_value(config: Dict[str, Any], key: str, value: Any) -> None:
    """
    Set a nested value in a dictionary using dot notation.

    Args:
        config: Configuration dictionary
        key: Dot-separated key (e.g., "llm.openai_api_key")
        value: Value to set
    """
    keys = key.split(".")
    current = config

    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    current[keys[-1]] = value


def _merge_configs(file_config: Dict[str, Any], env_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge file config and environment config with environment taking precedence.

    Args:
        file_config: Configuration from file
        env_config: Configuration from environment variables

    Returns:
        Merged configuration
    """
    merged = file_config.copy()

    def merge_nested(target: Dict[str, Any], source: Dict[str, Any]) -> None:
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                merge_nested(target[key], value)
            else:
                target[key] = value

    merge_nested(merged, env_config)
    return merged
