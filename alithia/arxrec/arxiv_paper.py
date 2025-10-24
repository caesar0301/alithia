import re
import tarfile
from contextlib import ExitStack
from datetime import datetime
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError

import arxiv
import feedparser
import requests
import tiktoken
from cogents_core.llm import BaseLLMClient
from cogents_core.utils import get_logger
from pydantic import BaseModel, Field
from requests.adapters import HTTPAdapter, Retry

logger = get_logger(__name__)


class ArxivPaper(BaseModel):
    """Represents an ArXiv paper with all relevant metadata."""

    title: str
    summary: str
    authors: List[str]
    arxiv_id: str
    pdf_url: str
    code_url: Optional[str] = None
    affiliations: Optional[List[str]] = None
    tldr: Optional[str] = None
    score: Optional[float] = None
    published_date: Optional[datetime] = None
    tex: Optional[Dict[str, str]] = None  # Store extracted LaTeX content
    arxiv_result: Optional[Any] = Field(
        default=None, exclude=True
    )  # Store original arxiv.Result object for source access

    @classmethod
    def from_arxiv_result(cls, paper_result) -> "ArxivPaper":
        """Create ArxivPaper from arxiv.Result object."""
        arxiv_id = re.sub(r"v\d+$", "", paper_result.get_short_id())

        # Validate that we have essential fields
        if not paper_result.title or not paper_result.summary:
            logger.warning(f"Skipping paper with missing title or summary: {arxiv_id}")
            return None

        return cls(
            title=paper_result.title.strip(),
            summary=paper_result.summary.strip(),
            authors=[author.name for author in paper_result.authors],
            arxiv_id=arxiv_id,
            pdf_url=paper_result.pdf_url,
            published_date=paper_result.published,
            arxiv_result=paper_result,  # Store the original result object
        )

    def download_source(self, dirpath: str) -> str:
        """Download source files for the paper."""
        if self.arxiv_result is None:
            raise AttributeError("Cannot download source: no arxiv_result available")
        return self.arxiv_result.download_source(dirpath=dirpath)

    def process(self, llm: BaseLLMClient) -> None:
        """Process the paper."""
        try:
            if not self.tldr:
                self.tldr = self._generate_tldr(llm)
        except Exception as e:
            logger.warning(f"Failed to generate TLDR for {self.arxiv_id}: {str(e)}")
            self.tldr = "TLDR generation failed"

        try:
            if not self.affiliations:
                self.affiliations = self._extract_affiliations(llm)
        except Exception as e:
            logger.warning(f"Failed to extract affiliations for {self.arxiv_id}: {str(e)}")
            self.affiliations = []

        try:
            if not self.code_url:
                self.code_url = self._get_code_url()
        except Exception as e:
            logger.warning(f"Failed to get code URL for {self.arxiv_id}: {str(e)}")
            self.code_url = None

    def _extract_tex_content(self) -> Optional[Dict[str, str]]:
        """
        Extract LaTeX content from paper source.

        Args:
            paper: ArxivPaper instance

        Returns:
            Dictionary with extracted LaTeX content or None if extraction fails
        """
        with ExitStack() as stack:
            tmpdirname = stack.enter_context(TemporaryDirectory())
            try:
                file = self.download_source(dirpath=tmpdirname)
            except (HTTPError, AttributeError) as e:
                if isinstance(e, HTTPError) and e.code == 404:
                    logger.warning(f"Source for {self.arxiv_id} not found (404). Skipping source analysis.")
                    return None
                elif isinstance(e, AttributeError):
                    logger.warning(f"No arxiv_result available for {self.arxiv_id}. Skipping source analysis.")
                    return None
                else:
                    logger.error(f"HTTP Error {e.code} when downloading source for {self.arxiv_id}: {e.reason}")
                    raise
            try:
                tar = stack.enter_context(tarfile.open(file))
            except tarfile.ReadError:
                logger.debug(f"Failed to find main tex file of {self.arxiv_id}: Not a tar file.")
                return None

            tex_files = [f for f in tar.getnames() if f.endswith(".tex")]
            if len(tex_files) == 0:
                logger.debug(f"Failed to find main tex file of {self.arxiv_id}: No tex file.")
                return None

            bbl_file = [f for f in tar.getnames() if f.endswith(".bbl")]
            match len(bbl_file):
                case 0:
                    if len(tex_files) > 1:
                        logger.debug(
                            f"Cannot find main tex file of {self.arxiv_id} from bbl: There are multiple tex files while no bbl file."
                        )
                        main_tex = None
                    else:
                        main_tex = tex_files[0]
                case 1:
                    main_name = bbl_file[0].replace(".bbl", "")
                    main_tex = f"{main_name}.tex"
                    if main_tex not in tex_files:
                        logger.debug(
                            f"Cannot find main tex file of {self.arxiv_id} from bbl: The bbl file does not match any tex file."
                        )
                        main_tex = None
                case _:
                    logger.debug(
                        f"Cannot find main tex file of {self.arxiv_id} from bbl: There are multiple bbl files."
                    )
                    main_tex = None
            if main_tex is None:
                logger.debug(
                    f"Trying to choose tex file containing the document block as main tex file of {self.arxiv_id}"
                )

            # read all tex files
            file_contents = {}
            for t in tex_files:
                f = tar.extractfile(t)
                content = f.read().decode("utf-8", errors="ignore")
                # remove comments
                content = re.sub(r"%.*\n", "\n", content)
                content = re.sub(r"\\begin{comment}.*?\\end{comment}", "", content, flags=re.DOTALL)
                content = re.sub(r"\\iffalse.*?\\fi", "", content, flags=re.DOTALL)
                # remove redundant \n
                content = re.sub(r"\n+", "\n", content)
                content = re.sub(r"\\\\", "", content)
                # remove consecutive spaces
                content = re.sub(r"[ \t\r\f]{3,}", " ", content)
                if main_tex is None and re.search(r"\\begin\{document\}", content):
                    main_tex = t
                    logger.debug(f"Choose {t} as main tex file of {self.arxiv_id}")
                file_contents[t] = content

            if main_tex is not None:
                main_source: str = file_contents[main_tex]
                # find and replace all included sub-files
                include_files = re.findall(r"\\input\{(.+?)\}", main_source) + re.findall(
                    r"\\include\{(.+?)\}", main_source
                )
                for f in include_files:
                    if not f.endswith(".tex"):
                        file_name = f + ".tex"
                    else:
                        file_name = f
                    main_source = main_source.replace(f"\\input{{{f}}}", file_contents.get(file_name, ""))
                file_contents["all"] = main_source
            else:
                logger.debug(
                    f"Failed to find main tex file of {self.arxiv_id}: No tex file containing the document block."
                )
                file_contents["all"] = None
        return file_contents

    def _generate_tldr(self, llm: BaseLLMClient) -> str:
        """
        Generate TLDR summary for a paper.

        Args:
            paper: ArxivPaper to summarize
            llm: LLM instance for generation

        Returns:
            TLDR summary string
        """
        introduction = ""
        conclusion = ""
        if self.tex is not None:
            content = self.tex.get("all")
            if content is None:
                content = "\n".join(self.tex.values())
            # remove cite
            content = re.sub(r"~?\\cite.?\{.*?\}", "", content)
            # remove figure
            content = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "", content, flags=re.DOTALL)
            # remove table
            content = re.sub(r"\\begin\{table\}.*?\\end\{table\}", "", content, flags=re.DOTALL)
            # find introduction and conclusion
            # end word can be \section or \end{document} or \bibliography or \appendix
            match = re.search(
                r"\\section\{Introduction\}.*?(\\section|\\end\{document\}|\\bibliography|\\appendix|$)",
                content,
                flags=re.DOTALL,
            )
            if match:
                introduction = match.group(0)
            match = re.search(
                r"\\section\{Conclusion\}.*?(\\section|\\end\{document\}|\\bibliography|\\appendix|$)",
                content,
                flags=re.DOTALL,
            )
            if match:
                conclusion = match.group(0)

        prompt = """Given the title, abstract, introduction and the conclusion (if any) of a paper in latex format, generate a one-sentence TLDR summary in __LANG__:
        
        \\title{__TITLE__}
        \\begin{abstract}__ABSTRACT__\\end{abstract}
        __INTRODUCTION__
        __CONCLUSION__
        """
        # Get language from LLM or default to English
        lang = getattr(llm, "lang", "English")
        if hasattr(lang, "__call__"):  # If it's a Mock or callable, use default
            lang = "English"
        prompt = prompt.replace("__LANG__", lang)
        prompt = prompt.replace("__TITLE__", self.title)
        prompt = prompt.replace("__ABSTRACT__", self.summary)
        prompt = prompt.replace("__INTRODUCTION__", introduction)
        prompt = prompt.replace("__CONCLUSION__", conclusion)

        # use gpt-4o tokenizer for estimation
        enc = tiktoken.encoding_for_model("gpt-4o")
        prompt_tokens = enc.encode(prompt)
        prompt_tokens = prompt_tokens[:4000]  # truncate to 4000 tokens
        prompt = enc.decode(prompt_tokens)

        tldr = llm.completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistant who perfectly summarizes scientific paper, and gives the core idea of the paper to the user.",
                },
                {"role": "user", "content": prompt},
            ]
        )
        return tldr

    def _extract_affiliations(self, llm) -> Optional[List[str]]:
        """
        Extract author affiliations from paper.

        Args:
            paper: ArxivPaper to analyze
            llm: LLM instance for extraction

        Returns:
            List of affiliations or None if extraction fails
        """
        # First try to get tex content from paper.tex, then fall back to extract_tex_content
        tex_content = self.tex
        if tex_content is None:
            tex_content = self._extract_tex_content()
            # If we got content from extract_tex_content, store it in paper.tex for future use
            if tex_content is not None:
                self.tex = tex_content

        if tex_content is not None:
            content = tex_content.get("all")
            if content is None:
                content = "\n".join(tex_content.values())
            # search for affiliations
            possible_regions = [r"\\author.*?\\maketitle", r"\\begin{document}.*?\\begin{abstract}"]
            matches = [re.search(p, content, flags=re.DOTALL) for p in possible_regions]
            match = next((m for m in matches if m), None)
            if match:
                information_region = match.group(0)
            else:
                logger.debug(f"Failed to extract affiliations of {self.arxiv_id}: No author information found.")
                return None
            prompt = f"Given the author information of a paper in latex format, extract the affiliations of the authors in a python list format, which is sorted by the author order. If there is no affiliation found, return an empty list '[]'. Following is the author information:\n{information_region}"
            # use gpt-4o tokenizer for estimation
            enc = tiktoken.encoding_for_model("gpt-4o")
            prompt_tokens = enc.encode(prompt)
            prompt_tokens = prompt_tokens[:4000]  # truncate to 4000 tokens
            prompt = enc.decode(prompt_tokens)
            affiliations = llm.completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an assistant who perfectly extracts affiliations of authors from the author information of a paper. You should return a python list of affiliations sorted by the author order, like ['TsingHua University','Peking University']. If an affiliation is consisted of multi-level affiliations, like 'Department of Computer Science, TsingHua University', you should return the top-level affiliation 'TsingHua University' only. Do not contain duplicated affiliations. If there is no affiliation found, you should return an empty list [ ]. You should only return the final list of affiliations, and do not return any intermediate results.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )

            try:
                affiliations = re.search(r"\[.*?\]", affiliations, flags=re.DOTALL).group(0)
                affiliations = eval(affiliations)
                affiliations = list(set(affiliations))
                affiliations = [str(a) for a in affiliations]
            except Exception as e:
                logger.debug(f"Failed to extract affiliations of {self.arxiv_id}: {e}")
                return None
            return affiliations

    def _get_code_url(self) -> Optional[str]:
        """
        Find code repository URL for a paper.

        Args:
            paper: ArxivPaper to search for

        Returns:
            Code repository URL or None if not found
        """
        s = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1)
        s.mount("https://", HTTPAdapter(max_retries=retries))
        try:
            paper_list = s.get(f"https://paperswithcode.com/api/v1/papers/?arxiv_id={self.arxiv_id}").json()
        except Exception as e:
            logger.debug(f"Error when searching {self.arxiv_id}: {e}")
            return None

        if paper_list.get("count", 0) == 0:
            return None
        paper_id = paper_list["results"][0]["id"]

        try:
            repo_list = s.get(f"https://paperswithcode.com/api/v1/papers/{paper_id}/repositories/").json()
        except Exception as e:
            logger.debug(f"Error when searching {self.arxiv_id}: {e}")
            return None
        if repo_list.get("count", 0) == 0:
            return None
        return repo_list["results"][0]["url"]


