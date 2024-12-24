import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import json
from base_types import DailyLog
from progress_tracker import ProgressTracker
import csv
from pathlib import Path


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
                'fat_mass': log.fat_mass,
                'steps': log.steps,
                'water': log.water,
                'sleep': log.sleep,
                'notes': log.notes
            })

        df = pd.DataFrame(data)

        # Add calculated columns
        if not df.empty:
            df['weight_change'] = df['weight'].diff()
            df['lean_mass_change'] = df['lean_mass'].diff()
            df['fat_mass_change'] = df['fat_mass'].diff()

            # Add rolling averages
            df['weight_7day_avg'] = df['weight'].rolling(7).mean()
            df['calories_7day_avg'] = df['calories'].rolling(7).mean()
            df['protein_7day_avg'] = df['protein'].rolling(7).mean()

            # Add week-over-week changes
            df['weekly_weight_change'] = df['weight'].diff(7)
            df['weekly_lean_change'] = df['lean_mass'].diff(7)
            df['weekly_fat_change'] = df['fat_mass'].diff(7)

        return df

    def export_csv(self, filename: str) -> str:
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
            'weight': ['mean', 'min', 'max', 'std'],
            'calories': ['mean', 'std', 'count'],
            'protein': ['mean', 'min', 'max'],
            'body_fat': 'mean',
            'lean_mass': 'mean',
            'fat_mass': 'mean'
        }).round(1)

        weekly.columns = ['_'.join(col).strip() for col in weekly.columns.values]
        return weekly

    def export_json(self, filename: str) -> str:
        """Export all data in JSON format with metadata"""
        data = {
            'logs': [self._log_to_dict(log) for log in self.tracker.logs],
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_logs': len(self.tracker.logs),
                'date_range': {
                    'start': min(log.date for log in self.tracker.logs).isoformat(),
                    'end': max(log.date for log in self.tracker.logs).isoformat()
                }
            },
            'summary': self._generate_summary()
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        return f"Data exported to {filename}"

    def export_excel(self, filename: str) -> str:
        """Export data to Excel with multiple sheets"""
        df = self.to_dataframe()
        weekly = self.get_weekly_summary()
        summary = pd.DataFrame([self._generate_summary()])

        with pd.ExcelWriter(filename) as writer:
            df.to_excel(writer, sheet_name='Daily Logs', index=False)
            weekly.to_excel(writer, sheet_name='Weekly Summary')
            summary.to_excel(writer, sheet_name='Overall Summary', index=False)

            # Add some basic charts
            workbook = writer.book
            worksheet = writer.sheets['Daily Logs']

            # Weight progress chart
            chart = workbook.add_chart({'type': 'line'})
            chart.add_series({
                'name': 'Weight',
                'categories': f'=Daily Logs!$A$2:$A${len(df) + 1}',
                'values': f'=Daily Logs!$B$2:$B${len(df) + 1}'
            })
            worksheet.insert_chart('O2', chart)

        return f"Data exported to {filename}"

    def _log_to_dict(self, log: DailyLog) -> Dict:
        """Convert DailyLog to dictionary for export"""
        return {
            'date': log.date.isoformat(),
            'weight': log.weight,
            'body_fat': log.body_fat,
            'calories': log.calories,
            'protein': log.protein,
            'carbs': log.carbs,
            'fat': log.fat,
            'lean_mass': log.lean_mass,
            'fat_mass': log.fat_mass,
            'steps': log.steps,
            'water': log.water,
            'sleep': log.sleep,
            'notes': log.notes
        }

    def _generate_summary(self) -> Dict:
        """Generate overall progress summary"""
        df = self.to_dataframe()
        if df.empty:
            return {}

        return {
            'duration_days': len(df),
            'weight_change': float(df['weight'].iloc[-1] - df['weight'].iloc[0]),
            'average_weekly_change': float(df['weekly_weight_change'].mean()),
            'average_calories': float(df['calories'].mean()),
            'average_protein': float(df['protein'].mean()),
            'adherence_rate': float((df['calories'] > 0).mean() * 100),
            'body_fat_change': float(df['body_fat'].iloc[-1] - df['body_fat'].iloc[0])
            if df['body_fat'].notna().any() else None,
            'lean_mass_change': float(df['lean_mass'].iloc[-1] - df['lean_mass'].iloc[0])
            if df['lean_mass'].notna().any() else None
        }

    def import_csv(self, filename: str) -> List[DailyLog]:
        """Import data from CSV file"""
        df = pd.read_csv(filename)

        # Standardize column names
        df.columns = [col.lower().strip() for col in df.columns]

        # Map common column variations
        column_maps = {
            'date': ['date', 'day', 'log_date'],
            'weight': ['weight', 'body_weight', 'weight_kg'],
            'body_fat': ['body_fat', 'bodyfat', 'bf', 'body_fat_percent'],
            'calories': ['calories', 'kcal', 'total_calories'],
            'protein': ['protein', 'protein_g', 'prot'],
            'carbs': ['carbs', 'carbohydrates', 'carbs_g'],
            'fat': ['fat', 'fats', 'fat_g']
        }

        # Find matching columns
        column_mapping = {}
        for target, variations in column_maps.items():
            for var in variations:
                if var in df.columns:
                    column_mapping[var] = target
                    break

        # Rename columns
        df = df.rename(columns=column_mapping)

        # Convert date strings to datetime
        df['date'] = pd.to_datetime(df['date'])

        # Create DailyLog objects
        logs = []
        for _, row in df.iterrows():
            try:
                log = DailyLog(
                    date=row['date'].to_pydatetime(),
                    weight=float(row['weight']),
                    body_fat=float(row.get('body_fat', 0)),
                    calories=int(row['calories']),
                    protein=float(row['protein']),
                    carbs=float(row['carbs']),
                    fat=float(row['fat']),
                    steps=int(row['steps']) if 'steps' in row else None,
                    water=float(row['water']) if 'water' in row else None,
                    sleep=float(row['sleep']) if 'sleep' in row else None,
                    notes=row['notes'] if 'notes' in row else None
                )
                logs.append(log)
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping row due to error: {e}")

        return sorted(logs, key=lambda x: x.date)

    def import_json(self, filename: str) -> List[DailyLog]:
        """Import data from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)

        logs = []
        if isinstance(data, list):
            # Simple list of logs
            json_logs = data
        elif isinstance(data, dict) and 'logs' in data:
            # Our export format
            json_logs = data['logs']
        else:
            raise ValueError("Unrecognized JSON format")

        for log_data in json_logs:
            try:
                log = DailyLog(
                    date=datetime.fromisoformat(log_data['date']),
                    weight=float(log_data['weight']),
                    body_fat=float(log_data.get('body_fat', 0)),
                    calories=int(log_data['calories']),
                    protein=float(log_data['protein']),
                    carbs=float(log_data['carbs']),
                    fat=float(log_data['fat']),
                    steps=int(log_data['steps']) if 'steps' in log_data else None,
                    water=float(log_data['water']) if 'water' in log_data else None,
                    sleep=float(log_data['sleep']) if 'sleep' in log_data else None,
                    notes=log_data.get('notes')
                )
                logs.append(log)
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping log due to error: {e}")

        return sorted(logs, key=lambda x: x.date)

    def import_myfitnesspal_csv(self, filename: str) -> List[DailyLog]:
        """Import data from MyFitnessPal export CSV"""
        df = pd.read_csv(filename)

        # MyFitnessPal specific column mappings
        mfp_columns = {
            'Date': 'date',
            'Weight': 'weight',
            'Calories': 'calories',
            'Protein (g)': 'protein',
            'Carbohydrates (g)': 'carbs',
            'Fat (g)': 'fat'
        }

        df = df.rename(columns=mfp_columns)
        df['date'] = pd.to_datetime(df['date'])

        logs = []
        for _, row in df.iterrows():
            try:
                log = DailyLog(
                    date=row['date'].to_pydatetime(),
                    weight=float(row['weight']) if not pd.isna(row['weight']) else 0,
                    body_fat=0,  # MFP doesn't typically include body fat
                    calories=int(row['calories']),
                    protein=float(row['protein']),
                    carbs=float(row['carbs']),
                    fat=float(row['fat'])
                )
                logs.append(log)
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping row due to error: {e}")

        return sorted(logs, key=lambda x: x.date)

    def import_excel(self, filename: str) -> List[DailyLog]:
        """Import data from Excel file"""
        df = pd.read_excel(filename)
        return self._process_dataframe(df)

    def merge_logs(self, new_logs: List[DailyLog], strategy: str = 'replace') -> List[DailyLog]:
        """Merge new logs with existing logs"""
        # Create dictionary of existing logs by date
        existing_logs = {log.date.date(): log for log in self.tracker.logs}

        merged_logs = existing_logs.copy()

        for new_log in new_logs:
            log_date = new_log.date.date()
            if log_date in existing_logs:
                if strategy == 'replace':
                    merged_logs[log_date] = new_log
                elif strategy == 'update':
                    # Update only non-null values
                    existing_log = existing_logs[log_date]
                    merged_logs[log_date] = self._update_log(existing_log, new_log)
            else:
                merged_logs[log_date] = new_log

        return sorted(merged_logs.values(), key=lambda x: x.date)

    def _update_log(self, old_log: DailyLog, new_log: DailyLog) -> DailyLog:
        """Update log with non-null values from new log"""
        updated_data = {}
        for field in old_log.__dict__:
            old_value = getattr(old_log, field)
            new_value = getattr(new_log, field)
            if new_value is not None and new_value != 0:
                updated_data[field] = new_value
            else:
                updated_data[field] = old_value

        return DailyLog(**updated_data)

    def _process_dataframe(self, df: pd.DataFrame) -> List[DailyLog]:
        """Process a DataFrame into DailyLog objects"""
        # Standardize column names
        df.columns = [col.lower().strip() for col in df.columns]

        # Ensure required columns exist
        required_columns = ['date', 'weight', 'calories', 'protein', 'carbs', 'fat']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Convert date column
        df['date'] = pd.to_datetime(df['date'])

        logs = []
        for _, row in df.iterrows():
            try:
                log = DailyLog(
                    date=row['date'].to_pydatetime(),
                    weight=float(row['weight']),
                    body_fat=float(row.get('body_fat', 0)),
                    calories=int(row['calories']),
                    protein=float(row['protein']),
                    carbs=float(row['carbs']),
                    fat=float(row['fat']),
                    steps=int(row['steps']) if 'steps' in row else None,
                    water=float(row['water']) if 'water' in row else None,
                    sleep=float(row['sleep']) if 'sleep' in row else None,
                    notes=row['notes'] if 'notes' in row else None
                )
                logs.append(log)
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping row due to error: {e}")

        return sorted(logs, key=lambda x: x.date)

    def import_data(self, filename: str, source: str = None) -> List[DailyLog]:
        """Import data from file with automatic format detection"""
        file_ext = Path(filename).suffix.lower()

        if source == 'myfitnesspal':
            return self.import_myfitnesspal_csv(filename)

        importers = {
            '.csv': self.import_csv,
            '.json': self.import_json,
            '.xlsx': self.import_excel,
            '.xls': self.import_excel
        }

        if file_ext not in importers:
            raise ValueError(f"Unsupported file format: {file_ext}")

        return importers[file_ext](filename)