from typing import Dict, Tuple, Optional
from base_types import UserStats, DietMode, MacroPreset, MacroSplitConfig, MacroPresets


class NutritionCalculator:
    def __init__(self, tracker):
        self.tracker = tracker

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

    def calculate_target_calories(self, stats: UserStats, mode: DietMode) -> Tuple[int, str]:
        """Calculate target calories based on diet mode and user stats"""
        # Get TDEE from tracker if available
        tdee = self.tracker.calculate_tdee()

        if tdee is None:
            # Calculate from BMR if no TDEE available
            bmr = self.calculate_bmr(stats)
            tdee = bmr * stats.activity_level.value

        # Adjust based on diet mode
        if mode == DietMode.AGGRESSIVE_CUT:
            target_calories = round(tdee * 0.75)  # 25% deficit
            description = "Aggressive deficit for maximum fat loss"
        elif mode == DietMode.STANDARD_CUT:
            target_calories = round(tdee * 0.80)  # 20% deficit
            description = "Standard deficit for steady fat loss"
        elif mode == DietMode.CONSERVATIVE_CUT:
            target_calories = round(tdee * 0.85)  # 15% deficit
            description = "Conservative deficit for gradual fat loss"
        elif mode == DietMode.MAINTENANCE:
            target_calories = round(tdee)
            description = "Maintenance calories for body recomposition"
        elif mode == DietMode.LEAN_BULK:
            target_calories = round(tdee * 1.10)  # 10% surplus
            description = "Slight surplus for lean muscle gain"
        else:  # STANDARD_BULK
            target_calories = round(tdee * 1.15)  # 15% surplus
            description = "Moderate surplus for muscle gain"

        return target_calories, description

    def calculate_macros(self, calories: int, stats: UserStats,
                         mode: DietMode, macro_preset: MacroPreset = MacroPreset.BALANCED,
                         custom_split: Optional[MacroSplitConfig] = None) -> Dict[str, int]:
        """Calculate macro targets based on calories and selected preset"""
        preset_config = custom_split if macro_preset == MacroPreset.CUSTOM else MacroPresets.get_presets()[macro_preset]

        # Calculate protein based on preset
        if preset_config.protein_source == "lean_mass":
            reference_weight = stats.weight * (1 - stats.body_fat / 100)
        else:
            reference_weight = stats.weight

        protein_grams = round(reference_weight * preset_config.protein_factor)
        protein_calories = protein_grams * 4

        # Calculate minimum fat requirement
        min_fat_grams = round(stats.weight * preset_config.min_fat)
        min_fat_calories = min_fat_grams * 9

        # Calculate fat based on ratio, but ensure it meets minimum
        target_fat_calories = calories * preset_config.fat_ratio
        fat_calories = max(target_fat_calories, min_fat_calories)
        fat_grams = round(fat_calories / 9)

        # Remaining calories go to carbs
        remaining_calories = calories - protein_calories - fat_calories
        carb_grams = max(0, round(remaining_calories / 4))

        return {
            'protein': protein_grams,
            'fat': fat_grams,
            'carbs': carb_grams,
            'ratios': {
                'protein': round(protein_calories / calories * 100),
                'fat': round(fat_calories / calories * 100),
                'carbs': round(remaining_calories / calories * 100)
            }
        }

    def get_meal_timing(self, calories: int, meal_count: int = 4) -> Dict[str, int]:
        """Calculate meal timing based on total calories"""
        if meal_count == 3:
            # Standard 3-meal split
            return {
                'breakfast': round(calories * 0.25),
                'lunch': round(calories * 0.35),
                'dinner': round(calories * 0.40)
            }
        elif meal_count == 4:
            # 4-meal split with snack
            return {
                'breakfast': round(calories * 0.25),
                'lunch': round(calories * 0.30),
                'snack': round(calories * 0.15),
                'dinner': round(calories * 0.30)
            }
        else:
            # Equal split for other meal counts
            meal_calories = round(calories / meal_count)
            return {f'meal_{i + 1}': meal_calories for i in range(meal_count)}

    def get_minimum_nutrients(self, stats: UserStats, calories: int) -> Dict[str, float]:
        """Calculate minimum recommended nutrients"""
        return {
            'protein': round(stats.weight * 1.6),  # Minimum protein
            'fat': round(stats.weight * 0.8),  # Minimum fat
            'fiber': round(calories / 1000 * 14),  # Fiber based on calories
            'water': round(stats.weight * 0.033)  # Water in liters
        }