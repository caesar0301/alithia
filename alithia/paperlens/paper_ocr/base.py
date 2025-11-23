from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from alithia.paperlens.models import AcademicPaper


class PaperOcrBase(ABC):
    """Base class for paper parsing."""

    @abstractmethod
    def parse_file(self, file_path: Path) -> Optional[AcademicPaper]:
        """Parse the file and return the AcademicPaper."""
