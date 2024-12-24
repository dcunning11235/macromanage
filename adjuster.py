# adjustment_system.py
from dataclasses import dataclass
from typing import List, Dict, Optional
from base_types import DietMode, UserStats
from diet_configs import DietConfigs
from progress_tracker import ProgressTracker


@dataclass
class Adjustment:
    calories: int
    protein: int
    reason: str
    severity: str  # 'low', 'medium', 'high'


class DynamicAdjuster:
    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker
        self.configs = DietConfigs.get_default_configs()

    def calculate_adjustments(self,
                              current_calories: int,
                              stats: UserStats,
                              mode: DietMode) -> List[Adjustment]:
        """Calculate needed adjustments based on progress"""
        adjustments = []
        config = self.configs[mode]
        changes = self.tracker.calculate_changes()
        composition = self.tracker.analyze_body_composition()

        if not changes or not composition:
            return adjustments

        # Check if progress is too fast or slow
        weekly_change = changes['weight_change']
        if weekly_change