import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from macro_tracker import MacroTracker
from base_types import UserStats, DailyLog, DietMode, ActivityLevel, TrainingLevel
import json


def show_settings_sidebar():
    """Display settings sidebar"""
    with st.sidebar:
        st.header("User Settings")

        # Basic Info
        weight = st.number_input("Current Weight (kg)", 40.0, 200.0, 80.0, key="settings_weight")
        body_fat = st.number_input("Body Fat %", 5.0, 50.0, 15.0, key="settings_bf")

        # Goals
        st.subheader("Goals")
        target_weight = st.number_input("Target Weight (kg)", 40.0, 200.0, 75.0, key="settings_target_weight")
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

        diet_mode = st.selectbox(
            "Diet Mode",
            options=[mode.name for mode in DietMode],
            format_func=lambda x: x.replace('_', ' ').title(),
            key="settings_diet_mode"
        )

        # Optional Info
        with st.expander("Additional Information"):
            height = st.number_input("Height (cm)", 100.0, 250.0, 170.0, key="settings_height")
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

        return DietMode[diet_mode]


def show_daily_log_tab():
    """Display daily logging interface"""
    st.header("Daily Log")

    col1, col2, col3 = st.columns(3)

    with col1:
        log_date = st.date_input("Date", datetime.now(), key="log_date")
        log_weight = st.number_input("Weight (kg)", 0.0, 300.0,
                                     st.session_state.current_stats.weight,
                                     key="log_weight")
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


# [Previous functions for creating charts remain the same]

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
        uploaded_file = st.file_uploader("Choose a file to import",
                                         type=['csv', 'xlsx', 'json'],
                                         key="file_uploader")
        source = st.selectbox(
            "Data Source",
            ["General", "MyFitnessPal", "Custom"],
            key="import_source"
        )

        if uploaded_file and st.button("Import Data", key="btn_import"):
            try:
                st.session_state.tracker.load_data(uploaded_file, source.lower())
                st.success("Data imported successfully!")
            except Exception as e:
                st.error(f"Import failed: {str(e)}")


def initialize_session_state():
    """Initialize session state variables"""
    if 'tracker' not in st.session_state:
        st.session_state.tracker = MacroTracker()
    if 'current_stats' not in st.session_state:
        st.session_state.current_stats = None


def main():
    st.set_page_config(
        page_title="Macro Tracker",
        page_icon="🎯",
        layout="wide"
    )

    st.title("Macro Tracker")

    initialize_session_state()
    diet_mode = show_settings_sidebar()

    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs([
        "Daily Log", "Recommendations", "Progress", "Data Management"
    ])

    with tab1:
        show_daily_log_tab()

    with tab2:
        show_recommendations_tab()

    with tab3:
        show_progress_tab()

    with tab4:
        show_data_tab()


if __name__ == "__main__":
    main()