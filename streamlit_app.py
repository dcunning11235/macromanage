import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import json
from pathlib import Path
from typing import List
from macro_tracker import MacroTracker
from base_types import UserStats, DailyLog, DietMode, ActivityLevel, TrainingLevel, MacroPreset, MacroPresets


# Unit conversion functions
def kg_to_lbs(kg: float) -> float:
    """Convert kilograms to pounds"""
    return kg * 2.20462


def lbs_to_kg(lbs: float) -> float:
    """Convert pounds to kilograms"""
    return lbs / 2.20462


def cm_to_inches(cm: float) -> float:
    """Convert centimeters to inches"""
    return cm / 2.54


def inches_to_cm(inches: float) -> float:
    """Convert inches to centimeters"""
    return inches * 2.54


def l_to_fl_oz(liters: float) -> float:
    """Convert liters to fluid ounces"""
    return liters * 33.814


def fl_oz_to_l(fl_oz: float) -> float:
    """Convert fluid ounces to liters"""
    return fl_oz / 33.814


def l_to_cups(liters: float) -> float:
    """Convert liters to cups"""
    return liters * 4.227


def cups_to_l(cups: float) -> float:
    """Convert cups to liters"""
    return cups / 4.227


def format_weight(weight: float, unit_system: str) -> str:
    """Format weight with appropriate unit"""
    if unit_system == 'imperial':
        return f"{kg_to_lbs(weight):.1f} lbs"
    return f"{weight:.1f} kg"


def format_height(height: float, unit_system: str) -> str:
    """Format height with appropriate unit"""
    if unit_system == 'imperial':
        inches = cm_to_inches(height)
        feet = int(inches // 12)
        remaining_inches = inches % 12
        return f"{feet}'{remaining_inches:.1f}\""
    return f"{height:.1f} cm"


def format_volume(volume: float, unit_system: str) -> str:
    """Format volume with appropriate unit"""
    if unit_system == 'imperial':
        if volume > 4:  # Use cups for larger amounts
            cups = l_to_cups(volume)
            return f"{cups:.1f} cups"
        else:  # Use fl oz for smaller amounts
            fl_oz = l_to_fl_oz(volume)
            return f"{fl_oz:.1f} fl oz"
    return f"{volume:.1f} L"


def calculate_projected_weight_change(target_calories: int, maintenance_calories: int,
                                      unit_system: str = 'metric') -> str:
    """Calculate and format projected weekly weight change"""
    daily_deficit = target_calories - maintenance_calories
    weekly_cal_deficit = daily_deficit * 7

    # 3500 calories per pound of body weight
    weekly_lb_change = weekly_cal_deficit / 3500
    weekly_kg_change = weekly_lb_change / 2.20462

    if abs(weekly_lb_change) < 0.1:  # Less than 0.1 lbs/week is negligible
        return "Projected to maintain weight"

    direction = "loss" if weekly_lb_change < 0 else "gain"

    if unit_system == 'imperial':
        return (f"Projected weekly {direction}: "
                f"{abs(weekly_lb_change):.1f} lbs")
    else:
        return (f"Projected weekly {direction}: "
                f"{abs(weekly_kg_change):.1f} kg")


def save_preferences(preferences: dict):
    """Save user preferences to file"""
    prefs_file = Path("user_preferences.json")
    try:
        prefs_file.write_text(json.dumps(preferences))
    except Exception as e:
        st.warning(f"Could not save preferences: {e}")


def load_preferences() -> dict:
    """Load user preferences from file"""
    prefs_file = Path("user_preferences.json")
    default_prefs = {
        "unit_system": "metric",
        "diet_mode": "STANDARD_CUT",
        "macro_preset": "BALANCED",
        "custom_macro_settings": {
            "protein_factor": 2.0,
            "fat_ratio": 0.30,
            "min_fat": 0.8,
            "protein_source": "body_weight"
        }
    }

    if prefs_file.exists():
        try:
            saved_prefs = json.loads(prefs_file.read_text())
            # Merge with defaults in case new preferences were added
            return {**default_prefs, **saved_prefs}
        except Exception:
            pass
    return default_prefs


def initialize_session_state():
    """Initialize session state variables"""
    if 'tracker' not in st.session_state:
        st.session_state.tracker = MacroTracker()
    if 'current_stats' not in st.session_state:
        st.session_state.current_stats = None
    if 'preferences' not in st.session_state:
        st.session_state.preferences = load_preferences()


def create_metrics_chart(df: pd.DataFrame, metrics: List[str]) -> go.Figure:
    """Create a line chart for selected metrics"""
    fig = go.Figure()

    for metric in metrics:
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df[metric],
            name=metric.replace('_', ' ').title(),
            mode='lines+markers'
        ))

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        title_text='Progress Over Time',
        hovermode='x'
    )

    return fig