def get_arxiv_papers(arxiv_query: str, debug: bool = False) -> List[ArxivPaper]:
    """
    Retrieve papers from ArXiv based on query.

    Args:
        arxiv_query: ArXiv query string (e.g., "cs.AI+cs.CV")
        debug: If True, limit to 5 papers but still use the actual query

    Returns:
        List of ArxivPaper objects
    """
    client = arxiv.Client(num_retries=10, delay_seconds=10)

    if debug:
        # In debug mode, use the actual query but limit to 5 papers
        # Convert the query format for ArXiv API
        query_parts = arxiv_query.split("+")
        if len(query_parts) > 1:
            # For multiple categories, use OR logic
            formatted_query = " OR ".join([f"cat:{part}" for part in query_parts])
        else:
            formatted_query = f"cat:{arxiv_query}"

        logger.info(f"Debug mode: Using query '{formatted_query}'")
        search = arxiv.Search(query=formatted_query, sort_by=arxiv.SortCriterion.SubmittedDate, max_results=5)
        papers = []
        for p in client.results(search):
            paper = ArxivPaper.from_arxiv_result(p)
            if paper is not None:
                papers.append(paper)
        return papers

    # Fetch papers from RSS feed
    feed = feedparser.parse(f"https://rss.arxiv.org/atom/{arxiv_query}")

    if "Feed error for query" in feed.feed.get("title", ""):
        raise ValueError(f"Invalid ARXIV_QUERY: {arxiv_query}")

    # Extract paper IDs from feed
    paper_ids = [
        entry.id.removeprefix("oai:arXiv.org:")
        for entry in feed.entries
        if hasattr(entry, "arxiv_announce_type") and entry.arxiv_announce_type == "new"
    ]

    if not paper_ids:
        return []

    # Fetch paper details in batches
    papers = []
    batch_size = 50

    for i in range(0, len(paper_ids), batch_size):
        batch_ids = paper_ids[i : i + batch_size]
        search = arxiv.Search(id_list=batch_ids)
        batch_papers = [ArxivPaper.from_arxiv_result(p) for p in client.results(search)]
        papers.extend(batch_papers)

    return papers
