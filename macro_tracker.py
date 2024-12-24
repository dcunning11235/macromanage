from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from base_types import DailyLog, UserStats, DietMode
from progress_tracker import ProgressTracker
from nutrition_calculator import NutritionCalculator
from adjustment_system import DynamicAdjuster
from data_manager import DataManager


class MacroTracker:
    def __init__(self):
        """Initialize the macro tracking system"""
        self.logs = []
        self.tracker = ProgressTracker(self.logs)
        self.calculator = NutritionCalculator(self.tracker)
        self.adjuster = DynamicAdjuster(self.tracker)
        self.data_manager = DataManager(self.tracker)

    def load_data(self, filename: str, source: str = None) -> None:
        """Load tracking data from file"""
        imported_logs = self.data_manager.import_data(filename, source)
        self.logs = self.data_manager.merge_logs(imported_logs)
        self._update_components()

    def add_log(self, log: DailyLog) -> None:
        """Add a new daily log entry"""
        self.logs.append(log)
        self.logs.sort(key=lambda x: x.date)
        self._update_components()

    def get_recommendations(self, stats: UserStats, mode: DietMode) -> Dict:
        """Get comprehensive nutrition recommendations"""
        # Calculate base targets
        target_calories, explanation = self.calculator.calculate_target_calories(stats, mode)
        macros = self.calculator.calculate_macros(target_calories, stats, mode)

        # Get progress-based adjustments
        adjustments = self.adjuster.calculate_adjustments(stats, mode)

        # Apply adjustments if we have enough data
        if adjustments:
            changes = self.adjuster.get_net_adjustment(adjustments)
            target_calories += changes['calories']

            # Recalculate macros with new calories
            macros = self.calculator.calculate_macros(target_calories, stats, mode)
            macros['protein'] += changes['protein']

            # Adjust carbs to maintain calorie target
            total_calories = (macros['protein'] * 4 +
                              macros['fat'] * 9 +
                              macros['carbs'] * 4)

            if total_calories != target_calories:
                carb_calories = (target_calories -
                                 (macros['protein'] * 4 + macros['fat'] * 9))
                macros['carbs'] = max(0, round(carb_calories / 4))

        # Get meal timing suggestions
        meal_timing = self.calculator.get_meal_timing(target_calories, meal_count=4)

        # Get minimum nutrients
        min_nutrients = self.calculator.get_minimum_nutrients(stats)

        return {
            'calories': target_calories,
            'macros': macros,
            'meal_timing': meal_timing,
            'minimum_nutrients': min_nutrients,
            'explanation': explanation,
            'adjustments': adjustments
        }

    def get_progress_summary(self, days: int = 28) -> Dict:
        """Get comprehensive progress summary"""
        return {
            'overall_changes': self.tracker.analyze_body_composition(days),
            'weekly_stats': self.data_manager.get_weekly_summary(),
            'adherence': self.tracker.get_adherence_stats(days),
            'current_tdee': self.tracker.calculate_tdee(),
            'trends': self.tracker.calculate_trends(days),
            'suggestions': self.tracker.suggest_adjustments(days)
        }

    def export_data(self, format: str = 'csv', filename: Optional[str] = None) -> str:
        """Export tracking data in specified format"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'macro_tracker_export_{timestamp}'

        if format.lower() == 'csv':
            return self.data_manager.export_csv(f"{filename}.csv")
        elif format.lower() == 'json':
            return self.data_manager.export_json(f"{filename}.json")
        elif format.lower() == 'excel':
            return self.data_manager.export_excel(f"{filename}.xlsx")
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def generate_report(self, filename: str) -> str:
        """Generate comprehensive progress report"""
        progress = self.get_progress_summary()
        weekly_stats = self.data_manager.get_weekly_summary()

        # Get current recommendations
        if self.logs:
            latest = self.logs[-1]
            stats = UserStats(
                weight=latest.weight,
                body_fat=latest.body_fat,
                target_weight=latest.weight,  # Maintenance recommendations
                target_body_fat=latest.body_fat
            )
            current_recs = self.get_recommendations(stats, DietMode.MAINTENANCE)
        else:
            current_recs = None

        report_data = {
            'progress': progress,
            'weekly_stats': weekly_stats.to_dict() if len(weekly_stats) > 0 else {},
            'current_recommendations': current_recs,
            'generated_date': datetime.now().isoformat()
        }

        # Save report
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)

        return f"Report generated and saved to {filename}"

    def _update_components(self) -> None:
        """Update all components with current data"""
        self.tracker = ProgressTracker(self.logs)
        self.calculator = NutritionCalculator(self.tracker)
        self.adjuster = DynamicAdjuster(self.tracker)
        self.data_manager = DataManager(self.tracker)


# Example usage
def main():
    # Initialize tracker
    tracker = MacroTracker()

    # Load existing data if available
    try:
        tracker.load_data('tracking_history.csv')
    except FileNotFoundError:
        print("No existing data found, starting fresh")

    # Create sample user stats
    stats = UserStats(
        weight=80.0,
        body_fat=15.0,
        target_weight=75.0,
        target_body_fat=12.0
    )

    # Add sample log
    log = DailyLog(
        date=datetime.now(),
        weight=80.0,
        body_fat=15.0,
        calories=2500,
        protein=180,
        carbs=250,
        fat=83
    )
    tracker.add_log(log)

    # Get recommendations
    recommendations = tracker.get_recommendations(stats, DietMode.STANDARD_CUT)
    print("\nRecommendations:", recommendations)

    # Get progress summary
    summary = tracker.get_progress_summary()
    print("\nProgress Summary:", summary)

    # Export data
    tracker.export_data('csv', 'tracking_data')
    print("\nData exported to tracking_data.csv")


if __name__ == "__main__":
    main()