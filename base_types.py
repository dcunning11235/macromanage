from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
from enum import Enum
import numpy as np

class NutrientType(Enum):
    PROTEIN = "protein"
    CARBS = "carbs"
    FAT = "fat"

class DietMode(Enum):
    AGGRESSIVE_CUT = "aggressive_cut"
    STANDARD_CUT = "standard_cut"
    CONSERVATIVE_CUT = "conservative_cut"
    MAINTENANCE = "maintenance"
    LEAN_BULK = "lean_bulk"
    STANDARD_BULK = "standard_bulk"

class TrainingLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class ActivityLevel(Enum):
    SEDENTARY = 1.2
    LIGHT = 1.375
    MODERATE = 1.55
    VERY_ACTIVE = 1.725
    EXTREMELY_ACTIVE = 1.9

class MacroPreset(Enum):
    BALANCED = "balanced"
    HIGH_PROTEIN = "high_protein"
    KETO = "keto"
    HIGH_CARB = "high_carb"
    LEAN_BULK = "lean_bulk"
    PERFORMANCE = "performance"
    CUSTOM = "custom"

@dataclass
class MacroSplitConfig:
    name: str
    description: str
    protein_factor: float  # g/kg of body weight or lean mass
    fat_ratio: float  # percentage of total calories
    min_fat: float  # minimum grams per kg bodyweight
    protein_source: str = "body_weight"  # or "lean_mass"

class MacroPresets:
    @staticmethod
    def get_presets() -> Dict[MacroPreset, MacroSplitConfig]:
        return {
            MacroPreset.BALANCED: MacroSplitConfig(
                name="Balanced",
                description="Standard macro split suitable for general fitness",
                protein_factor=2.0,
                fat_ratio=0.30,
                min_fat=0.8
            ),
            MacroPreset.HIGH_PROTEIN: MacroSplitConfig(
                name="High Protein",
                description="Extra protein for muscle preservation during cuts",
                protein_factor=2.4,
                fat_ratio=0.25,
                min_fat=0.8,
                protein_source="lean_mass"
            ),
            MacroPreset.KETO: MacroSplitConfig(
                name="Ketogenic",
                description="Very low carb, high fat for ketosis",
                protein_factor=2.0,
                fat_ratio=0.70,
                min_fat=1.2
            ),
            MacroPreset.HIGH_CARB: MacroSplitConfig(
                name="High Carb",
                description="Higher carbs for endurance training",
                protein_factor=1.8,
                fat_ratio=0.20,
                min_fat=0.6
            ),
            MacroPreset.LEAN_BULK: MacroSplitConfig(
                name="Lean Bulk",
                description="Optimized for lean muscle gain",
                protein_factor=2.2,
                fat_ratio=0.25,
                min_fat=0.8,
                protein_source="lean_mass"
            ),
            MacroPreset.PERFORMANCE: MacroSplitConfig(
                name="Performance",
                description="Balanced split for athletic performance",
                protein_factor=2.0,
                fat_ratio=0.25,
                min_fat=0.8
            ),
            MacroPreset.CUSTOM: MacroSplitConfig(
                name="Custom",
                description="User-defined macro split",
                protein_factor=2.0,
                fat_ratio=0.30,
                min_fat=0.8
            )
        }

@dataclass
class UserStats:
    """Core user statistics and goals"""
    weight: float  # kg
    body_fat: float  # percentage
    target_weight: float
    target_body_fat: float
    height: Optional[float] = None  # cm
    age: Optional[int] = None
    gender: Optional[str] = None
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    training_level: TrainingLevel = TrainingLevel.INTERMEDIATE

    def calculate_lean_mass(self) -> float:
        """Calculate lean body mass in kg"""
        return self.weight * (1 - self.body_fat / 100)

    def calculate_fat_mass(self) -> float:
        """Calculate fat mass in kg"""
        return self.weight * (self.body_fat / 100)

    def calculate_bmi(self) -> Optional[float]:
        """Calculate BMI if height is available"""
        if self.height:
            return self.weight / ((self.height / 100) ** 2)
        return None

@dataclass
class DailyLog:
    """Single day's worth of tracking data"""
    date: datetime
    weight: float
    body_fat: float
    calories: int
    protein: float
    carbs: float
    fat: float
    lean_mass: Optional[float] = None
    fat_mass: Optional[float] = None
    steps: Optional[int] = None
    water: Optional[float] = None  # liters
    sleep: Optional[float] = None  # hours
    notes: Optional[str] = None

    def __post_init__(self):
        """Calculate body composition metrics after initialization"""
        if self.weight and self.body_fat:
            self.fat_mass = self.weight * (self.body_fat / 100)
            self.lean_mass = self.weight - self.fat_mass

    def calculate_total_calories(self) -> int:
        """Calculate total calories from macros"""
        return round(
            self.protein * 4 +
            self.carbs * 4 +
            self.fat * 9
        )

    def validate_macros(self) -> bool:
        """Check if logged macros match total calories"""
        macro_calories = self.calculate_total_calories()
        return abs(macro_calories - self.calories) < 10  # Allow small difference