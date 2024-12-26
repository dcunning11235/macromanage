from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from base_types import DailyLog, UserStats, ProgressMetrics


class ProgressTracker:
    def __init__(self, logs: List[DailyLog]):
        self.logs = sorted(logs, key=lambda x: x.date)

    def calculate_tdee(self, days: int = 14) -> Optional[float]:
        """
        Calculate TDEE based on weight change and calorie intake

        Uses linear regression to determine weight change rate and
        averages daily calories over the period to estimate TDEE.
        """
        if len(self.logs) < 7:  # Need at least a week of data
            return None

        recent_logs = sorted(self.logs[-days:], key=lambda x: x.date)
        if len(recent_logs) < 7:
            return None

        # Calculate average daily calories
        avg_calories = np.mean([log.calories for log in recent_logs])

        # Create arrays for linear regression
        dates = np.array([(log.date - recent_logs[0].date).days for log in recent_logs])
        weights = np.array([log.weight for log in recent_logs])

        # Perform linear regression to get daily weight change rate
        slope, _ = np.polyfit(dates, weights, 1)
        daily_weight_change = slope  # kg per day

        # Convert kg to lbs and calculate daily calorie adjustment
        # Each pound of weight change represents 3500 calories
        daily_cal_adjustment = (daily_weight_change * 2.20462 * 3500)

        # TDEE = average calories - daily calorie surplus/deficit
        tdee = round(avg_calories - daily_cal_adjustment)

        return tdee if 500 <= tdee <= 10000 else None

    def get_weekly_stats(self) -> List[Dict]:
        """Calculate average stats for each week"""
        if not self.logs:
            return []

        df = pd.DataFrame([vars(log) for log in self.logs])
        df['week'] = pd.to_datetime(df['date']).dt.isocalendar().week

        weekly_stats = df.groupby('week').agg({
            'weight': ['mean', 'min', 'max', 'std'],
            'body_fat': 'mean',
            'calories': ['mean', 'std'],
            'protein': 'mean',
            'carbs': 'mean',
            'fat': 'mean',
            'lean_mass': 'mean',
            'fat_mass': 'mean'
        }).round(2)

        return weekly_stats.to_dict()

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

    def detect_plateau(self, threshold: float = 0.2, weeks: int = 3) -> Tuple[bool, str]:
        """Detect if progress has plateaued"""
        changes = self.calculate_trends(weeks * 7)
        if not changes or 'weight_trend' not in changes:
            return False, "Insufficient data"

        if abs(changes['weight_trend']) < threshold:
            adherence = changes.get('calorie_adherence', 0)
            if adherence > 0.9:
                return True, "True plateau detected (good adherence)"
            else:
                return True, f"Plateau detected but adherence is low ({adherence:.0%})"

        return False, "No plateau detected"

    def analyze_body_composition(self, days: int = 28) -> Dict[str, float]:
        """Analyze changes in body composition"""
        if len(self.logs) < days:
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

    def get_progress_metrics(self) -> Optional[ProgressMetrics]:
        """Get comprehensive progress metrics"""
        return ProgressMetrics.from_logs(self.logs) if self.logs else None

    def suggest_adjustments(self, stats: UserStats) -> List[str]:
        """Suggest adjustments based on progress"""
        suggestions = []
        trends = self.calculate_trends()
        composition = self.analyze_body_composition()

        if not trends or not composition:
            return ["Insufficient data for recommendations"]

        # Check if losing too much lean mass
        if composition.get('lean_mass_ratio', 1) < 0.7:
            suggestions.append("Consider increasing protein intake and reducing deficit")

        # Check if progress is stalled
        is_plateaued, plateau_msg = self.detect_plateau()
        if is_plateaued:
            suggestions.append(f"Progress plateaued: {plateau_msg}")

        # Check adherence
        adherence = self.get_adherence_stats()
        if adherence.get('logging_adherence', 1) < 0.8:
            suggestions.append("Improve tracking consistency for better analysis")

        return suggestions

    def generate_report(self) -> Dict:
        """Generate comprehensive progress report"""
        return {
            'trends': self.calculate_trends(),
            'body_composition': self.analyze_body_composition(),
            'adherence': self.get_adherence_stats(),
            'weekly_stats': self.get_weekly_stats(),
            'tdee': self.calculate_tdee(),
            'suggestions': self.suggest_adjustments(None),  # Pass actual stats if available
            'metrics': self.get_progress_metrics()
        }