import json
import os
import tempfile
from unittest import mock

import pytest

from alithia.config_loader import (
    _build_config_from_envs,
    _load_config_from_file,
    _merge_configs,
    _set_nested_value,
    get_env,
    load_config,
)


@pytest.mark.unit
def test_get_env_returns_value():
    """Test that get_env returns the environment variable value."""
    with mock.patch.dict(os.environ, {"TEST_KEY": "test_value"}):
        assert get_env("TEST_KEY") == "test_value"


@pytest.mark.unit
def test_get_env_returns_default_for_missing_key():
    """Test that get_env returns default value for missing keys."""
    with mock.patch.dict(os.environ, {}, clear=False):
        assert get_env("NONEXISTENT_KEY", "default") == "default"


@pytest.mark.unit
def test_get_env_returns_default_for_empty_string():
    """Test that get_env treats empty strings as None and returns default."""
    with mock.patch.dict(os.environ, {"EMPTY_KEY": ""}, clear=False):
        assert get_env("EMPTY_KEY", "default") == "default"


@pytest.mark.unit
def test_set_nested_value_flat_key():
    """Test setting a flat key in config dictionary."""
    config = {}
    _set_nested_value(config, "key", "value")
    assert config == {"key": "value"}


@pytest.mark.unit
def test_set_nested_value_nested_key():
    """Test setting a nested key using dot notation."""
    config = {}
    _set_nested_value(config, "llm.openai_api_key", "test_key")
    assert config == {"llm": {"openai_api_key": "test_key"}}


@pytest.mark.unit
def test_set_nested_value_deeply_nested_key():
    """Test setting a deeply nested key with multiple levels."""
    config = {}
    _set_nested_value(config, "a.b.c.d", "value")
    assert config == {"a": {"b": {"c": {"d": "value"}}}}


@pytest.mark.unit
def test_set_nested_value_overwrites_existing():
    """Test that setting a nested value overwrites existing values."""
    config = {"llm": {"openai_api_key": "old_key"}}
    _set_nested_value(config, "llm.openai_api_key", "new_key")
    assert config == {"llm": {"openai_api_key": "new_key"}}


@pytest.mark.unit
def test_merge_configs_simple_values():
    """Test merging simple configuration values."""
    file_config = {"key1": "value1", "key2": "value2"}
    env_config = {"key2": "env_value2", "key3": "env_value3"}

    merged = _merge_configs(file_config, env_config)

    assert merged == {
        "key1": "value1",
        "key2": "env_value2",  # env takes precedence
        "key3": "env_value3",
    }


@pytest.mark.unit
def test_merge_configs_nested_values():
    """Test merging nested configuration values."""
    file_config = {
        "llm": {"openai_api_key": "file_key", "model_name": "gpt-3.5"},
        "zotero": {"zotero_id": "file_id"},
    }
    env_config = {
        "llm": {"openai_api_key": "env_key"},
        "zotero": {"zotero_key": "env_key"},
    }

    merged = _merge_configs(file_config, env_config)

    assert merged == {
        "llm": {"openai_api_key": "env_key", "model_name": "gpt-3.5"},
        "zotero": {"zotero_id": "file_id", "zotero_key": "env_key"},
    }


@pytest.mark.unit
def test_merge_configs_env_takes_precedence():
    """Test that environment config takes precedence in merging."""
    file_config = {"llm": {"model_name": "gpt-3.5", "openai_api_key": "file_key"}}
    env_config = {"llm": {"openai_api_key": "env_key"}}

    merged = _merge_configs(file_config, env_config)

    assert merged["llm"]["openai_api_key"] == "env_key"
    assert merged["llm"]["model_name"] == "gpt-3.5"


