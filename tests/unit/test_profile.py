import pytest

from alithia.core.researcher.connected import (
    EmailConnection,
    GithubConnection,
    GoogleScholarConnection,
    LLMConnection,
    XConnection,
    ZoteroConnection,
)
from alithia.core.researcher.profile import ResearcherProfile


@pytest.mark.unit
def test_profile_from_config_defaults_and_values():
    cfg = {
        "email": "test@example.com",
        "research_interests": ["AI"],
        "expertise_level": "advanced",
        "language": "English",
        "zotero": {
            "zotero_id": "zid",
            "zotero_key": "zkey",
        },
        "llm": {
            "openai_api_key": "ok",
            "openai_api_base": "http://base",
            "model_name": "gpt-x",
        },
        "email_notification": {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "sender": "sender@example.com",
            "sender_password": "pass",
            "receiver": "recv@example.com",
        },
        "github": {
            "github_username": "test_user",
            "github_token": "test_token",
        },
        "google_scholar": {
            "google_scholar_id": "test_id",
            "google_scholar_token": "test_token",
        },
        "x": {
            "x_username": "test_user",
            "x_token": "test_token",
        },
    }
    p = ResearcherProfile.from_config(cfg)

    assert p.email == "test@example.com"
    assert p.research_interests == ["AI"]
    assert p.expertise_level == "advanced"
    assert p.language == "English"
    assert p.zotero.zotero_id == "zid"
    assert p.zotero.zotero_key == "zkey"
    assert p.llm.openai_api_key == "ok"
    assert p.llm.model_name == "gpt-x"


@pytest.mark.unit
def test_profile_validate_missing_fields():
    # Test that creating a profile with missing required fields raises validation error
    with pytest.raises(Exception):
        p = ResearcherProfile(
            # Missing email field
            zotero=ZoteroConnection(zotero_id="test_id", zotero_key="test_key"),
            llm=LLMConnection(
                openai_api_key="test_key", openai_api_base="https://api.openai.com/v1", model_name="gpt-4o"
            ),
            email_notification=EmailConnection(
                smtp_server="smtp.test.com",
                smtp_port=587,
                sender="test@example.com",
                sender_password="test_pass",
                receiver="test@example.com",
            ),
            github=GithubConnection(github_username="test_user", github_token="test_token"),
            google_scholar=GoogleScholarConnection(google_scholar_id="test_id", google_scholar_token="test_token"),
            x=XConnection(x_username="test_user", x_token="test_token"),
        )


@pytest.mark.unit
def test_profile_validate_llm_requires_key():
    # Test that creating a profile with missing LLM connection raises validation error
    with pytest.raises(Exception):
        p = ResearcherProfile(
            email="test@example.com",
            zotero=ZoteroConnection(zotero_id="a", zotero_key="b"),
            # Missing llm field
            email_notification=EmailConnection(
                smtp_server="smtp.test.com",
                smtp_port=587,
                sender="test@example.com",
                sender_password="pass",
                receiver="test@example.com",
            ),
            github=GithubConnection(github_username="test_user", github_token="test_token"),
            google_scholar=GoogleScholarConnection(google_scholar_id="test_id", google_scholar_token="test_token"),
            x=XConnection(x_username="test_user", x_token="test_token"),
        )
