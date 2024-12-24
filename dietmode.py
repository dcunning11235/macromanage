# diet_configs.py
from dataclasses import dataclass
from typing import Dict
from base_types import DietMode, MacroSplit


@dataclass
class DietConfig:
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


class DietConfigs:
    """Default configurations for different diet modes"""

    @staticmethod
    def get_default_configs() -> Dict[DietMode, DietConfig]:
        return {
            DietMode.AGGRESSIVE_CUT: DietConfig(
                name="Aggressive Cut",
                description="Rapid fat loss with higher risk of muscle loss",
                calorie_adjustment=0.75,  # 25% deficit
                min_weekly_change=0.7,
                max_weekly_change=1.2,
                min_deficit=500,
                max_deficit=1000,
                protein_factor=2.4,
                macro_split=MacroSplit(protein=40, fat=30, carbs=30),
                lean_mass_preservation=0.85
            ),
            DietMode.STANDARD_CUT: DietConfig(
                name="Standard Cut",
                description="Balanced approach to fat loss",
                calorie_adjustment=0.80,
                min_weekly_change=0.5,
                max_weekly_change=1.0,
                min_deficit=400,
                max_deficit=750,
                protein_factor=2.2,
                macro_split=MacroSplit(protein=35, fat=30, carbs=35),
                lean_mass_preservation=0.9
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
                calorie_adjustment=1.10,
                min_weekly_change=0.2,
                max_weekly_change=0.4,
                min_deficit=200,
                max_deficit=400,
                protein_factor=2.0,
                macro_split=MacroSplit(protein=30, fat=25, carbs=45),
                lean_mass_preservation=1.0
            )
        }