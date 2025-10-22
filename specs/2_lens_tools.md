Of course. Here is a detailed design document for the core tools of the Alithia Lens Agent.
Alithia Lens Agent: Core Toolset Design Document
This document outlines the design for a set of fundamental tools for the Alithia Lens Agent, an AI research assistant. The tools are designed to be modular, robust, and chainable, forming the foundation for complex research workflows.
1. Tool: core.pdf_parser
Objective
To perform a deep parse of a research paper PDF, extracting not just text, but all semantically meaningful elements into a structured, machine-readable format. This structured data is the primary input for most other agent tools.
Inputs
 * file_path: str: The local path to the PDF file.
Outputs
 * structured_paper: JSON or a Python dataclass object with the following schema:
<!-- end list -->
{
  "paper_id": "UUID generated on ingestion",
  "metadata": {
    "title": "string",
    "authors": [
      { "name": "string", "affiliation": "string", "email": "string" }
    ],
    "abstract": "string",
    "publication_date": "string (ISO 8601)",
    "journal_or_conference": "string",
    "keywords": ["list", "of", "strings"]
  },
  "sections": [
    {
      "section_number": "string (e.g., '1', '2.1')",
      "title": "string",
      "content": [
        {
          "element_id": "unique_id (e.g., 'para_001')",
          "type": "paragraph",
          "text": "string containing the paragraph text.",
          "citations": [
            { "key": "[1]", "text": "Author et al. (2023)" }
          ]
        },
        {
          "element_id": "fig_001",
          "type": "figure",
          "label": "Figure 1",
          "image_path": "/path/to/extracted/figure1.png",
          "caption": "string containing the figure caption.",
          "in_text_reference": "As shown in Figure 1..."
        },
        {
          "element_id": "tbl_001",
          "type": "table",
          "label": "Table 1",
          "caption": "string containing the table caption.",
          "data_csv": "string in CSV format",
          "data_json": "list of lists or list of dicts"
        },
        {
          "element_id": "eq_001",
          "type": "equation",
          "label": "(1)",
          "latex_code": "E = mc^2",
          "image_path": "/path/to/extracted/equation1.png"
        },
        {
          "element_id": "alg_001",
          "type": "algorithm",
          "label": "Algorithm 1",
          "caption": "The training process for our model.",
          "pseudocode": "string of the formatted pseudocode"
        }
      ]
    }
  ],
  "bibliography": [
    {
      "ref_id": "[1]",
      "full_citation": "string of the full reference."
    }
  ]
}

