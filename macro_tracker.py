from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path
from io import BytesIO
from base_types import UserStats, DietMode, DailyLog, MacroPreset, MacroSplitConfig
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

    def load_data(self, file: Union[str, BytesIO, Path], source: str = None, units: str = 'metric') -> None:
        """
        Load tracking data from file

        Args:
            file: File path or uploaded file object
            source: Source of the data (e.g., 'myfitnesspal')
            units: Unit system of the input data ('metric' or 'imperial')
        """
        imported_logs = self.data_manager.import_data(file, source, units)
        self.logs = self.data_manager.merge_logs(imported_logs)
        self._update_components()

    def add_log(self, log: DailyLog) -> None:
        """Add a new daily log entry"""
        self.logs.append(log)
        self.logs.sort(key=lambda x: x.date)
        self._update_components()

    def get_recommendations(self, stats: UserStats, mode: DietMode,
                            macro_preset: MacroPreset = MacroPreset.BALANCED,
                            custom_split: Optional[MacroSplitConfig] = None) -> Dict:
        """Get comprehensive nutrition recommendations"""
        # Calculate base targets
        target_calories, explanation = self.calculator.calculate_target_calories(stats, mode)

        # Get maintenance calories if available
        maintenance_calories = self.tracker.calculate_tdee() or self.calculator.calculate_target_calories(stats, DietMode.MAINTENANCE)[0] #target_calories

        # Get macros based on preset
        macros = self.calculator.calculate_macros(
            target_calories,
            stats,
            mode,
            macro_preset=macro_preset,
            custom_split=custom_split
        )

        # Get progress-based adjustments
        adjustments = self.adjuster.calculate_adjustments(target_calories, stats, mode)

        # Apply adjustments if we have enough data
        if adjustments:
            changes = self.adjuster.get_net_adjustment(adjustments)
            target_calories += changes['calories']

            # Recalculate macros with adjusted calories
            macros = self.calculator.calculate_macros(
                target_calories,
                stats,
                mode,
                macro_preset=macro_preset,
                custom_split=custom_split
            )
            macros['protein'] += changes['protein']

            # Adjust carbs to maintain calorie target
            total_calories = (macros['protein'] * 4 +
                              macros['fat'] * 9 +
                              macros['carbs'] * 4)

            if total_calories != target_calories:
                carb_calories = (target_calories -
                                 (macros['protein'] * 4 + macros['fat'] * 9))
                macros['carbs'] = max(0, round(carb_calories / 4))

        # Calculate meal timing suggestions
        meal_timing = self.calculator.get_meal_timing(target_calories)
        min_nutrients = self.calculator.get_minimum_nutrients(stats, target_calories)

        return {
            'calories': target_calories,
            'maintenance_calories': maintenance_calories,
            'macros': macros,
            'meal_timing': meal_timing,
            'minimum_nutrients': min_nutrients,
            'explanation': explanation,
            'adjustments': adjustments
        }

    def get_progress_summary(self) -> Dict:
        """Get comprehensive progress summary"""
        return {
            'overall_changes': self.tracker.analyze_body_composition(),
            'weekly_stats': self.data_manager.get_weekly_summary(),
            'adherence': self.tracker.get_adherence_stats(),
            'current_tdee': self.tracker.calculate_tdee(),
            'trends': self.tracker.calculate_trends(),
            'suggestions': self.tracker.suggest_adjustments()
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

    def _update_components(self) -> None:
        """Update all components with current data"""
        self.tracker = ProgressTracker(self.logs)
        self.calculator = NutritionCalculator(self.tracker)
        self.adjuster = DynamicAdjuster(self.tracker)
        self.data_manager = DataManager(self.tracker)