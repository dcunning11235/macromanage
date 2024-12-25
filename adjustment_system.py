from dataclasses import dataclass
from typing import List, Dict, Tuple
from base_types import UserStats, DietMode
from progress_tracker import ProgressTracker


@dataclass
class Adjustment:
    calories: int
    protein: int
    reason: str
    severity: str  # 'low', 'medium', 'high'
    suggestion: str


class DynamicAdjuster:
    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker

    def calculate_weekly_change(self, days: int = 7) -> Dict[str, float]:
        """Calculate rate of change for weight and body composition"""
        logs = self.tracker.logs
        if len(logs) < days:
            return {}

        recent = sorted(logs[-days:], key=lambda x: x.date)
        start, end = recent[0], recent[-1]
        actual_days = (end.date - start.date).days
        weeks = actual_days / 7

        return {
            'weight_change': (end.weight - start.weight) / weeks,
            'lean_change': (end.lean_mass - start.lean_mass) / weeks if end.lean_mass and start.lean_mass else 0,
            'fat_change': (end.fat_mass - start.fat_mass) / weeks if end.fat_mass and start.fat_mass else 0
        }

    def detect_plateau(self, weeks: int = 3) -> Tuple[bool, str]:
        """Check if progress has stalled"""
        changes = self.calculate_weekly_change(weeks * 7)
        if not changes or 'weight_change' not in changes:
            return False, "Insufficient data"

        if abs(changes.get('weight_change', 0)) < 0.2:  # Less than 0.2kg/week change
            adherence = self.check_diet_adherence()
            if adherence > 0.9:
                return True, "True plateau detected (good adherence)"
            else:
                return True, f"Plateau detected but adherence is low ({adherence:.0%})"

        return False, "No plateau detected"

    def check_diet_adherence(self, days: int = 14) -> float:
        """Calculate adherence to calorie targets"""
        logs = self.tracker.logs
        if len(logs) < days:
            return 1.0

        recent = logs[-days:]
        adherent_days = sum(1 for log in recent if log.calories > 0)
        return adherent_days / len(recent)

    def calculate_adjustments(self, stats: UserStats, mode: DietMode) -> List[Adjustment]:
        """Calculate needed adjustments based on progress"""
        adjustments = []
        changes = self.calculate_weekly_change()

        if not changes:
            return adjustments

        weekly_change = changes.get('weight_change', 0)
        logs = self.tracker.logs
        current_body_fat = logs[-1].body_fat if logs else stats.body_fat

        # Calculate adaptive adjustment size
        base_adjustment = self._calculate_adaptive_adjustment(weekly_change, mode, current_body_fat)

        # Weight loss modes
        if mode in [DietMode.AGGRESSIVE_CUT, DietMode.STANDARD_CUT]:
            target_loss = -0.8 if mode == DietMode.AGGRESSIVE_CUT else -0.5
            self._handle_weight_loss_adjustments(
                adjustments, weekly_change, target_loss, base_adjustment, changes
            )

        # Weight gain modes
        elif mode in [DietMode.LEAN_BULK, DietMode.STANDARD_BULK]:
            target_gain = 0.25 if mode == DietMode.LEAN_BULK else 0.5
            self._handle_weight_gain_adjustments(
                adjustments, weekly_change, target_gain, base_adjustment, changes
            )

        # Handle body composition changes
        self._handle_body_composition_adjustments(
            adjustments, changes, mode, current_body_fat
        )

        # Check for plateaus
        self._handle_plateau_adjustments(adjustments, mode)

        return adjustments

    def _calculate_adaptive_adjustment(
            self, weekly_change: float, mode: DietMode, body_fat: float
    ) -> int:
        """Calculate adaptive adjustment size based on current progress"""
        # Base adjustment size
        base = 200

        # Adjust based on body fat percentage
        if body_fat < 12:
            base *= 0.7  # Smaller adjustments for leaner individuals
        elif body_fat > 25:
            base *= 1.3  # Larger adjustments for higher body fat

        # Adjust based on rate of change
        if mode in [DietMode.AGGRESSIVE_CUT, DietMode.STANDARD_CUT]:
            target = -0.8 if mode == DietMode.AGGRESSIVE_CUT else -0.5
            deviation = abs(weekly_change - target)
        else:
            target = 0.25 if mode == DietMode.LEAN_BULK else 0.5
            deviation = abs(weekly_change - target)

        # Scale adjustment based on how far off target we are
        if deviation > 0.5:  # Significantly off target
            base *= 1.5
        elif deviation < 0.2:  # Close to target
            base *= 0.7

        return round(base)

    def _handle_weight_loss_adjustments(
            self, adjustments: List[Adjustment], weekly_change: float,
            target_loss: float, base_adjustment: int, changes: Dict[str, float]
    ) -> None:
        """Handle adjustments for weight loss phases"""
        if weekly_change > target_loss * 0.5:  # Too slow
            adjustments.append(Adjustment(
                calories=-base_adjustment,
                protein=0,
                reason=f"Weight loss too slow ({abs(weekly_change):.1f} vs {abs(target_loss):.1f} kg/week)",
                severity="medium",
                suggestion=f"Reduce calories by {base_adjustment} per day"
            ))
        elif weekly_change < target_loss * 1.5:  # Too fast
            adjustments.append(Adjustment(
                calories=base_adjustment,
                protein=round(base_adjustment / 40),  # Increase protein when losing too fast
                reason=f"Weight loss too fast ({abs(weekly_change):.1f} vs {abs(target_loss):.1f} kg/week)",
                severity="high",
                suggestion=f"Increase calories by {base_adjustment} and protein by {round(base_adjustment / 40)}g per day"
            ))

    def _handle_weight_gain_adjustments(
            self, adjustments: List[Adjustment], weekly_change: float,
            target_gain: float, base_adjustment: int, changes: Dict[str, float]
    ) -> None:
        """Handle adjustments for weight gain phases"""
        if weekly_change < target_gain * 0.5:  # Too slow
            adjustments.append(Adjustment(
                calories=base_adjustment,
                protein=0,
                reason=f"Weight gain too slow ({weekly_change:.1f} vs {target_gain:.1f} kg/week)",
                severity="medium",
                suggestion=f"Increase calories by {base_adjustment} per day"
            ))
        elif weekly_change > target_gain * 1.5:  # Too fast
            adjustments.append(Adjustment(
                calories=-base_adjustment,
                protein=0,
                reason=f"Weight gain too fast ({weekly_change:.1f} vs {target_gain:.1f} kg/week)",
                severity="high",
                suggestion=f"Reduce calories by {base_adjustment} per day"
            ))

    def _handle_body_composition_adjustments(
            self, adjustments: List[Adjustment], changes: Dict[str, float],
            mode: DietMode, body_fat: float
    ) -> None:
        """Handle adjustments based on body composition changes"""
        lean_change = changes.get('lean_change', 0)

        if lean_change < 0 and mode != DietMode.AGGRESSIVE_CUT:
            # Adjust protein based on current body fat
            protein_increase = 25 if body_fat > 20 else 35

            adjustments.append(Adjustment(
                calories=200,
                protein=protein_increase,
                reason="Losing lean mass",
                severity="high",
                suggestion=f"Increase calories by 200 and protein by {protein_increase}g per day"
            ))

    def _handle_plateau_adjustments(
            self, adjustments: List[Adjustment], mode: DietMode
    ) -> None:
        """Handle adjustments for plateaus"""
        is_plateaued, message = self.detect_plateau()
        if is_plateaued:
            adherence = self.check_diet_adherence()
            if adherence > 0.9:  # Good adherence
                if mode in [DietMode.AGGRESSIVE_CUT, DietMode.STANDARD_CUT]:
                    adjustments.append(Adjustment(
                        calories=-300,
                        protein=0,
                        reason="Progress has plateaued with good adherence",
                        severity="medium",
                        suggestion="Reduce calories by 300 per day or implement a diet break"
                    ))
                elif mode in [DietMode.LEAN_BULK, DietMode.STANDARD_BULK]:
                    adjustments.append(Adjustment(
                        calories=300,
                        protein=0,
                        reason="Progress has plateaued with good adherence",
                        severity="medium",
                        suggestion="Increase calories by 300 per day"
                    ))
            else:
                adjustments.append(Adjustment(
                    calories=0,
                    protein=0,
                    reason="Apparent plateau but adherence is low",
                    severity="low",
                    suggestion="Focus on consistency before making adjustments"
                ))