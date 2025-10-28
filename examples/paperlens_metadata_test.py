#!/usr/bin/env python3
"""
Comprehensive test script for PaperLensEngine metadata extraction accuracy.

This script tests the PaperLensEngine with real PDF papers and analyzes
the quality of metadata extraction to identify areas for improvement.
"""

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alithia.paperlens.engine import PaperLensEngine


class MetadataExtractionTester:
    """Test and analyze PaperLensEngine metadata extraction capabilities."""

    def __init__(self, papers_dir: Path, topic_file: Path):
        self.papers_dir = papers_dir
        self.topic_file = topic_file
        self.engine = None
        self.results = []

    def initialize_engine(self, model_name: str = "all-MiniLM-L6-v2", force_gpu: bool = False):
        """Initialize the PaperLens engine."""
        print(f"🚀 Initializing PaperLensEngine with model: {model_name}")
        try:
            self.engine = PaperLensEngine(sbert_model=model_name, force_gpu=force_gpu)
            print("✅ Engine initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize engine: {e}")
            traceback.print_exc()
            return False

    def load_research_topic(self) -> str:
        """Load the research topic from file."""
        try:
            with open(self.topic_file, "r", encoding="utf-8") as f:
                topic = f.read().strip()
            print(f"📝 Research topic loaded: {topic[:100]}...")
            return topic
        except Exception as e:
            print(f"❌ Failed to load research topic: {e}")
            return ""

    def test_single_pdf_parsing(self, pdf_path: Path) -> Dict[str, Any]:
        """Test parsing a single PDF and analyze metadata extraction."""
        print(f"\n🔍 Testing PDF: {pdf_path.name}")

        result = {
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "parsing_success": False,
            "metadata_quality": {},
            "extracted_metadata": {},
            "errors": [],
            "suggestions": [],
        }

        try:
            # Parse the PDF
            paper = self.engine.parse_pdf(pdf_path)

            if paper is None:
                result["errors"].append("Failed to parse PDF - returned None")
                return result

            result["parsing_success"] = True
            result["extracted_metadata"] = paper.to_dict()

            # Analyze metadata quality
            metadata = paper.paper_metadata
            quality = result["metadata_quality"]

            # Check title extraction
            quality["title_extracted"] = bool(metadata.title and metadata.title.strip())
            quality["title_length"] = len(metadata.title) if metadata.title else 0
            quality["title_quality"] = self._assess_title_quality(metadata.title)

            # Check authors extraction
            quality["authors_extracted"] = bool(metadata.authors and len(metadata.authors) > 0)
            quality["author_count"] = len(metadata.authors) if metadata.authors else 0
            quality["authors_quality"] = self._assess_authors_quality(metadata.authors)

            # Check year extraction
            quality["year_extracted"] = bool(metadata.year)
            quality["year_reasonable"] = self._assess_year_quality(metadata.year)

            # Check abstract extraction
            quality["abstract_extracted"] = bool(metadata.abstract and metadata.abstract.strip())
            quality["abstract_length"] = len(metadata.abstract) if metadata.abstract else 0
            quality["abstract_quality"] = self._assess_abstract_quality(metadata.abstract)

            # Check DOI extraction
            quality["doi_extracted"] = bool(metadata.doi and metadata.doi.strip())
            quality["doi_format"] = self._assess_doi_quality(metadata.doi)

            # Check keywords extraction
            quality["keywords_extracted"] = bool(metadata.keywords and len(metadata.keywords) > 0)
            quality["keyword_count"] = len(metadata.keywords) if metadata.keywords else 0

            # Check venue extraction
            quality["venue_extracted"] = bool(metadata.venue and metadata.venue.strip())

            # Check content extraction
            content = paper.content
            quality["content_extracted"] = bool(content.full_text and content.full_text.strip())
            quality["content_length"] = len(content.full_text) if content.full_text else 0
            quality["sections_extracted"] = bool(content.sections and len(content.sections) > 0)
            quality["references_extracted"] = bool(content.references and len(content.references) > 0)

            # Generate suggestions for improvement
            result["suggestions"] = self._generate_improvement_suggestions(quality, metadata, content)

            print(f"✅ Successfully parsed {pdf_path.name}")
            print(
                f"   Title: {'✅' if quality['title_extracted'] else '❌'} {metadata.title[:50] if metadata.title else 'None'}..."
            )
            print(f"   Authors: {'✅' if quality['authors_extracted'] else '❌'} {quality['author_count']} authors")
            print(f"   Year: {'✅' if quality['year_extracted'] else '❌'} {metadata.year}")
            print(f"   Abstract: {'✅' if quality['abstract_extracted'] else '❌'} {quality['abstract_length']} chars")
            print(f"   DOI: {'✅' if quality['doi_extracted'] else '❌'} {metadata.doi}")
            print(f"   Content: {'✅' if quality['content_extracted'] else '❌'} {quality['content_length']} chars")

        except Exception as e:
            error_msg = f"Error parsing {pdf_path.name}: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            traceback.print_exc()

        return result

    def _assess_title_quality(self, title: str) -> str:
        """Assess the quality of extracted title."""
        if not title:
            return "missing"

        title = title.strip()
        if len(title) < 10:
            return "too_short"
        elif len(title) > 200:
            return "too_long"
        elif title.isupper():
            return "all_caps"
        elif not any(c.isalpha() for c in title):
            return "no_letters"
        else:
            return "good"

    def _assess_authors_quality(self, authors: List[str]) -> str:
        """Assess the quality of extracted authors."""
        if not authors:
            return "missing"

        if len(authors) == 0:
            return "empty_list"
        elif len(authors) > 20:
            return "too_many"
        else:
            # Check if authors look reasonable
            valid_authors = 0
            for author in authors:
                if author and len(author.strip()) > 2 and any(c.isalpha() for c in author):
                    valid_authors += 1

            if valid_authors == 0:
                return "no_valid_authors"
            elif valid_authors < len(authors) * 0.5:
                return "many_invalid_authors"
            else:
                return "good"

    def _assess_year_quality(self, year: int) -> str:
        """Assess the quality of extracted year."""
        if not year:
            return "missing"

        if year < 1900:
            return "too_old"
        elif year > 2030:
            return "future_year"
        else:
            return "reasonable"

    def _assess_abstract_quality(self, abstract: str) -> str:
        """Assess the quality of extracted abstract."""
        if not abstract:
            return "missing"

        abstract = abstract.strip()
        if len(abstract) < 50:
            return "too_short"
        elif len(abstract) > 2000:
            return "too_long"
        elif abstract.isupper():
            return "all_caps"
        else:
            return "good"

    def _assess_doi_quality(self, doi: str) -> str:
        """Assess the quality of extracted DOI."""
        if not doi:
            return "missing"

        doi = doi.strip()
        if not doi.startswith("10."):
            return "invalid_format"
        elif len(doi) < 10:
            return "too_short"
        else:
            return "good"

    def _generate_improvement_suggestions(self, quality: Dict, metadata, content) -> List[str]:
        """Generate suggestions for improving metadata extraction."""
        suggestions = []

        if not quality["title_extracted"]:
            suggestions.append("Improve title extraction - consider using multiple extraction methods")

        if not quality["authors_extracted"]:
            suggestions.append("Enhance author extraction - check different document sections")

        if not quality["year_extracted"]:
            suggestions.append("Add year extraction from various sources (header, footer, references)")

        if not quality["abstract_extracted"]:
            suggestions.append("Improve abstract detection - look for specific patterns")

        if not quality["doi_extracted"]:
            suggestions.append("Add DOI extraction from references and metadata")

        if not quality["keywords_extracted"]:
            suggestions.append("Extract keywords from abstract, title, and content analysis")

        if not quality["venue_extracted"]:
            suggestions.append("Add venue/journal extraction from headers and references")

        if not quality["sections_extracted"]:
            suggestions.append("Implement section parsing for better content structure")

        if not quality["references_extracted"]:
            suggestions.append("Extract and parse reference list")

        return suggestions

    def test_similarity_calculation(self, research_topic: str) -> List[Dict[str, Any]]:
        """Test similarity calculation and ranking."""
        print(f"\n🎯 Testing similarity calculation for topic: {research_topic[:50]}...")

        try:
            # Scan all PDFs
            papers = self.engine.scan_pdf_directory(self.papers_dir, recursive=True)
            print(f"📚 Found {len(papers)} papers to analyze")

            if not papers:
                print("❌ No papers found to analyze")
                return []

            # Calculate similarities
            papers_with_scores = self.engine.calculate_similarity(research_topic, papers)

            # Rank papers
            ranked_papers = self.engine.rank_papers(papers_with_scores, top_n=len(papers))

            # Prepare results
            similarity_results = []
            for i, paper in enumerate(ranked_papers):
                result = {
                    "rank": i + 1,
                    "file_name": paper.file_metadata.file_name,
                    "similarity_score": paper.similarity_score,
                    "title": paper.paper_metadata.title,
                    "authors": paper.paper_metadata.authors,
                    "year": paper.paper_metadata.year,
                    "abstract_preview": (
                        paper.paper_metadata.abstract[:200] + "..." if paper.paper_metadata.abstract else None
                    ),
                }
                similarity_results.append(result)
                print(f"   {i+1:2d}. {paper.file_metadata.file_name} (score: {paper.similarity_score:.3f})")

            return similarity_results

        except Exception as e:
            print(f"❌ Error in similarity calculation: {e}")
            traceback.print_exc()
            return []

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test of PaperLensEngine."""
        print("🧪 Starting comprehensive PaperLensEngine test")
        print("=" * 60)

        # Initialize engine
        if not self.initialize_engine():
            return {"error": "Failed to initialize engine"}

        # Load research topic
        research_topic = self.load_research_topic()
        if not research_topic:
            return {"error": "Failed to load research topic"}

        # Test individual PDF parsing
        print(f"\n📄 Testing individual PDF parsing in {self.papers_dir}")
        pdf_files = list(self.papers_dir.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files")

        parsing_results = []
        for pdf_path in pdf_files:
            result = self.test_single_pdf_parsing(pdf_path)
            parsing_results.append(result)

        # Test similarity calculation
        similarity_results = self.test_similarity_calculation(research_topic)

        # Generate summary
        summary = self._generate_test_summary(parsing_results, similarity_results)

        return {
            "summary": summary,
            "parsing_results": parsing_results,
            "similarity_results": similarity_results,
            "research_topic": research_topic,
        }

    def _generate_test_summary(self, parsing_results: List[Dict], similarity_results: List[Dict]) -> Dict[str, Any]:
        """Generate a summary of test results."""
        total_papers = len(parsing_results)
        successful_parses = sum(1 for r in parsing_results if r["parsing_success"])

        # Metadata extraction statistics
        metadata_stats = {}
        for field in ["title", "authors", "year", "abstract", "doi", "keywords", "venue"]:
            extracted_count = sum(1 for r in parsing_results if r["metadata_quality"].get(f"{field}_extracted", False))
            metadata_stats[field] = {
                "extracted": extracted_count,
                "percentage": (extracted_count / total_papers * 100) if total_papers > 0 else 0,
            }

        # Content extraction statistics
        content_stats = {}
        for field in ["content", "sections", "references"]:
            extracted_count = sum(1 for r in parsing_results if r["metadata_quality"].get(f"{field}_extracted", False))
            content_stats[field] = {
                "extracted": extracted_count,
                "percentage": (extracted_count / total_papers * 100) if total_papers > 0 else 0,
            }

        # Collect all suggestions
        all_suggestions = []
        for result in parsing_results:
            all_suggestions.extend(result.get("suggestions", []))

        # Count suggestion frequency
        suggestion_counts = {}
        for suggestion in all_suggestions:
            suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1

        return {
            "total_papers": total_papers,
            "successful_parses": successful_parses,
            "parse_success_rate": (successful_parses / total_papers * 100) if total_papers > 0 else 0,
            "metadata_extraction": metadata_stats,
            "content_extraction": content_stats,
            "top_suggestions": sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "similarity_tested": len(similarity_results) > 0,
        }

    def save_results(self, results: Dict[str, Any], output_file: Path):
        """Save test results to JSON file."""
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"💾 Results saved to {output_file}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")


def main():
    """Main function to run the metadata extraction test."""
    # Set up paths
    project_root = Path(__file__).parent.parent
    papers_dir = project_root / "data" / "papers"
    topic_file = project_root / "example_topic.txt"
    output_file = project_root / "examples" / "paperlens_test_results.json"

    print("🔬 PaperLensEngine Metadata Extraction Test")
    print("=" * 50)

    # Check if required files exist
    if not papers_dir.exists():
        print(f"❌ Papers directory not found: {papers_dir}")
        return

    if not topic_file.exists():
        print(f"❌ Topic file not found: {topic_file}")
        return

    # Create tester
    tester = MetadataExtractionTester(papers_dir, topic_file)

    # Run comprehensive test
    results = tester.run_comprehensive_test()

    if "error" in results:
        print(f"❌ Test failed: {results['error']}")
        return

    # Print summary
    print("\n📊 Test Summary")
    print("=" * 30)
    summary = results["summary"]
    print(f"Total papers: {summary['total_papers']}")
    print(f"Successful parses: {summary['successful_parses']} ({summary['parse_success_rate']:.1f}%)")

    print("\n📈 Metadata Extraction Rates:")
    for field, stats in summary["metadata_extraction"].items():
        print(f"  {field}: {stats['extracted']}/{summary['total_papers']} ({stats['percentage']:.1f}%)")

    print("\n📝 Content Extraction Rates:")
    for field, stats in summary["content_extraction"].items():
        print(f"  {field}: {stats['extracted']}/{summary['total_papers']} ({stats['percentage']:.1f}%)")

    print("\n💡 Top Improvement Suggestions:")
    for suggestion, count in summary["top_suggestions"][:5]:
        print(f"  • {suggestion} (mentioned {count} times)")

    # Save results
    tester.save_results(results, output_file)

    print(f"\n✅ Test completed! Check {output_file} for detailed results.")


if __name__ == "__main__":
    main()