def show_settings_sidebar():
    """Display settings sidebar"""
    with st.sidebar:
        st.header("User Settings")

        # Add unit system selection
        unit_system = st.radio(
            "Unit System",
            options=['metric', 'imperial'],
            index=0 if st.session_state.preferences["unit_system"] == "metric" else 1,
            key="unit_system",
            on_change=lambda: save_preferences(st.session_state.preferences)
        )
        st.session_state.preferences["unit_system"] = unit_system

        # Basic Info
        if unit_system == 'imperial':
            weight = lbs_to_kg(st.number_input("Current Weight (lbs)", 90.0, 440.0, 176.0, key="settings_weight"))
            height = inches_to_cm(st.number_input("Height (inches)", 48.0, 96.0, 67.0, key="settings_height"))
            target_weight = lbs_to_kg(
                st.number_input("Target Weight (lbs)", 90.0, 440.0, 165.0, key="settings_target_weight"))
        else:
            weight = st.number_input("Current Weight (kg)", 40.0, 200.0, 80.0, key="settings_weight")
            height = st.number_input("Height (cm)", 100.0, 250.0, 170.0, key="settings_height")
            target_weight = st.number_input("Target Weight (kg)", 40.0, 200.0, 75.0, key="settings_target_weight")

        body_fat = st.number_input("Body Fat %", 5.0, 50.0, 15.0, key="settings_bf")
        target_bf = st.number_input("Target Body Fat %", 5.0, 50.0, 12.0, key="settings_target_bf")

        # Additional Settings
        activity = st.selectbox(
            "Activity Level",
            options=[level.name for level in ActivityLevel],
            format_func=lambda x: x.replace('_', ' ').title(),
            key="settings_activity"
        )

        training = st.selectbox(
            "Training Experience",
            options=[level.name for level in TrainingLevel],
            format_func=lambda x: x.replace('_', ' ').title(),
            key="settings_training"
        )

        # Diet Mode selection with persistence
        diet_mode = st.selectbox(
            "Diet Mode",
            options=[mode.name for mode in DietMode],
            index=[mode.name for mode in DietMode].index(st.session_state.preferences["diet_mode"]),
            format_func=lambda x: x.replace('_', ' ').title(),
            key="settings_diet_mode",
            on_change=lambda: _save_diet_preferences()
        )

        preset_config = MacroPresets.get_presets()

        # Macro Preset selection with persistence
        macro_preset = st.selectbox(
            "Macro Split Preset",
            options=[preset.name for preset in MacroPreset],
            index=[preset.name for preset in MacroPreset].index(st.session_state.preferences["macro_preset"]),
            format_func=lambda x: preset_config[MacroPreset[x]].name,
            key="settings_macro_preset",
            on_change=lambda: _save_diet_preferences()
        )

        # Show custom macro inputs if custom selected
        if macro_preset == MacroPreset.CUSTOM.name:
            with st.expander("Custom Macro Settings"):
                custom_settings = st.session_state.preferences["custom_macro_settings"]
                new_protein_factor = st.number_input(
                    "Protein (g/kg bodyweight)",
                    min_value=1.0,
                    max_value=3.0,
                    value=float(custom_settings["protein_factor"]),
                    step=0.1,
                    key="custom_protein_factor"
                )
                new_fat_ratio = st.slider(
                    "Fat (% of total calories)",
                    min_value=15,
                    max_value=75,
                    value=int(custom_settings["fat_ratio"] * 100),
                    key="custom_fat_ratio"
                )
                new_min_fat = st.number_input(
                    "Minimum Fat (g/kg bodyweight)",
                    min_value=0.3,
                    max_value=2.0,
                    value=float(custom_settings["min_fat"]),
                    step=0.1,
                    key="custom_min_fat"
                )
                new_protein_source = st.radio(
                    "Calculate protein based on",
                    options=["body_weight", "lean_mass"],
                    index=0 if custom_settings["protein_source"] == "body_weight" else 1,
                    key="custom_protein_source"
                )

                # Update custom settings in preferences
                st.session_state.preferences["custom_macro_settings"].update({
                    "protein_factor": new_protein_factor,
                    "fat_ratio": new_fat_ratio / 100,
                    "min_fat": new_min_fat,
                    "protein_source": new_protein_source
                })
                save_preferences(st.session_state.preferences)

        # Optional Info
        with st.expander("Additional Information"):
            age = st.number_input("Age", 18, 100, 30, key="settings_age")
            gender = st.selectbox("Gender", ["male", "female"], key="settings_gender")

        # Create UserStats object
        st.session_state.current_stats = UserStats(
            weight=weight,
            body_fat=body_fat,
            target_weight=target_weight,
            target_body_fat=target_bf,
            height=height,
            age=age,
            gender=gender,
            activity_level=ActivityLevel[activity],
            training_level=TrainingLevel[training]
        )

        return DietMode[diet_mode], MacroPreset[macro_preset]


