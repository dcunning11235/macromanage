from dataclasses import dataclass
from typing import List, Dict
from base_types import UserStats, DietMode, DailyLog


@dataclass
class Adjustment:
    calories: int
    protein: int
    reason: str
    severity: str  # 'low', 'medium', 'high'
    suggestion: str


class DynamicAdjuster:
    def __init__(self, logs: List[DailyLog]):
        self.logs = logs

    def calculate_weekly_change(self, days: int = 7) -> Dict[str, float]:
        """Calculate rate of change for weight and body composition"""
        if len(self.logs) < days:
            return {}

        recent = sorted(self.logs[-days:], key=lambda x: x.date)
        start, end = recent[0], recent[-1]
        actual_days = (end.date - start.date).days
        weeks = actual_days / 7

        return {
            'weight_change': (end.weight - start.weight) / weeks,
            'lean_change': (end.lean_mass - start.lean_mass) / weeks if end.lean_mass and start.lean_mass else 0,
            'fat_change': (end.fat_mass - start.fat_mass) / weeks if end.fat_mass and start.fat_mass else 0
        }

    def detect_plateau(self, weeks: int = 3) -> bool:
        """Check if progress has stalled"""
        changes = self.calculate_weekly_change(weeks * 7)
        if not changes:
            return False
        return abs(changes.get('weight_change', 0)) < 0.2  # Less than 0.2kg/week change

    def check_diet_adherence(self, days: int = 14) -> float:
        """Calculate adherence to calorie targets"""
        if len(self.logs) < days:
            return 1.0

        recent = self.logs[-days:]
        adherent_days = sum(1 for log in recent if log.calories > 0)
        return adherent_days / len(recent)

    def calculate_adjustments(self, stats: UserStats, mode: DietMode) -> List[Adjustment]:
        """Calculate needed adjustments based on progress"""
        adjustments = []
        changes = self.calculate_weekly_change()

        if not changes:
            return adjustments

        weekly_change = changes['weight_change']

        # Adjust based on diet mode and progress
        if mode in [DietMode.AGGRESSIVE_CUT, DietMode.STANDARD_CUT]:
            # Weight loss modes
            target_loss = -0.8 if mode == DietMode.AGGRESSIVE_CUT else -0.5

            if weekly_change > target_loss * 0.5:  # Too slow
                adjustments.append(Adjustment(
                    calories=-250,
                    protein=0,
                    reason=f"Weight loss too slow ({abs(weekly_change):.1f} vs {abs(target_loss):.1f} kg/week)",
                    severity="medium",
                    suggestion="Reduce calories by 250 per day"
                ))
            elif weekly_change < target_loss * 1.5:  # Too fast
                adjustments.append(Adjustment(
                    calories=250,
                    protein=10,
                    reason=f"Weight loss too fast ({abs(weekly_change):.1f} vs {abs(target_loss):.1f} kg/week)",
                    severity="high",
                    suggestion="Increase calories by 250 and protein by 10g per day"
                ))

        elif mode in [DietMode.LEAN_BULK, DietMode.STANDARD_BULK]:
            # Weight gain modes
            target_gain = 0.25 if mode == DietMode.LEAN_BULK else 0.5

            if weekly_change < target_gain * 0.5:  # Too slow
                adjustments.append(Adjustment(
                    calories=250,
                    protein=0,
                    reason=f"Weight gain too slow ({weekly_change:.1f} vs {target_gain:.1f} kg/week)",
                    severity="medium",
                    suggestion="Increase calories by 250 per day"
                ))
            elif weekly_change > target_gain * 1.5:  # Too fast
                adjustments.append(Adjustment(
                    calories=-250,
                    protein=0,
                    reason=f"Weight gain too fast ({weekly_change:.1f} vs {target_gain:.1f} kg/week)",
                    severity="high",
                    suggestion="Reduce calories by 250 per day"
                ))

        # Check body composition
        if changes.get('lean_change', 0) < 0 and mode != DietMode.AGGRESSIVE_CUT:
            adjustments.append(Adjustment(
                calories=200,
                protein=25,
                reason="Losing lean mass",
                severity="high",
                suggestion="Increase calories by 200 and protein by 25g per day"
            ))

        # Check for plateaus
        if self.detect_plateau():
            # Adjust based on adherence
            adherence = self.check_diet_adherence()
            if adherence > 0.9:  # Good adherence, true plateau
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

        return adjustments

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