from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum
import numpy as np


class DietMode(Enum):
    """Different diet modes with specific targets and adjustments"""
    AGGRESSIVE_CUT = "aggressive_cut"
    STANDARD_CUT = "standard_cut"
    CONSERVATIVE_CUT = "conservative_cut"
    MAINTENANCE = "maintenance"
    LEAN_BULK = "lean_bulk"
    STANDARD_BULK = "standard_bulk"


class TrainingLevel(Enum):
    """User's training experience level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ActivityLevel(Enum):
    """Daily activity multipliers for TDEE calculation"""
    SEDENTARY = 1.2
    LIGHT = 1.375
    MODERATE = 1.55
    VERY_ACTIVE = 1.725
    EXTREMELY_ACTIVE = 1.9


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
class MacroSplit:
    """Defines the ratio of macronutrients"""
    protein: float  # percentage of total calories
    fat: float
    carbs: float

    def validate(self) -> bool:
        """Ensure macro percentages sum to 100"""
        return np.isclose(self.protein + self.fat + self.carbs, 100, atol=0.1)

    def to_grams(self, total_calories: float) -> dict:
        """Convert percentage-based macros to grams"""
        protein_cals = total_calories * (self.protein / 100)
        fat_cals = total_calories * (self.fat / 100)
        carb_cals = total_calories * (self.carbs / 100)

        return {
            'protein': round(protein_cals / 4),  # 4 calories per gram
            'fat': round(fat_cals / 9),  # 9 calories per gram
            'carbs': round(carb_cals / 4)  # 4 calories per gram
        }


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


@dataclass
class ProgressMetrics:
    """Calculated progress metrics"""
    weight_change: float  # kg per week
    fat_mass_change: float
    lean_mass_change: float
    average_calories: float
    average_protein: float
    adherence_rate: float  # percentage of days logged
    trend_direction: str  # 'increasing', 'decreasing', or 'stable'

    @classmethod
    def from_logs(cls, logs: list[DailyLog], days: int = 7):
        """Calculate progress metrics from a list of daily logs"""
        if len(logs) < 2:
            return None

        recent = sorted(logs[-days:], key=lambda x: x.date)
        start, end = recent[0], recent[-1]
        weeks = (end.date - start.date).days / 7

        return cls(
            weight_change=(end.weight - start.weight) / weeks,
            fat_mass_change=(end.fat_mass - start.fat_mass) / weeks if end.fat_mass and start.fat_mass else 0,
            lean_mass_change=(end.lean_mass - start.lean_mass) / weeks if end.lean_mass and start.lean_mass else 0,
            average_calories=sum(log.calories for log in recent) / len(recent),
            average_protein=sum(log.protein for log in recent) / len(recent),
            adherence_rate=len(recent) / days * 100,
            trend_direction='increasing' if end.weight > start.weight else 'decreasing' if end.weight < start.weight else 'stable'
        )