def _save_diet_preferences():
    """Helper function to save diet and macro preferences"""
    st.session_state.preferences.update({
        "diet_mode": st.session_state.settings_diet_mode,
        "macro_preset": st.session_state.settings_macro_preset
    })
    save_preferences(st.session_state.preferences)


def show_daily_log_tab():
    """Display daily logging interface"""
    st.header("Daily Log")

    unit_system = st.session_state.preferences["unit_system"]

    col1, col2, col3 = st.columns(3)

    with col1:
        log_date = st.date_input("Date", datetime.now(), key="log_date")
        if unit_system == 'imperial':
            weight_lbs = st.number_input(
                "Weight (lbs)", 0.0, 660.0,
                kg_to_lbs(st.session_state.current_stats.weight),
                key="log_weight"
            )
            log_weight = lbs_to_kg(weight_lbs)
        else:
            log_weight = st.number_input(
                "Weight (kg)", 0.0, 300.0,
                st.session_state.current_stats.weight,
                key="log_weight"
            )
        log_bf = st.number_input("Body Fat %", 0.0, 50.0,
                                 st.session_state.current_stats.body_fat,
                                 key="log_bf")

    with col2:
        calories = st.number_input("Calories", 0, 10000, 2000, key="log_calories")
        protein = st.number_input("Protein (g)", 0, 500, 150, key="log_protein")
        carbs = st.number_input("Carbs (g)", 0, 1000, 200, key="log_carbs")
        fat = st.number_input("Fat (g)", 0, 200, 70, key="log_fat")

    with col3:
        steps = st.number_input("Steps", 0, 100000, 0, key="log_steps")
        if unit_system == 'imperial':
            water_cups = st.number_input("Water (cups)", 0.0, 20.0, 0.0, key="log_water")
            water = cups_to_l(water_cups)
        else:
            water = st.number_input("Water (L)", 0.0, 10.0, 0.0, key="log_water")
        sleep = st.number_input("Sleep (hours)", 0.0, 24.0, 0.0, key="log_sleep")
        notes = st.text_area("Notes", "", key="log_notes")

    if st.button("Add Log", key="btn_add_log"):
        log = DailyLog(
            date=datetime.combine(log_date, datetime.min.time()),
            weight=log_weight,
            body_fat=log_bf,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            steps=steps,
            water=water,
            sleep=sleep,
            notes=notes
        )
        st.session_state.tracker.add_log(log)
        st.success("Log added successfully!")


