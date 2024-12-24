# nutrition_calculator.py
from typing import Dict, Tuple
from base_types import UserStats, DietMode, MacroSplit
from diet_configs import DietConfigs, DietConfig
from progress_tracker import ProgressTracker


class NutritionCalculator:
    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker
        self.configs = DietConfigs.get_default_configs()

    def calculate_maintenance_calories(self, stats: UserStats) -> float:
        """Calculate maintenance calories using TDEE or estimate"""
        tdee = self.tracker.calculate_tdee()

        if tdee is None:
            # Mifflin-St Jeor formula
            bmr = (10 * stats.weight) + (6.25 * 170) - (5 * 30) + 5  # Assuming height=170cm, age=30, male
            tdee = bmr * stats.activity_level

        return round(tdee)

    def calculate_target_calories(self, stats: UserStats, mode: DietMode) -> Tuple[int, str]:
        """Calculate target calories based on diet mode"""
        maintenance = self.calculate_maintenance_calories(stats)
        config = self.configs[mode]

        target_calories = round(maintenance * config.calorie_adjustment)

        # Apply deficit/surplus limits
        adjustment = abs(target_calories - maintenance)
        if adjustment > config.max_deficit:
            target_calories = (maintenance - config.max_deficit
                               if target_calories < maintenance
                               else maintenance + config.max_deficit)
        elif adjustment < config.min_deficit:
            target_calories = (maintenance - config.min_deficit
                               if target_calories < maintenance
                               else maintenance + config.min_deficit)

        explanation = (
            f"Based on maintenance of {maintenance} calories. "
            f"Using {config.name} mode ({config.description}). "
            f"Creates a {'deficit' if target_calories < maintenance else 'surplus'} "
            f"of {abs(target_calories - maintenance)} calories."
        )

        return target_calories, explanation

    def calculate_macros(self, calories: int, stats: UserStats, mode: DietMode) -> Dict[str, int]:
        """Calculate macro targets based on calories and diet mode"""
        config = self.configs[mode]
        lean_mass = stats.weight * (1 - stats.body_fat / 100)

        # Calculate minimum protein based on lean mass
        min_protein = round(lean_mass * config.protein_factor)
        min_protein_calories = min_protein * 4

        # Adjust remaining calories according to macro split
        remaining_calories = calories - min_protein_calories
        fat_calories = remaining_calories * (
                    config.macro_split.fat / (config.macro_split.fat + config.macro_split.carbs))
        carb_calories = remaining_calories - fat_calories

        return {
            'protein': min_protein,
            'fat': round(fat_calories / 9),  # 9 calories per gram
            'carbs': round(carb_calories / 4)  # 4 calories per gram
        }

    def adjust_for_body_composition(self, macros: Dict[str, int], stats: UserStats) -> Dict[str, int]:
        """Make adjustments based on current body composition"""
        lean_mass = stats.weight * (1 - stats.body_fat / 100)

        # Adjust protein based on body fat percentage
        if stats.body_fat > 25:
            # Higher protein for higher body fat to preserve muscle
            macros['protein'] = max(macros['protein'], round(lean_mass * 2.3))
        elif stats.body_fat < 12:
            # Higher protein for very lean individuals
            macros['protein'] = max(macros['protein'], round(lean_mass * 2.5))

        return macros