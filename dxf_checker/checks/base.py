from abc import ABC, abstractmethod
from typing import Any, Tuple, List

class SegmentCheck(ABC):
    """
    Abstract base class for all DXF segment checks.
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.error_count = 0

    @abstractmethod
    def run(self, entities: List[Any], doc: Any = None) -> None:
        """
        Perform the check on DXF entities.
        - entities: list of DXF entities to check
        - doc: DXF document for creating error markers
        """
        pass

    def get_error_count(self) -> int:
        """Get the number of errors found by this check"""
        return self.error_count