def show_recommendations_tab(diet_mode: DietMode, macro_preset: MacroPreset):
    """Display recommendations with manual adjustments and projections"""
    st.header("Your Recommendations")

    if not st.session_state.current_stats:
        st.warning("Please set your stats in the sidebar first.")
        return

    recs = st.session_state.tracker.get_recommendations(st.session_state.current_stats, diet_mode, macro_preset)

    # Base calories and manual adjustment
    if 'calories' in recs:
        st.subheader("Calorie Targets")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.metric("Base Target Calories", f"{recs['calories']} kcal")

        with col2:
            calorie_adjustment = st.number_input(
                "Adjust Calories",
                min_value=-500,
                max_value=500,
                value=0,
                step=25,
                help="Fine-tune your daily calories"
            )

        adjusted_calories = recs['calories'] + calorie_adjustment

        with col3:
            st.metric("Adjusted Target Calories", f"{adjusted_calories} kcal")

        # Show projected weekly changes
        if 'maintenance_calories' in recs:
            projection = calculate_projected_weight_change(
                adjusted_calories,
                recs['maintenance_calories'],
                st.session_state.preferences["unit_system"]
            )
            st.info(projection)

        # Recalculate macros based on adjusted calories
        if calorie_adjustment != 0:
            macros = st.session_state.tracker.calculator.calculate_macros(
                adjusted_calories,
                st.session_state.current_stats,
                diet_mode
            )
        else:
            macros = recs['macros']

        # Display macros
        st.subheader("Macro Targets")
        macro_cols = st.columns(3)
        with macro_cols[0]:
            st.metric("Protein", f"{macros['protein']}g")
        with macro_cols[1]:
            st.metric("Carbs", f"{macros['carbs']}g")
        with macro_cols[2]:
            st.metric("Fat", f"{macros['fat']}g")

        # Display ratios if available
        if 'ratios' in macros:
            ratio_cols = st.columns(3)
            with ratio_cols[0]:
                st.caption(f"Protein: {macros['ratios']['protein']}%")
            with ratio_cols[1]:
                st.caption(f"Carbs: {macros['ratios']['carbs']}%")
            with ratio_cols[2]:
                st.caption(f"Fat: {macros['ratios']['fat']}%")

    # Display meal timing if available
    if 'meal_timing' in recs and recs['meal_timing']:
        st.subheader("Meal Timing")
        meal_cols = st.columns(len(recs['meal_timing']))
        total_calories = adjusted_calories if 'calories' in recs else sum(recs['meal_timing'].values())

        for i, (meal, cals) in enumerate(recs['meal_timing'].items()):
            # Adjust meal calories proportionally
            if 'calories' in recs:
                cals = round(cals * (adjusted_calories / recs['calories']))
            with meal_cols[i]:
                st.metric(meal.replace('_', ' ').title(), f"{cals} kcal")

        # Display minimum nutrients if available
        if 'minimum_nutrients' in recs and recs['minimum_nutrients']:
            st.subheader("Minimum Daily Targets")
            min_nutrients = recs['minimum_nutrients']
            cols = st.columns(len(min_nutrients))
            for col, (nutrient, value) in zip(cols, min_nutrients.items()):
                with col:
                    if nutrient == 'water':
                        display_value = format_volume(value, st.session_state.preferences["unit_system"])
                    else:
                        unit = 'g'
                        display_value = f"{value}{unit}"
                    st.metric(nutrient.title(), display_value)

        # Display adjustments if any
        if recs.get('adjustments'):
            st.subheader("Suggested Adjustments")
            for adj in recs['adjustments']:
                severity_color = {
                    'low': 'blue',
                    'medium': 'orange',
                    'high': 'red'
                }[adj.severity]
                st.markdown(f":{severity_color}[{adj.suggestion}]")

        if 'explanation' in recs:
            st.info(recs['explanation'])

