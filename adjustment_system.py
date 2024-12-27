from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from base_types import UserStats, DietMode, DailyLog


@dataclass
class Adjustment:
    calories: int
    protein: int
    reason: str
    severity: str  # 'low', 'medium', 'high'
    suggestion: str


class DynamicAdjuster:
    def __init__(self, tracker):
        self.tracker = tracker

    def calculate_adjustments(self, target_calories: int, stats: UserStats, mode: DietMode) -> List[Adjustment]:
        """Calculate needed adjustments based on progress"""
        adjustments = []
        changes = self.tracker.calculate_changes()

        if not changes:
            return adjustments

        weekly_change = changes['weight_change']
        current_body_fat = self.tracker.logs[-1].body_fat if self.tracker.logs else stats.body_fat

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
        is_plateaued = self.detect_plateau()
        if is_plateaued:
            adherence = self.check_adherence()
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

    def detect_plateau(self, weeks: int = 3) -> bool:
        """Check for plateaus in progress"""
        changes = self.tracker.calculate_changes(weeks * 7)
        return bool(changes and abs(changes.get('weight_change', 1.0)) < 0.2)

    def check_adherence(self, days: int = 14) -> float:
        """Check adherence to tracking"""
        adherence_stats = self.tracker.get_adherence_stats(days)
        return adherence_stats.get('calorie_adherence', 1.0)

    def get_net_adjustment(self, adjustments: List[Adjustment]) -> Dict[str, int]:
        """Combine all adjustments into final recommendations"""
        if not adjustments:
            return {'calories': 0, 'protein': 0}

        # Prioritize by severity
        high_priority = [adj for adj in adjustments if adj.severity == 'high']
        med_priority = [adj for adj in adjustments if adj.severity == 'medium']

        # Take the largest adjustment in each category
        calorie_adj = max([adj.calories for adj in high_priority], default=0) if high_priority else \
            max([adj.calories for adj in med_priority], default=0)

        protein_adj = max([adj.protein for adj in high_priority], default=0) if high_priority else \
            max([adj.protein for adj in med_priority], default=0)

        return {
            'calories': calorie_adj,
            'protein': protein_adj
        }