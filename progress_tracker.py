from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from base_types import DailyLog


class ProgressTracker:
    def __init__(self, logs: List[DailyLog]):
        self.logs = sorted(logs, key=lambda x: x.date)

    def calculate_tdee(self, days: int = 14) -> Optional[float]:
        """
        Calculate TDEE based on weight change and calorie intake
        with greater weight given to recent data
        """
        if len(self.logs) < 7:
            return None

        recent_logs = sorted(self.logs[-days:], key=lambda x: x.date)
        if len(self.logs) < 7:
            return None

        # Calculate weighted average daily calories
        # More recent days get higher weights
        days_array = np.array([(log.date - recent_logs[0].date).days for log in recent_logs])
        weights = 1 + (days_array / days_array.max()) * 0.5  # 1 to 1.5 weight factor
        calories_array = np.array([log.calories for log in recent_logs])
        avg_calories = np.average(calories_array, weights=weights)

        # Perform weighted linear regression for weight change
        weights_array = np.array([log.weight for log in recent_logs])
        # Use same weighting scheme for the regression
        slope, _ = np.polyfit(days_array, weights_array, 1, w=weights)
        daily_weight_change = slope

        # Convert kg to lbs and calculate daily calorie adjustment
        daily_cal_adjustment = (daily_weight_change * 2.20462 * 3500)

        # TDEE = average calories - daily calorie surplus/deficit
        tdee = round(avg_calories - daily_cal_adjustment)

        return tdee if 500 <= tdee <= 10000 else None

    def calculate_trends(self, days: int = 28) -> Dict[str, float]:
        """Calculate trends in various metrics"""
        if len(self.logs) < days:
            return {}

        recent = self.logs[-days:]
        trends = {}

        # Calculate linear regression for weight trend
        dates = [(log.date - recent[0].date).days for log in recent]
        weights = [log.weight for log in recent]

        if len(dates) > 1:  # Need at least 2 points for regression
            slope, _ = np.polyfit(dates, weights, 1)
            trends['weight_trend'] = slope * 7  # Convert daily to weekly rate

        # Calculate moving averages
        trends['weight_ma'] = np.mean([log.weight for log in recent[-7:]])
        trends['calories_ma'] = np.mean([log.calories for log in recent[-7:]])
        trends['protein_ma'] = np.mean([log.protein for log in recent[-7:]])

        # Calculate variability
        trends['weight_cv'] = np.std(weights) / np.mean(weights) * 100
        trends['calorie_adherence'] = np.mean([1 if log.calories > 0 else 0 for log in recent[-7:]])

        return trends

    def analyze_body_composition(self, days: int = 28) -> Dict[str, float]:
        """Analyze changes in body composition"""
        if len(self.logs) < 2:
            return {}

        recent = sorted(self.logs[-days:], key=lambda x: x.date)
        start, end = recent[0], recent[-1]

        results = {
            'total_weight_change': end.weight - start.weight,
            'rate_of_change': (end.weight - start.weight) / (days / 7)  # weekly rate
        }

        if end.lean_mass and start.lean_mass:
            results.update({
                'lean_mass_change': end.lean_mass - start.lean_mass,
                'fat_mass_change': end.fat_mass - start.fat_mass if end.fat_mass and start.fat_mass else 0,
                'lean_mass_ratio': (end.lean_mass - start.lean_mass) / (end.weight - start.weight)
                if end.weight != start.weight else 0
            })

        return results

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

    def get_adherence_stats(self, days: int = 28) -> Dict[str, float]:
        """Calculate adherence to targets"""
        if len(self.logs) < days:
            return {}

        recent = self.logs[-days:]

        return {
            'logging_adherence': len(recent) / days,
            'calorie_adherence': np.mean([1 if log.calories > 0 else 0 for log in recent]),
            'protein_adherence': np.mean([1 if log.protein > 0 else 0 for log in recent])
        }

    def suggest_adjustments(self, days: int = 28) -> List[str]:
        """Suggest adjustments based on analysis"""
        suggestions = []
        trends = self.calculate_trends(days)
        composition = self.analyze_body_composition(days)
        adherence = self.get_adherence_stats(days)

        if not trends or not composition:
            return ["Need more data to make suggestions"]

        # Check adherence
        if adherence.get('logging_adherence', 1) < 0.8:
            suggestions.append("Try to log more consistently for better analysis")

        # Check weight trend
        if abs(trends.get('weight_trend', 0)) > 1.0:  # More than 1kg/week
            suggestions.append("Weight changing faster than recommended")

        # Check body composition
        if composition.get('lean_mass_ratio', 1) < 0.7:  # More than 30% of loss from lean mass
            suggestions.append("Consider increasing protein and reducing deficit")

        # Check consistency
        if trends.get('weight_cv', 0) > 1.5:  # High weight variability
            suggestions.append("Weight showing high variability. Try to weigh at consistent times")

        return suggestions