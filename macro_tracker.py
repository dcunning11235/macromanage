from datetime import datetime
from models import DailyLog, UserStats, DietMode
from progress_tracker import ProgressTracker
from nutrition_calculator import NutritionCalculator
from adjustment_system import DynamicAdjuster
from data_export import DataManager


class MacroTracker:
    def __init__(self):
        self.logs = []
        self.tracker = ProgressTracker(self.logs)
        self.calculator = NutritionCalculator(self.tracker)
        self.adjuster = DynamicAdjuster(self.tracker)
        self.data_manager = DataManager(self.tracker)

    def add_log(self, log):
        """Add a new daily log"""
        self.logs.append(log)
        self.logs.sort(key=lambda x: x.date)
        # Update all components with new data
        self.tracker = ProgressTracker(self.logs)
        self.calculator = NutritionCalculator(self.tracker)
        self.adjuster = DynamicAdjuster(self.tracker)
        self.data_manager = DataManager(self.tracker)

    def get_recommendations(self, stats, mode):
        """Get comprehensive nutrition recommendations"""
        # Calculate base targets
        target_calories, explanation = self.calculator.calculate_target_calories(stats, mode)
        macros = self.calculator.calculate_macros(target_calories, stats, mode)
        adjusted_macros = self.calculator.adjust_for_body_composition(macros, stats)

        # Get progress-based adjustments
        adjustments = self.adjuster.calculate_adjustments(target_calories, stats, mode)

        # Apply adjustments if we have enough data
        if adjustments:
            changes = self.adjuster.get_recommended_changes(adjustments)
            target_calories += changes['calories']
            adjusted_macros['protein'] += changes['protein']

            # Recalculate other macros to maintain ratios
            total_calories = (adjusted_macros['protein'] * 4 +
                              adjusted_macros['fat'] * 9 +
                              adjusted_macros['carbs'] * 4)

            if total_calories != target_calories:
                # Adjust carbs to meet new calorie target
                carb_calories = (target_calories -
                                 (adjusted_macros['protein'] * 4 + adjusted_macros['fat'] * 9))
                adjusted_macros['carbs'] = max(0, round(carb_calories / 4))

        return {
            'calories': target_calories,
            'macros': adjusted_macros,
            'explanation': explanation,
            'adjustments': adjustments
        }

    def export_data(self, format='csv', filename=None):
        """Export tracking data in specified format"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'macro_tracker_export_{timestamp}'

        if format.lower() == 'csv':
            return self.data_manager.export_csv(f"{filename}.csv")
        elif format.lower() == 'json':
            return self.data_manager.save_json(f"{filename}.json")
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def get_progress_summary(self):
        """Get summary of progress and achievements"""
        df = self.data_manager.to_dataframe()
        weekly_summary = self.data_manager.get_weekly_summary()
        composition = self.tracker.analyze_body_composition()

        return {
            'overall_changes': composition,
            'weekly_summary': weekly_summary,
            'adherence': self.tracker.get_adherence_data(),
            'current_tdee': self.tracker.calculate_tdee()
        }


# Example usage
def main():
    # Initialize tracker
    tracker = MacroTracker()

    # Create sample user stats
    stats = UserStats(
        weight=80.0,
        body_fat=15.0,
        target_weight=75.0,
        target_body_fat=12.0,
        activity_level=1.55
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
    print("Recommendations:", recommendations)

    # Get progress summary
    summary = tracker.get_progress_summary()
    print("Progress Summary:", summary)

    # Export data
    tracker.export_data('csv', 'tracking_data')


if __name__ == "__main__":
    main()