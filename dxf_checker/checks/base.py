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
    def run(self, entity: Any, points: List[Tuple[float, float, float]], output_msp: Any) -> None:
        """
        Perform the check on a DXF entity and its points.
        - entity: the original DXF entity
        - points: list of 3D points from the entity
        - output_msp: modelspace for placing error markers if needed
        """
        pass