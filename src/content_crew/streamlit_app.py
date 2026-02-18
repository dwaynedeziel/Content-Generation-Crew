"""Streamlit dashboard for the Content Crew pipeline.

Launch via: python -m content_crew web
    or: streamlit run src/content_crew/streamlit_app.py
"""

from __future__ import annotations

import time

import streamlit as st

from content_crew.models import ClientContext
from content_crew.web_flow import RunManager, RunPhase

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Content Crew — AI Content Pipeline",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

if "run_manager" not in st.session_state:
    st.session_state.run_manager = RunManager()
if "current_run_id" not in st.session_state:
    st.session_state.current_run_id = None
if "logs" not in st.session_state:
    st.session_state.logs = []

rm: RunManager = st.session_state.run_manager


# ---------------------------------------------------------------------------
# Custom CSS for premium feel
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* Gradient header */
    .stApp > header { background: transparent; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        background: linear-gradient(135deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Phase indicator pills */
    .phase-pill {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 100px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .phase-active {
        background: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    .phase-complete {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .phase-waiting {
        background: rgba(148, 163, 184, 0.08);
        color: #64748b;
        border: 1px solid rgba(148, 163, 184, 0.15);
    }
    .phase-review {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }

    /* Log line styling */
    .log-line {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.78rem;
        padding: 2px 0;
        line-height: 1.7;
    }
    .log-time { color: #64748b; }
    .log-source { color: #818cf8; font-weight: 500; }
    .log-success { color: #34d399; }
    .log-warning { color: #fbbf24; }
    .log-error { color: #f87171; }

    /* Section dividers */
    .section-divider {
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        margin: 24px 0;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — Run management
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ◉ Content Crew")
    st.caption("AI-Powered Content Pipeline")
    st.markdown("---")

    if st.button("➕ New Pipeline Run", use_container_width=True, type="primary"):
        st.session_state.current_run_id = "new"
        st.session_state.logs = []
        st.rerun()

    st.markdown("---")
    st.markdown("##### Pipeline Runs")

    runs = rm.list_runs()
    if not runs:
        st.caption("No runs yet — start one above!")
    else:
        for run_info in runs:
            phase_label = run_info["phase"].replace("_", " ").title()
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(
                    f"**{run_info['client_name']}**\n\n{run_info['seed_topic'][:30]}...",
                    key=f"run_{run_info['run_id']}",
                    use_container_width=True,
                ):
                    st.session_state.current_run_id = run_info["run_id"]
                    st.session_state.logs = []
                    st.rerun()
            with col2:
                phase_cls = {
                    "phase1_running": "active", "phase2_running": "active",
                    "phase3_running": "active", "phase1_review": "review",
                    "phase2_review": "review", "complete": "complete",
                    "error": "active",
                }.get(run_info["phase"], "waiting")
                st.markdown(
                    f'<span class="phase-pill phase-{phase_cls}">{phase_label}</span>',
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Main content area
# ---------------------------------------------------------------------------

def render_setup_form():
    """Render the client context form for a new run."""
    st.markdown("## 📋 New Pipeline Run")
    st.caption("Fill in the client details to start the content generation pipeline.")

    with st.form("setup_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            client_name = st.text_input("Client Name *", placeholder="e.g. Acme Corp")
            industry = st.text_input("Industry *", placeholder="e.g. SaaS, Accounting, eCommerce")
            brand_voice = st.text_input("Brand Voice", placeholder="e.g. authoritative, friendly")
            competitive_landscape = st.text_input("Key Competitors", placeholder="Optional")

        with col2:
            seed_topic = st.text_input("Seed Topic *", placeholder="e.g. accounting services for small business")
            business_summary = st.text_area("Business Summary *", placeholder="What they do, who they serve...")
            brand_tone = st.text_input("Brand Tone", placeholder="e.g. professional, conversational")
            style_preferences = st.text_input("Style Preferences", placeholder="e.g. data-driven, concise")

        submitted = st.form_submit_button("🚀 Start Pipeline", type="primary", use_container_width=True)

        if submitted:
            if not client_name or not seed_topic or not industry:
                st.error("Please fill in all required fields (Client Name, Industry, Seed Topic)")
                return

            client = ClientContext(
                client_name=client_name,
                business_summary=business_summary,
                brand_voice=brand_voice,
                brand_tone=brand_tone,
                style_preferences=style_preferences,
                industry=industry,
                competitive_landscape=competitive_landscape,
            )

            run = rm.create_run(client, seed_topic)
            rm.start_phase1(run)

            st.session_state.current_run_id = run.run_id
            st.session_state.logs = []
            st.rerun()


def render_phase_tracker(phase: str):
    """Render the phase progress indicator."""
    phases = [
        ("1", "Research", ["phase1_running"]),
        ("✓", "Review 1", ["phase1_review"]),
        ("2", "Briefs", ["phase2_running"]),
        ("✓", "Review 2", ["phase2_review"]),
        ("3", "Production", ["phase3_running"]),
    ]

    cols = st.columns(len(phases))
    for i, (num, label, active_phases) in enumerate(phases):
        with cols[i]:
            # Determine state
            phase_order = [
                "phase1_running", "phase1_review", "phase2_running",
                "phase2_review", "phase3_running", "complete"
            ]
            current_idx = phase_order.index(phase) if phase in phase_order else -1
            # Each step maps to an index range
            step_idx = i  # 0-4
            # Map step to its "completion" threshold
            complete_after = [1, 2, 3, 4, 5]  # index in phase_order after which step is complete

            if phase == "complete":
                cls = "complete"
            elif phase in active_phases:
                cls = "active" if "review" not in phase else "review"
            elif current_idx > i:
                cls = "complete"
            else:
                cls = "waiting"

            st.markdown(
                f'<div style="text-align:center">'
                f'<span class="phase-pill phase-{cls}">{num}</span>'
                f'<br><small style="color:#94a3b8">{label}</small></div>',
                unsafe_allow_html=True,
            )


def drain_logs(run):
    """Drain new log events from the run's queue into session state."""
    while not run.log_queue.empty():
        try:
            event = run.log_queue.get_nowait()
            st.session_state.logs.append(event)
        except Exception:
            break


def render_logs():
    """Render the agent activity log."""
    st.markdown("#### 🔄 Agent Activity Log")

    log_container = st.container(height=250)
    with log_container:
        if not st.session_state.logs:
            st.caption("Waiting for events...")
        else:
            for entry in st.session_state.logs[-100:]:  # Show last 100
                level = entry.get("level", "info")
                color_cls = f"log-{level}" if level in ("success", "warning", "error") else ""
                st.markdown(
                    f'<div class="log-line {color_cls}">'
                    f'<span class="log-time">{entry.get("time", "")}</span> '
                    f'<span class="log-source">{entry.get("source", "")}</span> '
                    f'{entry.get("message", "")}</div>',
                    unsafe_allow_html=True,
                )


def render_run_detail(run_id: str):
    """Render the detail view for a specific pipeline run."""
    run = rm.get_run(run_id)
    if not run:
        st.error(f"Run {run_id} not found")
        return

    # Drain any new logs
    drain_logs(run)

    # Header
    st.markdown(f"## {run.state.client.client_name} — *{run.state.seed_topic}*")

    # Phase tracker
    if run.phase != RunPhase.ERROR:
        render_phase_tracker(run.phase.value)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Progress
    if run.phase not in (RunPhase.COMPLETE, RunPhase.ERROR):
        phase_names = {
            "phase1_running": "Phase 1: Research & Topic Map",
            "phase1_review": "✅ Phase 1 Complete — Review Topic Map",
            "phase2_running": "Phase 2: Content Brief Generation",
            "phase2_review": "✅ Phase 2 Complete — Review Briefs",
            "phase3_running": "Phase 3: Content Production & QA",
        }
        st.markdown(f"**{phase_names.get(run.phase.value, 'Working...')}**")
        st.progress(run.progress["percent"] / 100)
        st.caption(run.progress.get("current_task", ""))

    # Error state
    if run.phase == RunPhase.ERROR:
        st.error(f"❌ Pipeline Error: {run.error}")

    # Phase 1 Review — Topic Map
    if run.phase.value in ("phase1_review", "phase2_running", "phase2_review", "phase3_running", "complete"):
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("#### 📊 Topic Map")

        if run.state.topic_entries:
            import pandas as pd

            topic_data = []
            for t in run.state.topic_entries:
                topic_data.append({
                    "Topic": t.topic_name,
                    "Level": t.topic_level,
                    "Type": t.content_type,
                    "Primary Keyword": t.primary_keyword,
                    "Priority": t.priority_score,
                    "Competition": t.competition_level,
                    "Words": f"{t.word_count_min}-{t.word_count_max}",
                })

            df = pd.DataFrame(topic_data)

            if run.phase == RunPhase.PHASE1_REVIEW:
                # Editable table during review
                edited_df = st.data_editor(
                    df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"topic_editor_{run_id}",
                )

                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("✅ Approve & Continue", type="primary", key="approve_p1"):
                        rm.start_phase2(run)
                        st.rerun()
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)

    # Phase 2 Review — Briefs
    if run.phase.value in ("phase2_review", "phase3_running", "complete"):
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("#### 📝 Content Briefs")

        if run.state.briefs:
            for i, brief in enumerate(run.state.briefs):
                with st.expander(
                    f"**{brief.topic_name}** — {brief.content_type} | Priority: {brief.priority_score} | {brief.word_count_min}-{brief.word_count_max} words"
                ):
                    import os
                    brief_path = os.path.join(run.state.output_dir, "briefs", brief.filename)
                    if os.path.exists(brief_path):
                        with open(brief_path, "r", encoding="utf-8") as f:
                            st.markdown(f.read())
                    else:
                        st.caption(f"Brief file not found: {brief.filename}")

            if run.phase == RunPhase.PHASE2_REVIEW:
                if st.button("✅ Approve & Start Production", type="primary", key="approve_p2"):
                    rm.start_phase3(run)
                    st.rerun()

    # Phase 3 — Articles
    if run.phase.value in ("phase3_running", "complete") and run.state.articles:
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("#### 📄 Articles")

        for article in run.state.articles:
            status_icon = "✅" if article.qa_status == "PASSED" else "⚠️"
            with st.expander(
                f"{status_icon} **{article.topic_name}** — QA: {article.qa_status} | Attempts: {article.qa_attempts}/3"
            ):
                import os
                article_path = os.path.join(run.state.output_dir, "articles", article.filename)
                if os.path.exists(article_path):
                    with open(article_path, "r", encoding="utf-8") as f:
                        st.markdown(f.read())
                else:
                    st.caption(f"Article file not found: {article.filename}")

    # Completion summary
    if run.phase == RunPhase.COMPLETE:
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("#### 🎉 Pipeline Complete")

        c1, c2, c3, c4 = st.columns(4)
        passed = sum(1 for a in run.state.articles if a.qa_status == "PASSED")
        flagged = sum(1 for a in run.state.articles if a.qa_status == "FLAGGED")

        c1.metric("Topics", len(run.state.topic_entries))
        c2.metric("Briefs", len(run.state.briefs))
        c3.metric("Articles", len(run.state.articles))
        c4.metric("QA Passed", f"{passed}/{len(run.state.articles)}")

        st.info(f"📁 Output saved to: `{run.state.output_dir}`")

    # Agent Log
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    render_logs()

    # Auto-refresh while running
    if run.phase.value.endswith("_running"):
        time.sleep(2)
        st.rerun()


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

current = st.session_state.current_run_id

if current == "new":
    render_setup_form()
elif current:
    render_run_detail(current)
else:
    # Home view
    st.markdown("## ◉ Content Crew Dashboard")
    st.caption("AI-powered SEO content pipeline — powered by CrewAI")

    runs = rm.list_runs()
    if not runs:
        st.markdown("---")
        st.markdown(
            '<div style="text-align:center; padding:60px 0; color:#64748b;">'
            '<div style="font-size:2.5rem; margin-bottom:12px;">🚀</div>'
            '<p style="font-size:1rem;">No pipeline runs yet</p>'
            '<p style="font-size:0.85rem;">Click <b>New Pipeline Run</b> in the sidebar to get started</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("---")
        for run_info in runs:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{run_info['client_name']}** — {run_info['seed_topic']}")
                with col2:
                    st.caption(f"📊 {run_info['topic_count']} topics · 📝 {run_info['brief_count']} briefs · 📄 {run_info['article_count']} articles")
                with col3:
                    phase_label = run_info["phase"].replace("_", " ").title()
                    st.caption(phase_label)