def show_progress_tab():
    """Display progress charts and analysis"""
    st.header("Progress Analysis")

    if len(st.session_state.tracker.logs) == 0:
        st.info("Add some logs to see progress charts!")
        return

    unit_system = st.session_state.preferences["unit_system"]
    summary = st.session_state.tracker.get_progress_summary()

    # Progress charts
    metrics = st.multiselect(
        "Select metrics to display",
        ['weight', 'body_fat', 'calories', 'protein', 'carbs', 'fat'],
        default=['weight'],
        key="metric_select"
    )

    df = st.session_state.tracker.data_manager.to_dataframe()
    if not df.empty:
        # Convert weight values if using imperial
        if unit_system == 'imperial' and 'weight' in metrics:
            display_df = df.copy()
            display_df['weight'] = display_df['weight'].apply(kg_to_lbs)
            st.plotly_chart(create_metrics_chart(display_df, metrics), use_container_width=True)
        else:
            st.plotly_chart(create_metrics_chart(df, metrics), use_container_width=True)

    # Summary stats with unit conversion
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Overall Changes")
        if 'overall_changes' in summary and summary['overall_changes']:
            for metric, value in summary['overall_changes'].items():
                if value is not None:
                    if 'weight' in metric.lower() and unit_system == 'imperial':
                        display_value = kg_to_lbs(value)
                        unit = "lbs"
                    else:
                        display_value = value
                        unit = "kg" if 'weight' in metric.lower() else "%"
                    st.metric(
                        metric.replace('_', ' ').title(),
                        f"{display_value:.1f} {unit}"
                    )
        else:
            st.info("Need more data to calculate changes")

    with col2:
        st.subheader("Current Estimates")
        tdee = summary.get('current_tdee')
        if tdee:
            st.metric("Estimated TDEE", f"{tdee:.0f} kcal")
        else:
            st.info("Need more data to estimate TDEE (at least 7 days)")

        adherence = summary.get('adherence', {}).get('logging_adherence')
        if adherence is not None:
            st.metric("Adherence Rate", f"{adherence:.1%}")
        else:
            st.info("Need more data to calculate adherence")

    # Suggestions
    if summary.get('suggestions'):
        st.subheader("Suggestions")
        for suggestion in summary['suggestions']:
            st.info(suggestion, icon="ℹ️")

def show_data_tab():
    """Display data management options"""
    st.header("Data Management")

    tab1, tab2 = st.tabs(["Export Data", "Import Data"])

    with tab1:
        export_format = st.selectbox(
            "Export Format",
            ["CSV", "Excel", "JSON"],
            key="export_format"
        )

        if st.button("Export Data", key="btn_export"):
            try:
                filename = f"macro_tracker_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                result = st.session_state.tracker.export_data(
                    format=export_format.lower(),
                    filename=filename
                )
                st.success(result)
            except Exception as e:
                st.error(f"Export failed: {str(e)}")

    with tab2:
        uploaded_file = st.file_uploader(
            "Choose a file to import",
            type=['csv', 'xlsx', 'json'],
            key="file_uploader"
        )

        col1, col2 = st.columns(2)
        with col1:
            source = st.selectbox(
                "Data Source",
                ["General", "MyFitnessPal", "Custom"],
                key="import_source"
            )
        with col2:
            import_units = st.selectbox(
                "Input Units",
                ["metric", "imperial"],
                help="Select the unit system used in your import file",
                key="import_units"
            )

        if uploaded_file and st.button("Import Data", key="btn_import"):
            try:
                st.session_state.tracker.load_data(
                    uploaded_file,
                    source=source.lower(),
                    units=import_units
                )
                st.success("Data imported successfully!")
            except Exception as e:
                st.error(f"Import failed: {str(e)}")


def main():
    st.set_page_config(
        page_title="Macro Tracker",
        page_icon="🎯",
        layout="wide"
    )

    st.title("Macro Tracker")

    initialize_session_state()

    # Call show_settings_sidebar once and store the result
    diet_mode, macro_preset = show_settings_sidebar()

    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs([
        "Daily Log", "Recommendations", "Progress", "Data Management"
    ])

    with tab1:
        show_daily_log_tab()

    with tab2:
        show_recommendations_tab(diet_mode, macro_preset)

    with tab3:
        show_progress_tab()

    with tab4:
        show_data_tab()


if __name__ == "__main__":
    main()