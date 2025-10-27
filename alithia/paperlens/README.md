# paperlens

A powerful research paper discovery tool that uses semantic similarity to find the most relevant papers for your research topic.

## Features

- 📄 **PDF Parsing**: Uses docling library to extract structured content from academic PDFs
- 🧠 **Semantic Matching**: Leverages sentence-transformers for intelligent similarity scoring
- 📊 **Structured Data Model**: Comprehensive data model for paper metadata and content
- 🔍 **Smart Ranking**: Ranks papers by relevance to your research topic
- ⚡ **Batch Processing**: Efficiently processes directories of papers

## Installation

Install paperlens with its dependencies:

```bash
pip install 'alithia[paperlens,extra]'
```

## Usage

### Basic Usage

1. Create a text file with your research topic (paragraph or snippet)
2. Place your PDF papers in a directory
3. Run paperlens:

```bash
python -m alithia.paperlens -i research_topic.txt -d ./papers
```

### Command Line Options

```
-i, --input FILE          Input file containing research topic (required)
-d, --directory DIR       Directory containing PDF papers (required)
-n, --top-n N            Number of top papers to display (default: 10)
--model MODEL            Sentence transformer model to use (default: all-MiniLM-L6-v2)
--no-recursive           Don't search subdirectories for PDFs
-v, --verbose            Enable verbose logging
```

### Examples

Find top 10 papers:
```bash
python -m alithia.paperlens -i topic.txt -d ./papers
```

Find top 20 papers with verbose output:
```bash
python -m alithia.paperlens -i topic.txt -d ./papers -n 20 -v
```

Use a more powerful model:
```bash
python -m alithia.paperlens -i topic.txt -d ./papers --model all-mpnet-base-v2
```

## Architecture

### Paper Reference Seeking

Given a paragraph or snippet of research topic, and a collection of PDF papers,
scan and find most related papers related to given research topic.

Components:
- PDF parsing with docling
- Topic extraction and semantic matching with sentence-transformers
- Text similarity calculation using cosine similarity
- Structured data models for papers

---

## 🧩 **Compact Deep Reading Structure (10 fields max)**

1. **📘 Basic Info**
   *Title, Authors, Year, Field / Topic*

2. **🎯 Core Question / Problem**
   *What key question or gap does this paper address?*

3. **💡 Main Idea / Thesis**
   *The central claim or insight — one sentence summary.*

4. **⚙️ Approach / Method**
   *How the authors tackled it (theoretical, empirical, model, framework, experiment, etc.)*

5. **🔍 Key Findings / Results**
   *What did they discover or prove?*

6. **🧠 Insight / Contribution**
   *Why it matters — conceptual or practical significance.*

7. **⚖️ Limitations / Critique**
   *Weaknesses, assumptions, or potential biases.*

8. **🔗 Relations**
   *How it connects — prior work, successor ideas, or cross-domain links.*

9. **🪞 Reflection / Takeaway**
   *Your distilled understanding, implication, or question raised.*

10. **🧭 Keywords / Tags**
    *Concepts for indexing (e.g., “causal inference”, “embodied cognition”, “agent modeling”).*

---

### Example (filled)

| Field             | Example Entry                                                           |
| ----------------- | ----------------------------------------------------------------------- |
| **Title**         | “The Role of Mental Simulation in Human Planning”                       |
| **Core Question** | How do humans use mental simulation to plan future actions?             |
| **Main Idea**     | Humans plan by running internal forward models of action outcomes.      |
| **Approach**      | Behavioral experiments + computational modeling.                        |
| **Key Findings**  | Planning accuracy correlates with the fidelity of internal simulations. |
| **Insight**       | Supports the view of cognition as predictive simulation.                |
| **Limitations**   | Lab-based tasks; unclear neural implementation.                         |
| **Relations**     | Builds on predictive coding; connects to model-based RL.                |
| **Reflection**    | Suggests bridging human planning and AI world models.                   |
| **Tags**          | cognitive modeling, planning, simulation, prediction                    |

---

### Optional “3-Layer Mental Model”

If you want an even quicker mnemonic:

> **Q–A–I**
>
> * **Q:** What question is asked?
> * **A:** How is it answered?
> * **I:** What insight emerges?

Everything else (metadata, critique, connection) hangs off that spine.
