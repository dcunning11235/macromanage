from typing import Dict, Tuple, Optional
from base_types import UserStats, DietMode, MacroSplit
from diet_configs import DietConfigs
from progress_tracker import ProgressTracker


class NutritionCalculator:
    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker
        self.configs = DietConfigs()

    def calculate_bmr(self, stats: UserStats) -> float:
        """Calculate Basal Metabolic Rate using Mifflin-St Jeor equation"""
        if not stats.height or not stats.age or not stats.gender:
            # Use simplified calculation if full data not available
            return (10 * stats.weight) + (6.25 * 170) - (5 * 30) + 5

        # Mifflin-St Jeor Equation
        bmr = (10 * stats.weight) + (6.25 * stats.height) - (5 * stats.age)
        if stats.gender.lower() == 'male':
            bmr += 5
        else:
            bmr -= 161

        return round(bmr)

    def calculate_maintenance_calories(self, stats: UserStats) -> float:
        """Calculate maintenance calories using TDEE or BMR"""
        tdee = self.tracker.calculate_tdee()

        if tdee is None:
            # Calculate from BMR if no TDEE available
            bmr = self.calculate_bmr(stats)
            tdee = bmr * stats.activity_level.value

        return round(tdee)

    def calculate_target_calories(self, stats: UserStats, mode: DietMode) -> Tuple[int, str]:
        """Calculate target calories based on diet mode and user stats"""
        maintenance = self.calculate_maintenance_calories(stats)
        config = self.configs.get_config_for_user(mode, stats)

        # Calculate initial target
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
        config = self.configs.get_config_for_user(mode, stats)
        lean_mass = stats.weight * (1 - stats.body_fat / 100)

        # Calculate protein based on lean mass and diet mode
        protein = round(lean_mass * config.protein_factor)
        protein_calories = protein * 4

        # Distribute remaining calories according to macro split
        remaining_calories = calories - protein_calories
        remaining_ratio = config.macro_split.fat / (config.macro_split.fat + config.macro_split.carbs)

        fat_calories = remaining_calories * remaining_ratio
        fat = round(fat_calories / 9)

        carb_calories = remaining_calories - fat_calories
        carbs = round(carb_calories / 4)

        return {
            'protein': protein,
            'fat': fat,
            'carbs': carbs
        }

    def adjust_for_training_day(self, macros: Dict[str, int], is_training: bool) -> Dict[str, int]:
        """Adjust macros based on training vs rest day"""
        if not is_training:
            # Reduce carbs on rest days, increase fats to maintain calories
            carb_reduction = round(macros['carbs'] * 0.2)  # 20% reduction
            fat_increase = round((carb_reduction * 4) / 9)  # Convert calories to fat grams

            return {
                'protein': macros['protein'],
                'carbs': macros['carbs'] - carb_reduction,
                'fat': macros['fat'] + fat_increase
            }
        return macros

    def calculate_refeed_macros(self, maintenance_calories: int, stats: UserStats) -> Dict[str, int]:
        """Calculate macros for refeed days"""
        refeed_calories = round(maintenance_calories * 1.0)  # At maintenance

        # Higher carbs, lower fat, maintain protein
        return {
            'protein': round(stats.weight * 2.2),  # Maintain protein
            'fat': round((maintenance_calories * 0.2) / 9),  # 20% from fat
            'carbs': round((refeed_calories -
                            (stats.weight * 2.2 * 4) -  # Protein calories
                            (maintenance_calories * 0.2)) / 4)  # Remaining to carbs
        }

    def get_minimum_nutrients(self, stats: UserStats, calories: int) -> Dict[str, float]:
        """Calculate minimum recommended nutrients"""
        return {
            'protein': round(stats.weight * 1.6),  # Minimum protein
            'fat': round(stats.weight * 0.8),  # Minimum fat
            'fiber': round(calories / 1000 * 14),  # Fiber based on calories
            'water': round(stats.weight * 0.033)  # Water in liters
        }

    def get_meal_timing(self, calories: int, meal_count: int) -> Dict[str, int]:
        """Distribute calories across meals"""
        if meal_count == 3:
            distribution = [0.3, 0.4, 0.3]  # 30/40/30 split
        elif meal_count == 4:
            distribution = [0.25, 0.3, 0.25, 0.2]
        else:
            distribution = [1 / meal_count] * meal_count

        return {
            f'meal_{i + 1}': round(calories * dist)
            for i, dist in enumerate(distribution)
        }