@pytest.mark.unit
def test_load_config_from_file_valid_json():
    """Test loading valid JSON configuration file."""
    config_data = {
        "research_interests": ["AI", "ML"],
        "llm": {"openai_api_key": "test_key"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        loaded_config = _load_config_from_file(temp_path)
        assert loaded_config == config_data
    finally:
        os.unlink(temp_path)


@pytest.mark.unit
def test_load_config_from_file_nonexistent():
    """Test that loading a non-existent file raises SystemExit."""
    with pytest.raises(SystemExit):
        _load_config_from_file("/path/that/does/not/exist.json")


@pytest.mark.unit
def test_load_config_from_file_invalid_json():
    """Test that loading invalid JSON raises SystemExit."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{invalid json content")
        temp_path = f.name

    try:
        with pytest.raises(SystemExit):
            _load_config_from_file(temp_path)
    finally:
        os.unlink(temp_path)


@pytest.mark.unit
def test_build_config_from_envs_research_interests():
    """Test building config from environment variables - research interests."""
    env_vars = {
        "ALITHIA_RESEARCH_INTERESTS": "AI,Machine Learning,Computer Vision",
    }

    with mock.patch.dict(os.environ, env_vars, clear=False):
        config = _build_config_from_envs()
        assert config["research_interests"] == ["AI", "Machine Learning", "Computer Vision"]


@pytest.mark.unit
def test_build_config_from_envs_integer_conversion():
    """Test that integer values are correctly converted."""
    env_vars = {
        "ALITHIA_SMTP_PORT": "587",
        "ALITHIA_MAX_PAPER_NUM": "50",
    }

    with mock.patch.dict(os.environ, env_vars, clear=False):
        config = _build_config_from_envs()
        assert config["email_notification"]["smtp_port"] == 587
        assert config["arxrec"]["max_papers"] == 50
        assert isinstance(config["email_notification"]["smtp_port"], int)
        assert isinstance(config["arxrec"]["max_papers"], int)


@pytest.mark.unit
def test_build_config_from_envs_boolean_conversion():
    """Test that boolean values are correctly converted."""
    test_cases = [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
    ]

    for env_value, expected in test_cases:
        env_vars = {"ALITHIA_SEND_EMPTY": env_value}
        with mock.patch.dict(os.environ, env_vars, clear=False):
            config = _build_config_from_envs()
            assert config["arxrec"]["send_empty"] is expected


@pytest.mark.unit
def test_build_config_from_envs_ignore_patterns():
    """Test that ignore patterns are converted to list."""
    env_vars = {
        "ALITHIA_ZOTERO_IGNORE": "pattern1,pattern2,pattern3",
    }

    with mock.patch.dict(os.environ, env_vars, clear=False):
        config = _build_config_from_envs()
        assert config["arxrec"]["ignore_patterns"] == ["pattern1", "pattern2", "pattern3"]


@pytest.mark.unit
def test_build_config_from_envs_integer_conversion_invalid():
    """Test that invalid integer values are skipped."""
    env_vars = {
        "ALITHIA_SMTP_PORT": "not_a_number",
    }

    with mock.patch.dict(os.environ, env_vars, clear=False):
        config = _build_config_from_envs()
        # Invalid integer values should be skipped
        assert "email_notification" not in config or "smtp_port" not in config.get("email_notification", {})


@pytest.mark.unit
def test_build_config_from_envs_all_llm_settings():
    """Test building all LLM settings from environment."""
    env_vars = {
        "ALITHIA_OPENAI_API_KEY": "test_key",
        "ALITHIA_OPENAI_API_BASE": "https://api.example.com/v1",
        "ALITHIA_MODEL_NAME": "gpt-4o",
    }

    with mock.patch.dict(os.environ, env_vars, clear=False):
        config = _build_config_from_envs()
        assert config["llm"]["openai_api_key"] == "test_key"
        assert config["llm"]["openai_api_base"] == "https://api.example.com/v1"
        assert config["llm"]["model_name"] == "gpt-4o"


@pytest.mark.unit
def test_build_config_from_envs_all_zotero_settings():
    """Test building all Zotero settings from environment."""
    env_vars = {
        "ALITHIA_ZOTERO_ID": "test_id",
        "ALITHIA_ZOTERO_KEY": "test_key",
    }

    with mock.patch.dict(os.environ, env_vars, clear=False):
        config = _build_config_from_envs()
        assert config["zotero"]["zotero_id"] == "test_id"
        assert config["zotero"]["zotero_key"] == "test_key"


@pytest.mark.unit
def test_build_config_from_envs_all_email_notification_settings():
    """Test building all email notification settings from environment."""
    env_vars = {
        "ALITHIA_SMTP_SERVER": "smtp.example.com",
        "ALITHIA_SMTP_PORT": "587",
        "ALITHIA_SENDER": "sender@example.com",
        "ALITHIA_SENDER_PASSWORD": "password",
        "ALITHIA_RECEIVER": "receiver@example.com",
    }

    with mock.patch.dict(os.environ, env_vars, clear=False):
        config = _build_config_from_envs()
        assert config["email_notification"]["smtp_server"] == "smtp.example.com"
        assert config["email_notification"]["smtp_port"] == 587
        assert config["email_notification"]["sender"] == "sender@example.com"
        assert config["email_notification"]["sender_password"] == "password"
        assert config["email_notification"]["receiver"] == "receiver@example.com"


@pytest.mark.unit
def test_build_config_from_envs_debug_flag():
    """Test that debug flag is correctly converted."""
    env_vars = {"ALITHIA_DEBUG": "true"}

    with mock.patch.dict(os.environ, env_vars, clear=False):
        config = _build_config_from_envs()
        assert config["debug"] is True


@pytest.mark.unit
def test_load_config_with_nonexistent_file_raises_error():
    """Test that providing a non-existent config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("/path/that/does/not/exist.json")


@pytest.mark.unit
def test_load_config_env_only():
    """Test loading config from environment variables only."""
    env_vars = {
        "ALITHIA_OPENAI_API_KEY": "test_key",
        "ALITHIA_MODEL_NAME": "gpt-4o",
        "ALITHIA_ZOTERO_ID": "zotero_123",
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a temporary directory without a config file
        with mock.patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            assert config["llm"]["openai_api_key"] == "test_key"
            assert config["llm"]["model_name"] == "gpt-4o"
            assert config["zotero"]["zotero_id"] == "zotero_123"


@pytest.mark.unit
def test_load_config_file_only():
    """Test loading config from JSON file only."""
    config_data = {
        "research_interests": ["AI", "ML"],
        "llm": {
            "openai_api_key": "file_key",
            "model_name": "gpt-3.5",
        },
        "zotero": {
            "zotero_id": "file_id",
            "zotero_key": "file_key",
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        with mock.patch.dict(os.environ, {}, clear=True):
            config = load_config(temp_path)

            assert config["research_interests"] == ["AI", "ML"]
            assert config["llm"]["openai_api_key"] == "file_key"
            assert config["llm"]["model_name"] == "gpt-3.5"
            assert config["zotero"]["zotero_id"] == "file_id"
    finally:
        os.unlink(temp_path)


@pytest.mark.unit
def test_load_config_env_overrides_file():
    """Test that environment variables take precedence over file config."""
    config_data = {
        "llm": {
            "openai_api_key": "file_key",
            "model_name": "gpt-3.5",
        },
        "zotero": {
            "zotero_id": "file_id",
            "zotero_key": "file_key",
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        env_vars = {
            "ALITHIA_OPENAI_API_KEY": "env_key",
            "ALITHIA_ZOTERO_ID": "env_id",
        }

        with mock.patch.dict(os.environ, env_vars, clear=True):
            config = load_config(temp_path)

            # Environment values should override file values
            assert config["llm"]["openai_api_key"] == "env_key"
            assert config["zotero"]["zotero_id"] == "env_id"

            # File values should remain for non-overridden keys
            assert config["llm"]["model_name"] == "gpt-3.5"
            assert config["zotero"]["zotero_key"] == "file_key"
    finally:
        os.unlink(temp_path)


@pytest.mark.unit
def test_load_config_merged_nested_structures():
    """Test loading and merging complex nested structures."""
    config_data = {
        "llm": {
            "openai_api_key": "file_key",
            "model_name": "gpt-3.5",
            "openai_api_base": "https://api.openai.com/v1",
        },
        "email_notification": {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "sender": "sender@example.com",
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        env_vars = {
            "ALITHIA_OPENAI_API_KEY": "env_key",
            "ALITHIA_SMTP_SERVER": "smtp.env.com",
        }

        with mock.patch.dict(os.environ, env_vars, clear=True):
            config = load_config(temp_path)

            # Check merged LLM config
            assert config["llm"]["openai_api_key"] == "env_key"
            assert config["llm"]["model_name"] == "gpt-3.5"
            assert config["llm"]["openai_api_base"] == "https://api.openai.com/v1"

            # Check merged email notification config
            assert config["email_notification"]["smtp_server"] == "smtp.env.com"
            assert config["email_notification"]["smtp_port"] == 587
            assert config["email_notification"]["sender"] == "sender@example.com"
    finally:
        os.unlink(temp_path)


@pytest.mark.unit
def test_load_config_general_settings():
    """Test loading general settings from both sources."""
    config_data = {
        "research_interests": ["File Interest"],
        "expertise_level": "beginner",
        "language": "English",
        "email": "file@example.com",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        env_vars = {
            "ALITHIA_EMAIL": "env@example.com",
            "ALITHIA_RESEARCH_INTERESTS": "AI,ML,CV",
        }

        with mock.patch.dict(os.environ, env_vars, clear=True):
            config = load_config(temp_path)

            # Environment overrides for email
            assert config["email"] == "env@example.com"

            # Environment overrides for research interests
            assert config["research_interests"] == ["AI", "ML", "CV"]

            # File values for non-overridden keys
            assert config["expertise_level"] == "beginner"
            assert config["language"] == "English"
    finally:
        os.unlink(temp_path)


@pytest.mark.unit
def test_load_config_arxrec_settings():
    """Test loading arxrec-specific settings."""
    config_data = {
        "arxrec": {
            "query": "cs.AI+cs.CV",
            "max_papers": 50,
            "send_empty": False,
            "ignore_patterns": ["pattern1", "pattern2"],
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        env_vars = {
            "ALITHIA_ARXIV_QUERY": "cs.LG",
            "ALITHIA_MAX_PAPER_NUM": "100",
            "ALITHIA_SEND_EMPTY": "true",
            "ALITHIA_ZOTERO_IGNORE": "ignore1,ignore2",
        }

        with mock.patch.dict(os.environ, env_vars, clear=False):
            config = load_config(temp_path)

            assert config["arxrec"]["query"] == "cs.LG"
            assert config["arxrec"]["max_papers"] == 100
            assert config["arxrec"]["send_empty"] is True
            assert config["arxrec"]["ignore_patterns"] == ["ignore1", "ignore2"]
    finally:
        os.unlink(temp_path)


@pytest.mark.unit
def test_load_config_with_whitespace_in_lists():
    """Test that list conversion handles whitespace correctly."""
    env_vars = {
        "ALITHIA_RESEARCH_INTERESTS": "  AI  ,  Machine Learning  ,  Computer Vision  ",
        "ALITHIA_ZOTERO_IGNORE": "  pattern1  ,  pattern2  ",
    }

    with tempfile.TemporaryDirectory():
        with mock.patch.dict(os.environ, env_vars, clear=False):
            config = _build_config_from_envs()

            # Whitespace should be stripped
            assert config["research_interests"] == ["AI", "Machine Learning", "Computer Vision"]
            assert config["arxrec"]["ignore_patterns"] == ["pattern1", "pattern2"]


@pytest.mark.unit
def test_load_config_empty_list_handling():
    """Test that empty lists in env are handled correctly."""
    env_vars = {
        "ALITHIA_RESEARCH_INTERESTS": "",  # Empty string should be treated as None
        "ALITHIA_ZOTERO_IGNORE": "   ,   ,   ",  # Only whitespace should result in empty list
    }

    with tempfile.TemporaryDirectory():
        with mock.patch.dict(os.environ, env_vars, clear=False):
            config = _build_config_from_envs()

            # Empty research interests should not be in config
            assert "research_interests" not in config

            # Whitespace-only patterns should result in empty list
            assert config["arxrec"]["ignore_patterns"] == []
