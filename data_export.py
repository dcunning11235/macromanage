# data_export.py
import pandas as pd
from typing import Dict
from datetime import datetime
import json
from models import DailyLog
from progress_tracker import ProgressTracker


class DataManager:
    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker

    def to_dataframe(self) -> pd.DataFrame:
        """Convert tracking data to DataFrame with calculated metrics"""
        data = []
        for log in self.tracker.logs:
            data.append({
                'date': log.date,
                'weight': log.weight,
                'body_fat': log.body_fat,
                'calories': log.calories,
                'protein': log.protein,
                'carbs': log.carbs,
                'fat': log.fat,
                'lean_mass': log.lean_mass,
                'fat_mass': log.fat_mass
            })

        df = pd.DataFrame(data)

        # Add calculated columns
        df['weight_change'] = df['weight'].diff()
        df['lean_mass_change'] = df['lean_mass'].diff()
        df['fat_mass_change'] = df['fat_mass'].diff()

        # Add rolling averages
        df['weight_7day_avg'] = df['weight'].rolling(7).mean()
        df['calories_7day_avg'] = df['calories'].rolling(7).mean()

        # Add week-over-week changes
        df['weekly_weight_change'] = df['weight'].diff(7)
        df['weekly_lean_change'] = df['lean_mass'].diff(7)
        df['weekly_fat_change'] = df['fat_mass'].diff(7)

        return df

    def export_csv(self, filename: str):
        """Export data to CSV with summary statistics"""
        df = self.to_dataframe()

        # Export main data
        df.to_csv(filename, index=False)

        # Calculate summary statistics
        summary = {
            'start_date': df['date'].min(),
            'end_date': df['date'].max(),
            'total_days': len(df),
            'starting_weight': df['weight'].iloc[0],
            'ending_weight': df['weight'].iloc[-1],
            'total_weight_change': df['weight'].iloc[-1] - df['weight'].iloc[0],
            'avg_weekly_change': df['weekly_weight_change'].mean(),
            'avg_calories': df['calories'].mean(),
            'avg_protein': df['protein'].mean(),
            'adherence_rate': (df['calories'] > 0).mean() * 100
        }

        if df['lean_mass'].notna().any():
            summary.update({
                'lean_mass_change': df['lean_mass'].iloc[-1] - df['lean_mass'].iloc[0],
                'fat_mass_change': df['fat_mass'].iloc[-1] - df['fat_mass'].iloc[0]
            })

        # Export summary
        summary_filename = filename.replace('.csv', '_summary.csv')
        pd.DataFrame([summary]).to_csv(summary_filename, index=False)

        return f"Data exported to {filename} and summary to {summary_filename}"

    def get_weekly_summary(self) -> pd.DataFrame:
        """Generate weekly progress summary"""
        df = self.to_dataframe()
        df['week'] = pd.to_datetime(df['date']).dt.isocalendar().week

        weekly = df.groupby('week').agg({
            'weight': ['mean', 'min', 'max'],
            'calories': ['mean', 'std'],
            'protein': 'mean',
            'body_fat': 'mean',
            'lean_mass': 'mean',
            'fat_mass': 'mean'
        }).round(1)

        weekly['weight_change'] = weekly['weight']['mean'].diff()

        return weekly

    def save_json(self, filename: str):
        """Save all data to JSON format"""
        data = {
            'logs': [self._log_to_dict(log) for log in self.tracker.logs],
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_logs': len(self.tracker.logs),
                'date_range': {
                    'start': self.tracker.logs[0].date.isoformat(),
                    'end': self.tracker.logs[-1].date.isoformat()
                }
            }
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _log_to_dict(log: DailyLog) -> Dict:
        """Convert DailyLog to dictionary for JSON export"""
        return {
            'date': log.date.isoformat(),
            'weight': log.weight,
            'body_fat': log.body_fat,
            'calories': log.calories,
            'protein': log.protein,
            'carbs': log.carbs,
            'fat': log.fat,
            'lean_mass': log.lean_mass,
            'fat_mass': log.fat_mass
        }