# base_types.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
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

@dataclass
class UserStats:
    weight: float  # kg
    body_fat: float  # percentage
    target_weight: float
    target_body_fat: float
    activity_level: float = 1.55  # Default to moderately active

@dataclass
class DailyLog:
    date: datetime
    weight: float
    body_fat: float
    calories: int
    protein: float
    carbs: float
    fat: float
    lean_mass: Optional[float] = None
    fat_mass: Optional[float] = None

    def __post_init__(self):
        if self.weight and self.body_fat:
            self.fat_mass = self.weight * (self.body_fat / 100)
            self.lean_mass = self.weight - self.fat_mass

@dataclass
class MacroSplit:
    protein: float  # percentage of total calories
    fat: float
    carbs: float

    def validate(self) -> bool:
        return np.isclose(self.protein + self.fat + self.carbs, 100, atol=0.1)