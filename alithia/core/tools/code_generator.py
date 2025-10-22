from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from alithia.core.llm_utils import get_llm
from alithia.core.researcher.connected import (
    EmailConnection,
    GithubConnection,
    GoogleScholarConnection,
    LLMConnection,
    XConnection,
    ZoteroConnection,
)
from alithia.core.researcher.profile import ResearcherProfile

from .base import ToolInput, ToolOutput
from .models import StructuredPaper


class CodeGeneratorInput(ToolInput):
    pseudocode_element: Dict[str, Any]
    source_paper: StructuredPaper
    related_elements: Optional[List[Dict[str, Any]]] = None
    profile: Optional[ResearcherProfile] = None


class CodeGeneratorOutput(ToolOutput):
    generated_code: str


class CodeGeneratorTool(BaseTool):
    name: str = "core.code_generator"
    description: str = "Translate algorithmic pseudocode into executable Python using an LLM"
    args_schema: type[BaseModel] = CodeGeneratorInput

    def execute(self, inputs: CodeGeneratorInput, **kwargs: Any) -> CodeGeneratorOutput:
        profile = inputs.profile
        if profile is None:
            # Minimal default profile
            profile = ResearcherProfile(
                email="default@example.com",
                zotero=ZoteroConnection(zotero_id="", zotero_key=""),
                llm=LLMConnection(openai_api_key="", openai_api_base="https://api.openai.com/v1", model_name="gpt-4o"),
                email_notification=EmailConnection(
                    smtp_server="", smtp_port=587, sender="", sender_password="", receiver=""
                ),
                github=GithubConnection(github_username="", github_token=""),
                google_scholar=GoogleScholarConnection(google_scholar_id="", google_scholar_token=""),
                x=XConnection(x_username="", x_token=""),
            )
        llm = get_llm(profile)

        prompt_messages = self._build_prompt(inputs)
        response = self._send_llm(llm, prompt_messages)
        code = str(response).strip()
        return CodeGeneratorOutput(generated_code=code)

    # BaseTool sync run implementation (structured)
    def _run(self, pseudocode_element: Dict[str, Any], source_paper: StructuredPaper, related_elements: Optional[List[Dict[str, Any]]] = None, profile: Optional[ResearcherProfile] = None) -> CodeGeneratorOutput:  # type: ignore[override]
        return self.execute(
            CodeGeneratorInput(
                pseudocode_element=pseudocode_element,
                source_paper=source_paper,
                related_elements=related_elements,
                profile=profile,
            )
        )

    def _build_prompt(self, inputs: CodeGeneratorInput) -> List[Dict[str, str]]:
        pseudo = inputs.pseudocode_element.get("pseudocode") or inputs.pseudocode_element.get("text") or ""
        label = inputs.pseudocode_element.get("label") or "Algorithm"
        caption = inputs.pseudocode_element.get("caption") or ""

        # Gather simple context: first few paragraphs
        paragraphs: List[str] = []
        for section in inputs.source_paper.sections:
            for el in section.content[:3]:
                text = getattr(el, "text", None)
                if isinstance(text, str) and text:
                    paragraphs.append(text)
        context_block = "\n\n".join(paragraphs[:6])

        vis_hints = ""
        if inputs.related_elements:
            vis_hints = "\n\nVisual context hints (if any):\n" + "\n".join(
                [str(e.get("caption") or e.get("label") or e) for e in inputs.related_elements[:3]]
            )

        user_content = (
            "You are an expert programmer. Convert the following pseudocode into functional, idiomatic Python.\n"
            "Use NumPy/PyTorch/TensorFlow if appropriate. Include comments explaining key steps.\n\n"
            f"Label: {label}\n"
            f"Caption: {caption}\n\n"
            f"Pseudocode:\n{pseudo}\n\n"
            f"Context from paper:\n{context_block}{vis_hints}"
        )

        return [
            {
                "role": "system",
                "content": "You are AlithiaLens, a precise research assistant programmer.",
            },
            {"role": "user", "content": user_content},
        ]

    def _send_llm(self, llm: Any, messages: List[Dict[str, str]]) -> str:
        # Try common interfaces from cogents LLM
        if hasattr(llm, "generate"):
            return llm.generate(messages=messages)
        if hasattr(llm, "chat_completion"):
            return llm.chat_completion(messages=messages)
        # Fallback: try call
        return llm(messages)
