# progress_tracker.py
from typing import List, Dict, Optional
import numpy as np
from models import DailyLog


class ProgressTracker:
    def __init__(self, logs: List[DailyLog]):
        self.logs = sorted(logs, key=lambda x: x.date)

    def calculate_changes(self, days: int = 7) -> Dict[str, float]:
        """Calculate rate of change for different metrics"""
        if len(self.logs) < days:
            return {}

        recent = self.logs[-days:]
        start, end = recent[0], recent[-1]
        weeks = days / 7

        return {
            'weight_change': (end.weight - start.weight) / weeks,
            'fat_change': (end.fat_mass - start.fat_mass) / weeks if end.fat_mass and start.fat_mass else 0,
            'lean_change': (end.lean_mass - start.lean_mass) / weeks if end.lean_mass and start.lean_mass else 0
        }

    def detect_plateau(self, threshold: float = 0.2, weeks: int = 3) -> bool:
        """Check if progress has stalled"""
        changes = self.calculate_changes(weeks * 7)
        if not changes:
            return False
        return abs(changes['weight_change']) < threshold

    def calculate_tdee(self, days: int = 14) -> Optional[float]:
        """Estimate TDEE based on weight change and calorie intake"""
        if len(self.logs) < days:
            return None

        recent = self.logs[-days:]
        avg_calories = np.mean([day.calories for day in recent])
        weight_change = recent[-1].weight - recent[0].weight

        # Convert kg to lbs and use 3500 calories per pound
        daily_cal_adjustment = (weight_change * 2.20462 * 3500) / days
        return round(avg_calories - daily_cal_adjustment)

    def get_adherence_data(self, days: int = 28) -> Dict[str, float]:
        """Calculate adherence to targets"""
        if len(self.logs) < days:
            return {}

        recent = self.logs[-days:]

        return {
            'calorie_adherence': np.mean([1 if log.calories > 0 else 0 for log in recent]),
            'protein_adherence': np.mean([1 if log.protein > 0 else 0 for log in recent])
        }

    def analyze_body_composition(self) -> Dict[str, float]:
        """Analyze body composition changes"""
        if len(self.logs) < 2:
            return {}

        start, end = self.logs[0], self.logs[-1]
        days = (end.date - start.date).days

        if not (start.lean_mass and end.lean_mass):
            return {}

        return {
            'total_change': end.weight - start.weight,
            'lean_change': end.lean_mass - start.lean_mass,
            'fat_change': end.fat_mass - start.fat_mass if end.fat_mass and start.fat_mass else 0,
            'rate': (end.weight - start.weight) / (days / 7)  # weekly rate
        }