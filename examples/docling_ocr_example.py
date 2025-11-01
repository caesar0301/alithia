#!/usr/bin/env python3
"""
Basic example demonstrating how to use DoclingOCR to parse PDF files.

This example shows:
1. Basic PDF parsing without LLM
2. Enhanced parsing with LLM for metadata extraction
3. Displaying extracted information
"""

import json
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cogents_core.llm import get_llm_client

from alithia.paperlens.paper_ocr.docling_ocr import DoclingOCR


def print_separator(title: str = None):
    """Print a formatted separator line."""
    if title:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}\n")
    else:
        print(f"{'=' * 70}\n")


def display_paper_info(paper):
    """Display extracted paper information in a formatted way."""
    if paper is None:
        print("❌ Failed to parse PDF")
        return

    print_separator("FILE METADATA")
    print(f"📄 File Name: {paper.file_metadata.file_name}")
    print(f"📦 File Size: {paper.file_metadata.file_size / 1024:.2f} KB")
    print(f"🕒 Last Modified: {paper.file_metadata.last_modified}")
    print(f"🔐 MD5 Hash: {paper.file_metadata.md5_hash}")
    print(f"⏱️  Parse Timestamp: {paper.parse_timestamp}")

    print_separator("PAPER METADATA")
    meta = paper.paper_metadata
    print(f"📌 Title: {meta.title or 'Not extracted'}")
    print(f"\n👥 Authors ({len(meta.authors)}):")
    if meta.authors:
        for i, author in enumerate(meta.authors, 1):
            print(f"   {i}. {author}")
    else:
        print("   Not extracted")

    print(f"\n📅 Year: {meta.year or 'Not extracted'}")
    print(f"🔖 DOI: {meta.doi or 'Not extracted'}")
    print(f"🏛️  Venue: {meta.venue or 'Not extracted'}")
    print(f"🏷️  Field/Topic: {meta.field_topic or 'Not extracted'}")

    print(f"\n🏷️  Keywords ({len(meta.keywords)}):")
    if meta.keywords:
        print(f"   {', '.join(meta.keywords)}")
    else:
        print("   Not extracted")

    print(f"\n📝 Abstract ({len(meta.abstract) if meta.abstract else 0} characters):")
    if meta.abstract:
        # Display first 300 characters
        abstract_preview = meta.abstract[:300]
        if len(meta.abstract) > 300:
            abstract_preview += "..."
        print(f"   {abstract_preview}")
    else:
        print("   Not extracted")

    print_separator("CONTENT STATISTICS")
    content = paper.content
    print(f"📖 Full Text Length: {len(content.full_text):,} characters")
    print(f"📑 Sections: {len(content.sections)}")
    print(f"📚 References: {len(content.references)}")
    print(f"🖼️  Figures: {len(content.figures)}")
    print(f"📊 Tables: {len(content.tables)}")

    if paper.parsing_errors:
        print_separator("PARSING ERRORS")
        for i, error in enumerate(paper.parsing_errors, 1):
            print(f"   {i}. {error}")

    print_separator()


def example_llm_enhanced_parsing(pdf_path: Path):
    """
    Example 2: Enhanced PDF parsing with LLM.
    If docling doesn't extract complete metadata, LLM will fill in the gaps.

    Note: Requires OPENAI_API_KEY environment variable to be set.
    """
    print("\n🔍 EXAMPLE 2: Enhanced PDF Parsing (with LLM)")
    print_separator()

    try:
        # Initialize DoclingOCR with LLM
        print("Initializing DoclingOCR (with LLM)...")
        ocr = DoclingOCR(llm=get_llm_client(provider="openrouter"))
        print("✅ DoclingOCR initialized\n")

        # Parse the PDF
        print(f"Parsing PDF: {pdf_path.name}")
        print("(If docling metadata is incomplete, LLM will enhance it)\n")
        paper = ocr.parse_pdf(pdf_path)

        # Display results
        display_paper_info(paper)

        return paper

    except Exception as e:
        print(f"❌ Error in LLM-enhanced parsing: {e}")
        import traceback

        traceback.print_exc()
        return None


def example_save_to_json(paper, output_path: Path):
    """
    Example 3: Save parsed paper data to JSON file.
    """
    if paper is None:
        print("⚠️  No paper data to save")
        return

    print(f"\n💾 Saving parsed data to JSON: {output_path}")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(paper.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ Successfully saved to {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024:.2f} KB")
    except Exception as e:
        print(f"❌ Failed to save JSON: {e}")


def main():
    """Main function to run the examples."""
    print("=" * 70)
    print("  DoclingOCR Example - PDF Parsing Demonstration")
    print("=" * 70)

    # Check if PDF path is provided
    if len(sys.argv) < 2:
        print("\n⚠️  Usage: python docling_ocr_example.py <path_to_pdf>")
        return

    # Get PDF path from command line
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"\n❌ Error: PDF file not found: {pdf_path}")
        return

    # Example 2: Try LLM-enhanced parsing (will fail gracefully if no API key)
    paper_enhanced = example_llm_enhanced_parsing(pdf_path)

    # Example 3: Save enhanced result to JSON
    if paper_enhanced:
        output_path = pdf_path.parent / f"{pdf_path.stem}_parsed_enhanced.json"
        example_save_to_json(paper_enhanced, output_path)

    print("\n✅ All examples completed!")


if __name__ == "__main__":
    main()
