from dxf_checker.checks.base import SegmentCheck

class RoadGeometryValidatorCheck(SegmentCheck):
    """
    Placeholder – real work is done inline in main.py
    """
    def __init__(self, verbose=False):
        super().__init__("RoadGeometryValidator", "Road geometry validation")
        self.verbose = verbose

    def run(self, entity, points, output_msp):
        # actual logic already executed in main.py
        pass