Core Components & Logic
 * Text and Layout Extraction: Use a library like PyMuPDF or pdfplumber to extract raw text blocks with their coordinates (x\_0, y\_0, x\_1, y\_1). This preserves reading order in multi-column layouts.
 * Multimodal Document Analysis (Primary Engine): Employ a powerful multimodal model (like Google's Gemini) with visual processing capabilities.
   * The model receives images of each page.
   * It performs Layout Analysis to identify and segment regions: paragraphs, tables, figures, headers, footers, etc.
   * It performs Optical Character Recognition (OCR) on the entire page, associating text with the identified segments.
 * Element-Specific Extraction:
   * Figures/Tables: Detected regions are cropped and saved as images. The associated text below or above is identified as the caption.
   * Equations: A specialized model like nougat (or the vision capabilities of a general model) is used to detect equations and convert them from images to LaTeX strings.
   * Algorithms: These are identified by keywords ("Algorithm", "Pseudocode") and their distinct formatting. The text content is extracted and cleaned.
   * Bibliography Parsing: The final section, typically "References", is parsed using a tool like Anystyle or custom regex to structure each entry.
 * Structuring and Linking: The tool reassembles the extracted elements into the final JSON structure, ensuring element_ids are unique and references within the text are linked to the bibliography.
Challenges & Considerations
 * Complex Layouts: Papers with figures spanning multiple columns or text wrapping around figures are challenging. Multimodal models are essential here.
 * Table Parsing: Converting complex tables (with merged cells, multi-line headers) into a structured format (CSV/JSON) is non-trivial.
 * Reference Style Diversity: Citation formats vary wildly (e.g., [1], (Author, 2023)). The system must be robust to different styles.
2. Tool: core.web_searcher
Objective
To act as the agent's connection to the live web, capable of finding papers, profiling researchers, and initiating deeper research sprints. This tool will heavily rely on the cogents library's web search functionalities.
Sub-Tools / Functions
 * find_paper_info(title: str, authors: list[str] = None)
   * Objective: Find metadata and a downloadable PDF link for a given paper.
   * Logic:
     * Query academic APIs in a waterfall sequence: Google Scholar, Semantic Scholar, arXiv, CrossRef API.
     * Prioritize results with open-access PDF links (e.g., from arXiv, institutional repositories).
     * If no direct link is found, perform a general web search for "{title}" filetype:pdf.
     * Parse the retrieved information into the structured_paper.metadata format.
   * Output: A dictionary containing metadata and a pdf_url if found.
 * find_author_profile(author_name: str, affiliation: str = None)
   * Objective: Build a profile of a researcher.
   * Logic:
     * Construct search queries like "{author_name}" "{affiliation}", "{author_name}" Google Scholar, "{author_name}" publications.
     * Prioritize official sources: Google Scholar profiles, university faculty pages, personal academic websites.
     * Use NLP to extract key information: Research Interests, recent publications list, contact information, links to projects.
   * Output: A dictionary with keys like research_interests, publications, homepage_url, scholar_profile_url.
 * discover_related_work(paper_title: str, abstract: str)
   * Objective: Given a seed paper, find a list of highly relevant related papers.
   * Logic:
     * Keyword Extraction: Use a language model (e.g., Gemini) to extract key concepts, methods, and terms from the title and abstract.
     * Seed Search: Use the extracted keywords to search academic databases (via find_paper_info).
     * Citation Chaining: For the most relevant initial results, fetch their references and the papers that cite them ("forward and backward search"). This creates a citation network.
     * Deep Dive (Optional Trigger): For a comprehensive analysis, this tool can trigger the cogents.deep_research_agent, which would autonomously perform the citation chaining, summarize findings, and synthesize a literature review.
   * Output: A list of paper metadata dictionaries, ranked by relevance.
3. Tool: core.reference_linker
Objective
To find and resolve all bibliographic references mentioned within a specific text snippet or related to a given topic from a parsed paper.
Inputs
 * source_paper: structured_paper: The full parsed data from the core.pdf_parser.
 * query: str: Can be either a direct quote/paragraph from the paper or a topic string (e.g., "the section on dataset statistics").
Outputs
 * list[dict]: A list of reference objects from the bibliography section of the source_paper that are relevant to the query. Each dict contains ref_id and full_citation.
Core Components & Logic
 * Create Reference Map: On initialization, the tool creates a hash map from the source_paper.bibliography list, mapping ref_id (e.g., [1]) to the full citation object.
 * Query Mode Detection: Determine if the query is a direct snippet or a topic.
   * Snippet Mode: If the query is a direct quote, use regex to find all citation patterns (e.g., \[\d+\], \(\w+ et al\., \d{4}\)). For each found key, look it up in the reference map.
   * Topic Mode: If the query is a topic, perform a semantic search (using vector embeddings) over all paragraph elements in the source_paper.sections.
     * Identify the top N most relevant paragraphs.
     * Extract the citation keys from the citations field of these paragraphs.
     * Look up these keys in the reference map.
 * De-duplication & Return: Collect all unique references found and return them as a list.
Example Usage
# Assume 'parsed_paper' is the output from core.pdf_parser
input_paragraph = "Our method builds upon the attention mechanism [3] and recent advances in transformer architectures [4, 5]."
references = agent.tools.core.reference_linker(source_paper=parsed_paper, query=input_paragraph)
# 'references' would contain the full bibliographic entries for [3], [4], and [5].

4. Tool: core.code_generator
Objective
To translate algorithmic pseudocode from a research paper into executable Python code, using contextual information from the paper and illustrative figures to resolve ambiguities.
Inputs
 * pseudocode_element: dict: The algorithm object extracted by core.pdf_parser (containing label, caption, and the pseudocode string).
 * source_paper: structured_paper: The full parsed data of the paper, to provide context.
 * related_elements: list[dict] = None: A list of related elements, such as figures illustrating the algorithm's inputs/outputs or tables with example data.
Outputs
 * generated_code: str: A string containing the generated Python code, complete with comments explaining the implementation choices.
Core Components & Logic
 * Context Aggregation: The tool constructs a detailed prompt for a powerful code-generation LLM (e.g., Gemini). The prompt includes:
   * Primary Instruction: "You are an expert programmer. Convert the following pseudocode into functional Python code. Use standard libraries like NumPy, PyTorch, or TensorFlow where appropriate."
   * The Pseudocode: The pseudocode string from the input element.
   * Algorithm Context: The caption of the algorithm and the text from the surrounding paragraphs in the source_paper. This explains what the variables are and the purpose of the algorithm.
   * Visual Context (if available): If related_elements contains figures, a multimodal model will analyze them. The prompt will include descriptions like: "The input is an image of shape (256, 256, 3) as shown in Figure 2. The output should be a segmentation mask as shown in Figure 3."
   * Library Hints: The tool can scan the paper's text for mentions of specific libraries ("implemented in PyTorch") to guide the model.
 * Code Generation: The LLM processes the rich prompt and generates the Python code.
 * Refinement and Validation (Optional):
   * The generated code is passed through a linter (ruff or pylint) and a formatter (black) for quality control.
   * A simple sandbox execution can be attempted to catch immediate NameError or SyntaxError exceptions, though semantic correctness is not guaranteed.
Challenges & Considerations
 * High Ambiguity: This is the most challenging and heuristic-based tool. Pseudocode often omits critical details (e.g., data structures, tensor dimensions, hyperparameters).
 * Not a "Compiler": The output is a best-effort translation, not a guaranteed-to-work program. It serves as a strong starting point for a human researcher to adapt and debug. The agent must frame the output with this caveat.
