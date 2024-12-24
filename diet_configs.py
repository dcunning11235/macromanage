from dataclasses import dataclass
from typing import Dict
from base_types import DietMode, MacroSplit, TrainingLevel, UserStats


@dataclass
class DietConfig:
    """Configuration for a specific diet mode"""
    name: str
    description: str
    calorie_adjustment: float  # multiplier for TDEE
    min_weekly_change: float  # kg/week
    max_weekly_change: float  # kg/week
    min_deficit: int  # minimum daily calorie deficit/surplus
    max_deficit: int  # maximum daily calorie deficit/surplus
    protein_factor: float  # g/kg of body weight
    macro_split: MacroSplit
    lean_mass_preservation: float  # minimum ratio to maintain
    diet_break_frequency: int = 0  # weeks between diet breaks (0 for none)
    refeed_frequency: int = 0  # days between refeeds (0 for none)


class DietConfigs:
    """Default configurations for different diet modes"""

    @staticmethod
    def adjust_for_training_level(config: DietConfig, level: TrainingLevel) -> DietConfig:
        """Adjust diet config based on training experience"""
        if level == TrainingLevel.BEGINNER:
            config.protein_factor *= 0.9
            config.max_weekly_change *= 1.2
        elif level == TrainingLevel.ADVANCED:
            config.protein_factor *= 1.1
            config.max_weekly_change *= 0.8
        return config

    @staticmethod
    def adjust_for_body_fat(config: DietConfig, body_fat: float) -> DietConfig:
        """Adjust diet config based on current body fat percentage"""
        if body_fat > 30:
            config.max_weekly_change *= 1.25
            config.max_deficit *= 1.2
        elif body_fat < 12:
            config.max_weekly_change *= 0.75
            config.protein_factor *= 1.2
            config.diet_break_frequency = 8  # More frequent diet breaks
        elif body_fat < 15:
            config.max_weekly_change *= 0.85
            config.protein_factor *= 1.1
        return config

    @staticmethod
    def get_default_configs() -> Dict[DietMode, DietConfig]:
        """Get base configurations for each diet mode"""
        return {
            DietMode.AGGRESSIVE_CUT: DietConfig(
                name="Aggressive Cut",
                description="Rapid fat loss with higher risk of muscle loss",
                calorie_adjustment=0.75,  # 25% deficit
                min_weekly_change=0.7,
                max_weekly_change=1.2,
                min_deficit=500,
                max_deficit=1000,
                protein_factor=2.4,  # g/kg body weight
                macro_split=MacroSplit(protein=40, fat=30, carbs=30),
                lean_mass_preservation=0.85,
                diet_break_frequency=6,
                refeed_frequency=14
            ),
            DietMode.STANDARD_CUT: DietConfig(
                name="Standard Cut",
                description="Balanced approach to fat loss",
                calorie_adjustment=0.80,  # 20% deficit
                min_weekly_change=0.5,
                max_weekly_change=1.0,
                min_deficit=400,
                max_deficit=750,
                protein_factor=2.2,
                macro_split=MacroSplit(protein=35, fat=30, carbs=35),
                lean_mass_preservation=0.9,
                diet_break_frequency=8,
                refeed_frequency=7
            ),
            DietMode.CONSERVATIVE_CUT: DietConfig(
                name="Conservative Cut",
                description="Slower fat loss with better muscle preservation",
                calorie_adjustment=0.85,  # 15% deficit
                min_weekly_change=0.3,
                max_weekly_change=0.7,
                min_deficit=300,
                max_deficit=500,
                protein_factor=2.0,
                macro_split=MacroSplit(protein=30, fat=30, carbs=40),
                lean_mass_preservation=0.95,
                refeed_frequency=5
            ),
            DietMode.MAINTENANCE: DietConfig(
                name="Maintenance",
                description="Maintain current weight and body composition",
                calorie_adjustment=1.0,
                min_weekly_change=0,
                max_weekly_change=0.2,
                min_deficit=0,
                max_deficit=0,
                protein_factor=1.8,
                macro_split=MacroSplit(protein=30, fat=30, carbs=40),
                lean_mass_preservation=1.0
            ),
            DietMode.LEAN_BULK: DietConfig(
                name="Lean Bulk",
                description="Gradual muscle gain with minimal fat",
                calorie_adjustment=1.10,  # 10% surplus
                min_weekly_change=0.2,
                max_weekly_change=0.4,
                min_deficit=200,
                max_deficit=400,
                protein_factor=2.0,
                macro_split=MacroSplit(protein=30, fat=25, carbs=45),
                lean_mass_preservation=1.0
            ),
            DietMode.STANDARD_BULK: DietConfig(
                name="Standard Bulk",
                description="Faster muscle gain accepting some fat gain",
                calorie_adjustment=1.15,  # 15% surplus
                min_weekly_change=0.3,
                max_weekly_change=0.5,
                min_deficit=300,
                max_deficit=500,
                protein_factor=1.8,
                macro_split=MacroSplit(protein=25, fat=25, carbs=50),
                lean_mass_preservation=1.0
            )
        }

    @classmethod
    def get_config_for_user(cls, mode: DietMode, stats: UserStats) -> DietConfig:
        """Get personalized diet configuration based on user stats"""
        base_config = cls.get_default_configs()[mode]

        # Adjust for training level
        config = cls.adjust_for_training_level(base_config, stats.training_level)

        # Adjust for body fat
        config = cls.adjust_for_body_fat(config, stats.body_fat)

        return config

    @staticmethod
    def calculate_refeed_calories(config: DietConfig, tdee: float) -> float:
        """Calculate calories for refeed days"""
        if config.refeed_frequency == 0:
            return 0

        if isinstance(config.calorie_adjustment, float) and config.calorie_adjustment < 1:
            # For cutting phases
            return tdee * 0.9  # 10% below maintenance
        return tdee

    @staticmethod
    def calculate_diet_break_calories(config: DietConfig, tdee: float) -> float:
        """Calculate calories for diet break periods"""
        if config.diet_break_frequency == 0:
            return 0

        return tdee * 0.95  # Slight deficit to maintain progress