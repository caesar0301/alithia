from pydantic import BaseModel


class ZoteroConnection(BaseModel):
    """Zotero connection."""

    zotero_id: str
    zotero_key: str


class EmailConnection(BaseModel):
    """Email connection."""

    smtp_server: str
    smtp_port: int
    sender: str
    sender_password: str
    receiver: str


class GithubConnection(BaseModel):
    """Github connection."""

    github_username: str
    github_token: str


class GoogleScholarConnection(BaseModel):
    """Google Scholar connection."""

    google_scholar_id: str
    google_scholar_token: str


class XConnection(BaseModel):
    """X connection."""

    x_username: str
    x_token: str


class LLMConnection(BaseModel):
    """LLM connection."""

    openai_api_key: str
    openai_api_base: str
    model_name: str
