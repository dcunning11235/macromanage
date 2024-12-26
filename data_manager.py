from typing import List, Dict, Optional, Union
from datetime import datetime
import pandas as pd
import numpy as np
import json
from io import BytesIO
from pathlib import Path
from base_types import DailyLog


class DataManager:
    def __init__(self, tracker):
        self.tracker = tracker

    def to_dataframe(self) -> pd.DataFrame:
        """Convert tracking data to DataFrame with calculated metrics"""
        data = []
        for log in self.tracker.logs:
            data.append({
                'date': log.date,
                'weight': log.weight if log.weight != 0 else np.nan,
                'body_fat': log.body_fat if log.body_fat != 0 else np.nan,
                'calories': log.calories if log.calories != 0 else np.nan,
                'protein': log.protein if log.protein != 0 else np.nan,
                'carbs': log.carbs if log.carbs != 0 else np.nan,
                'fat': log.fat if log.fat != 0 else np.nan,
                'lean_mass': log.lean_mass if log.lean_mass is not None and log.lean_mass != 0 else np.nan,
                'fat_mass': log.fat_mass if log.fat_mass is not None and log.fat_mass != 0 else np.nan,
                'steps': log.steps if log.steps is not None and log.steps != 0 else np.nan,
                'water': log.water if log.water is not None and log.water != 0 else np.nan,
                'sleep': log.sleep if log.sleep is not None and log.sleep != 0 else np.nan,
                'notes': log.notes
            })

        df = pd.DataFrame(data)

        # Set proper data types
        df = df.astype({
            'date': 'datetime64[ns]',
            'weight': 'float64',
            'body_fat': 'float64',
            'calories': 'float64',
            'protein': 'float64',
            'carbs': 'float64',
            'fat': 'float64',
            'lean_mass': 'float64',
            'fat_mass': 'float64',
            'steps': 'float64',  # float to handle NaN values
            'water': 'float64',
            'sleep': 'float64',
            'notes': 'object'
        })

        # Add calculated columns if we have data
        if not df.empty:
            # Weight changes
            df['weight_change'] = df['weight'].diff()
            df['lean_mass_change'] = df['lean_mass'].diff()
            df['fat_mass_change'] = df['fat_mass'].diff()

            # Rolling averages
            df['weight_7day_avg'] = df['weight'].rolling(7, min_periods=1).mean()
            df['calories_7day_avg'] = df['calories'].rolling(7, min_periods=1).mean()
            df['protein_7day_avg'] = df['protein'].rolling(7, min_periods=1).mean()

            # Week-over-week changes
            df['weekly_weight_change'] = df['weight'].diff(7)
            df['weekly_lean_change'] = df['lean_mass'].diff(7)
            df['weekly_fat_change'] = df['fat_mass'].diff(7)

        return df

    def get_weekly_summary(self) -> pd.DataFrame:
        """Generate weekly progress summary"""
        df = self.to_dataframe()
        if df.empty:
            return pd.DataFrame()

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

    def export_json(self, filename: str) -> str:
        """Export data in JSON format with metadata"""
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
            json.dump(data, f, indent=2, default=str)

        return f"Data exported to {filename}"

    def export_excel(self, filename: str) -> str:
        """Export data to Excel with multiple sheets and charts"""
        df = self.to_dataframe()
        weekly = self.get_weekly_summary()
        summary = pd.DataFrame([self._generate_summary()])

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Daily Logs', index=False)
            weekly.to_excel(writer, sheet_name='Weekly Summary')
            summary.to_excel(writer, sheet_name='Overall Summary', index=False)

        return f"Data exported to {filename}"

    def import_data(self, file: Union[str, BytesIO, Path], source: str = None, units: str = 'metric') -> List[DailyLog]:
        """
        Import data with automatic format detection

        Args:
            file: File path or uploaded file object
            source: Source of the data (e.g., 'myfitnesspal')
            units: Unit system of the input data ('metric' or 'imperial')
        """
        if isinstance(file, (str, Path)):
            file_ext = Path(str(file)).suffix.lower()
        else:  # BytesIO from file upload
            file_ext = Path(getattr(file, 'name', '')).suffix.lower()
            if not file_ext:
                raise ValueError("Could not determine file type")

        if source == 'myfitnesspal':
            return self.import_myfitnesspal_csv(file, units=units)

        importers = {
            '.csv': self.import_csv,
            '.json': self.import_json,
            '.xlsx': self.import_excel,
            '.xls': self.import_excel
        }

        if file_ext not in importers:
            raise ValueError(f"Unsupported file format: {file_ext}")

        return importers[file_ext](file, units=units)

    def _convert_units(self, df: pd.DataFrame, units: str) -> pd.DataFrame:
        """Convert units from input system to metric"""
        if units == 'metric':
            return df

        # Deep copy to avoid modifying original
        df = df.copy()

        # Convert weight from lbs to kg
        if 'weight' in df.columns:
            df['weight'] = df['weight'] / 2.20462

        # Convert water from fl oz to liters
        if 'water' in df.columns and not df['water'].isna().all():
            df['water'] = df['water'] / 33.814

        return df

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

    def import_csv(self, file: Union[str, BytesIO, Path], units: str = 'metric') -> List[DailyLog]:
        """Import data from CSV file or BytesIO object"""
        if isinstance(file, (str, Path)):
            df = pd.read_csv(file)
        else:  # BytesIO from file upload
            df = pd.read_csv(file)

        # Convert units if needed
        df = self._convert_units(df, units)

        return self._process_dataframe(df)

    def import_json(self, file: Union[str, BytesIO, Path], units: str = 'metric') -> List[DailyLog]:
        """Import data from JSON file or BytesIO object"""
        if isinstance(file, (str, Path)):
            with open(file, 'r') as f:
                data = json.load(f)
        else:  # BytesIO from file upload
            data = json.load(file)

        if isinstance(data, list):
            json_logs = data
        elif isinstance(data, dict) and 'logs' in data:
            json_logs = data['logs']
        else:
            raise ValueError("Unrecognized JSON format")

        # If imperial units, convert the values in the JSON data
        if units == 'imperial':
            for log in json_logs:
                if 'weight' in log:
                    log['weight'] = float(log['weight']) / 2.20462
                if 'water' in log and log['water'] is not None:
                    log['water'] = float(log['water']) / 33.814

        return self._process_json_logs(json_logs)

    def import_excel(self, file: Union[str, BytesIO, Path], units: str = 'metric') -> List[DailyLog]:
        """Import data from Excel file or BytesIO object"""
        if isinstance(file, (str, Path)):
            df = pd.read_excel(file)
        else:  # BytesIO from file upload
            df = pd.read_excel(file)

        # Convert units if needed
        df = self._convert_units(df, units)

        return self._process_dataframe(df)

    def import_myfitnesspal_csv(self, file: Union[str, BytesIO, Path], units: str = 'metric') -> List[DailyLog]:
        """Import data from MyFitnessPal export CSV"""
        if isinstance(file, (str, Path)):
            df = pd.read_csv(file)
        else:  # BytesIO from file upload
            df = pd.read_csv(file)

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

        # Convert units if needed (MyFitnessPal typically uses imperial units)
        df = self._convert_units(df, units)

        return self._process_dataframe(df)

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

    def _process_json_logs(self, json_logs: List[Dict]) -> List[DailyLog]:
        """Convert JSON log data to DailyLog objects"""
        logs = []
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

    def _update_log(self, old_log: DailyLog, new_log: DailyLog) -> DailyLog:
        """Update log with non-null values from new log"""
        updated_data = {}
        for field in vars(old_log):
            old_value = getattr(old_log, field)
            new_value = getattr(new_log, field)
            if new_value is not None and new_value != 0:
                updated_data[field] = new_value
            else:
                updated_data[field] = old_value

            return DailyLog(**updated_data)

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