import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from macro_tracker import MacroTracker
from models import UserStats, DailyLog, DietMode


def main():
    st.title("Macro Tracker")

    # Initialize tracker in session state
    if 'tracker' not in st.session_state:
        st.session_state.tracker = MacroTracker()

    # Sidebar for user stats
    with st.sidebar:
        st.header("Your Stats")
        weight = st.number_input("Current Weight (kg)", 40.0, 200.0, 80.0)
        body_fat = st.number_input("Body Fat %", 5.0, 50.0, 15.0)
        target_weight = st.number_input("Target Weight (kg)", 40.0, 200.0, 75.0)
        target_bf = st.number_input("Target Body Fat %", 5.0, 50.0, 12.0)

        mode = st.selectbox("Diet Mode",
                            ["STANDARD_CUT", "AGGRESSIVE_CUT", "MAINTENANCE", "LEAN_BULK"])

    # Main area tabs
    tab1, tab2, tab3 = st.tabs(["Daily Log", "Recommendations", "Progress"])

    # Daily Log Tab
    with tab1:
        st.header("Log Daily Progress")
        col1, col2, col3 = st.columns(3)

        with col1:
            log_weight = st.number_input("Weight (kg)", 40.0, 200.0, weight)
            log_bf = st.number_input("Body Fat %", 5.0, 50.0, body_fat)

        with col2:
            calories = st.number_input("Calories", 0, 10000, 2000)
            protein = st.number_input("Protein (g)", 0, 500, 150)

        with col3:
            carbs = st.number_input("Carbs (g)", 0, 500, 200)
            fat = st.number_input("Fat (g)", 0, 200, 70)

        if st.button("Add Log"):
            log = DailyLog(
                date=datetime.now(),
                weight=log_weight,
                body_fat=log_bf,
                calories=calories,
                protein=protein,
                carbs=carbs,
                fat=fat
            )
            st.session_state.tracker.add_log(log)
            st.success("Log added successfully!")

    # Recommendations Tab
    with tab2:
        st.header("Your Recommendations")

        stats = UserStats(
            weight=weight,
            body_fat=body_fat,
            target_weight=target_weight,
            target_body_fat=target_bf
        )

        recs = st.session_state.tracker.get_recommendations(stats, getattr(DietMode, mode))

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Target Calories", f"{recs['calories']} kcal")
            st.metric("Protein", f"{recs['macros']['protein']}g")
        with col2:
            st.metric("Carbs", f"{recs['macros']['carbs']}g")
            st.metric("Fat", f"{recs['macros']['fat']}g")

        st.text(recs['explanation'])

    # Progress Tab
    with tab3:
        st.header("Progress Charts")

        if len(st.session_state.tracker.logs) > 0:
            # Create weight progress chart
            df = st.session_state.tracker.data_manager.to_dataframe()

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['date'], y=df['weight'],
                                     mode='lines+markers',
                                     name='Weight'))
            fig.update_layout(title='Weight Progress',
                              xaxis_title='Date',
                              yaxis_title='Weight (kg)')
            st.plotly_chart(fig)

            # Summary metrics
            summary = st.session_state.tracker.get_progress_summary()
            st.json(summary)
        else:
            st.info("Add some logs to see progress charts!")

        if st.button("Export Data"):
            st.session_state.tracker.export_data('csv')
            st.success("Data exported successfully!")


if __name__ == "__main__":
    main()