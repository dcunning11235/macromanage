import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from macro_tracker import MacroTracker
from base_types import UserStats, DailyLog, DietMode, ActivityLevel, TrainingLevel
import json


def initialize_session_state():
    """Initialize session state variables"""
    if 'tracker' not in st.session_state:
        st.session_state.tracker = MacroTracker()
    if 'current_stats' not in st.session_state:
        st.session_state.current_stats = None
    if 'show_export' not in st.session_state:
        st.session_state.show_export = False


def create_metrics_chart(df, metrics):
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

        # Basic Info
        weight = st.number_input("Current Weight (kg)", 40.0, 200.0, 80.0)
        body_fat = st.number_input("Body Fat %", 5.0, 50.0, 15.0)

        # Goals
        st.subheader("Goals")
        target_weight = st.number_input("Target Weight (kg)", 40.0, 200.0, 75.0)
        target_bf = st.number_input("Target Body Fat %", 5.0, 50.0, 12.0)

        # Additional Settings
        activity = st.selectbox(
            "Activity Level",
            options=[level.name for level in ActivityLevel],
            format_func=lambda x: x.replace('_', ' ').title()
        )

        training = st.selectbox(
            "Training Experience",
            options=[level.name for level in TrainingLevel],
            format_func=lambda x: x.replace('_', ' ').title()
        )

        diet_mode = st.selectbox(
            "Diet Mode",
            options=[mode.name for mode in DietMode],
            format_func=lambda x: x.replace('_', ' ').title()
        )

        # Optional Info
        with st.expander("Additional Information"):
            height = st.number_input("Height (cm)", 100.0, 250.0, 170.0)
            age = st.number_input("Age", 18, 100, 30)
            gender = st.selectbox("Gender", ["male", "female"])

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
        log_date = st.date_input("Date", datetime.now())
        log_weight = st.number_input("Weight (kg)", 0.0, 300.0,
                                     st.session_state.current_stats.weight)
        log_bf = st.number_input("Body Fat %", 0.0, 50.0,
                                 st.session_state.current_stats.body_fat)

    with col2:
        calories = st.number_input("Calories", 0, 10000, 2000)
        protein = st.number_input("Protein (g)", 0, 500, 150)
        carbs = st.number_input("Carbs (g)", 0, 1000, 200)
        fat = st.number_input("Fat (g)", 0, 200, 70)

    with col3:
        steps = st.number_input("Steps", 0, 100000, 0)
        water = st.number_input("Water (L)", 0.0, 10.0, 0.0)
        sleep = st.number_input("Sleep (hours)", 0.0, 24.0, 0.0)
        notes = st.text_area("Notes", "")

    if st.button("Add Log"):
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


def show_recommendations_tab():
    """Display recommendations"""
    st.header("Your Recommendations")

    if not st.session_state.current_stats:
        st.warning("Please set your stats in the sidebar first.")
        return

    diet_mode = show_settings_sidebar()
    recs = st.session_state.tracker.get_recommendations(st.session_state.current_stats, diet_mode)

    # Display main targets
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Target Calories", f"{recs['calories']} kcal")
    with col2:
        st.metric("Protein", f"{recs['macros']['protein']}g")
    with col3:
        st.metric("Carbs", f"{recs['macros']['carbs']}g")
    with col4:
        st.metric("Fat", f"{recs['macros']['fat']}g")

    # Display meal timing
    st.subheader("Meal Timing")
    meal_cols = st.columns(len(recs['meal_timing']))
    for i, (meal, cals) in enumerate(recs['meal_timing'].items()):
        with meal_cols[i]:
            st.metric(meal.replace('_', ' ').title(), f"{cals} kcal")

    # Display adjustments if any
    if recs['adjustments']:
        st.subheader("Suggested Adjustments")
        for adj in recs['adjustments']:
            severity_color = {
                'low': 'blue',
                'medium': 'orange',
                'high': 'red'
            }[adj.severity]
            st.markdown(f":{severity_color}[{adj.suggestion}]")

    st.info(recs['explanation'])


def show_progress_tab():
    """Display progress charts and analysis"""
    st.header("Progress Analysis")

    if len(st.session_state.tracker.logs) == 0:
        st.info("Add some logs to see progress charts!")
        return

    summary = st.session_state.tracker.get_progress_summary()

    # Progress charts
    metrics = st.multiselect(
        "Select metrics to display",
        ['weight', 'body_fat', 'calories', 'protein', 'carbs', 'fat'],
        default=['weight']
    )

    df = st.session_state.tracker.data_manager.to_dataframe()
    st.plotly_chart(create_metrics_chart(df, metrics), use_container_width=True)

    # Summary stats
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Overall Changes")
        for metric, value in summary['overall_changes'].items():
            st.metric(
                metric.replace('_', ' ').title(),
                f"{value:.1f}"
            )

    with col2:
        st.subheader("Current Estimates")
        st.metric("Estimated TDEE", f"{summary['current_tdee']:.0f} kcal")
        st.metric("Adherence Rate", f"{summary['adherence']['logging_adherence']:.1%}")

    # Suggestions
    if summary['suggestions']:
        st.subheader("Suggestions")
        for suggestion in summary['suggestions']:
            st.info(suggestion)


def show_data_tab():
    """Display data management options"""
    st.header("Data Management")

    tab1, tab2 = st.tabs(["Export Data", "Import Data"])

    with tab1:
        export_format = st.selectbox(
            "Export Format",
            ["CSV", "Excel", "JSON"]
        )

        if st.button("Export Data"):
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
                                         type=['csv', 'xlsx', 'json'])
        source = st.selectbox(
            "Data Source",
            ["General", "MyFitnessPal", "Custom"]
        )

        if uploaded_file and st.button("Import Data"):
            try:
                st.session_state.tracker.load_data(uploaded_file, source.lower())
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