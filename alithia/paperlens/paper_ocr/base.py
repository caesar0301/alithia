from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from alithia.paperlens.models import AcademicPaper


class PaperOCRBase(ABC):
    """Base class for paper parsing."""

    @abstractmethod
    def parse_pdf(self, pdf_path: Path) -> Optional[AcademicPaper]:
        """Parse the PDF and return the AcademicPaper."""
