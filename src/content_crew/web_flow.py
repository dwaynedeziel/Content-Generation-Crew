"""Web-compatible flow wrapper — runs ContentFlow phases as background tasks.

Supports multiple simultaneous pipeline runs, each identified by a UUID.
Replaces terminal input()/print() with API-driven state management and
streams log output via SSE queues.
"""

from __future__ import annotations

import csv
import os
import threading
import uuid
from datetime import datetime
from enum import Enum
from queue import Queue
from typing import Any

from pydantic import BaseModel, Field

from content_crew.models import (
    Article,
    ClientContext,
    ContentBrief,
    ContentFlowState,
    TopicMapEntry,
)


class RunPhase(str, Enum):
    SETUP = "setup"
    PHASE1_RUNNING = "phase1_running"
    PHASE1_REVIEW = "phase1_review"
    PHASE2_RUNNING = "phase2_running"
    PHASE2_REVIEW = "phase2_review"
    PHASE3_RUNNING = "phase3_running"
    COMPLETE = "complete"
    ERROR = "error"


class PipelineRun:
    """A single pipeline run with its own state, logs, and thread."""

    def __init__(self, run_id: str, client: ClientContext, seed_topic: str, output_dir: str):
        self.run_id = run_id
        self.state = ContentFlowState(
            client=client,
            seed_topic=seed_topic,
            output_dir=output_dir,
        )
        self.phase = RunPhase.SETUP
        self.log_queue: Queue[dict] = Queue()
        self.progress: dict[str, Any] = {
            "phase": 0,
            "total_phases": 3,
            "current_task": "",
            "percent": 0,
            "topics_total": 0,
            "topics_done": 0,
        }
        self.error: str | None = None
        self._thread: threading.Thread | None = None
        self.created_at = datetime.now().isoformat()

    def emit_log(self, source: str, message: str, level: str = "info"):
        """Push a log event to the SSE queue."""
        self.log_queue.put({
            "time": datetime.now().strftime("%H:%M:%S"),
            "source": source,
            "message": message,
            "level": level,
        })

    def to_summary(self) -> dict:
        """Return a JSON-serializable summary of the run."""
        return {
            "run_id": self.run_id,
            "client_name": self.state.client.client_name,
            "seed_topic": self.state.seed_topic,
            "phase": self.phase.value,
            "progress": self.progress,
            "created_at": self.created_at,
            "error": self.error,
            "topic_count": len(self.state.topic_entries),
            "brief_count": len(self.state.briefs),
            "article_count": len(self.state.articles),
        }


class RunManager:
    """Thread-safe manager for multiple simultaneous pipeline runs."""

    def __init__(self):
        self._runs: dict[str, PipelineRun] = {}
        self._lock = threading.Lock()

    def create_run(self, client: ClientContext, seed_topic: str) -> PipelineRun:
        """Create a new pipeline run."""
        run_id = str(uuid.uuid4())[:8]

        # Build output dir scoped to run
        project_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        output_dir = os.path.join(project_dir, "output", f"run-{run_id}")
        os.makedirs(os.path.join(output_dir, "topic_maps"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "briefs"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "articles"), exist_ok=True)

        run = PipelineRun(run_id, client, seed_topic, output_dir)

        with self._lock:
            self._runs[run_id] = run

        return run

    def get_run(self, run_id: str) -> PipelineRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self) -> list[dict]:
        with self._lock:
            return [r.to_summary() for r in self._runs.values()]

    def start_phase1(self, run: PipelineRun):
        """Start Phase 1 (Research) in a background thread."""
        run.phase = RunPhase.PHASE1_RUNNING
        run.progress["phase"] = 1
        run.progress["current_task"] = "SEO research & topic map generation"
        run.progress["percent"] = 5

        def _run_phase1():
            try:
                from content_crew.crews.research_crew.research_crew import ResearchCrew

                run.emit_log("System", "Phase 1 started: Research & Topic Map Generation")

                today = datetime.now().strftime("%Y-%m-%d")
                inputs = {
                    "seed_topic": run.state.seed_topic,
                    "industry": run.state.client.industry,
                    "client_name": run.state.client.client_name,
                    "business_summary": run.state.client.business_summary,
                    "output_dir": run.state.output_dir,
                    "date": today,
                }

                run.progress["percent"] = 10
                run.emit_log("Research Crew", "Starting competitor audit & keyword research...")

                result = ResearchCrew().crew().kickoff(inputs=inputs)

                run.state.topic_map_csv_path = os.path.join(
                    run.state.output_dir, "topic_maps",
                    f"{run.state.seed_topic} - {today}.csv"
                )
                run.state.topic_map_summary = result.raw if hasattr(result, "raw") else str(result)

                if os.path.exists(run.state.topic_map_csv_path):
                    _parse_topic_map(run)

                run.progress["percent"] = 100
                run.progress["current_task"] = "Topic map ready for review"
                run.progress["topics_total"] = len(run.state.topic_entries)
                run.phase = RunPhase.PHASE1_REVIEW
                run.emit_log("System", f"Phase 1 complete — {len(run.state.topic_entries)} topics generated", "success")

            except Exception as e:
                run.phase = RunPhase.ERROR
                run.error = str(e)
                run.emit_log("System", f"Phase 1 error: {e}", "error")

        run._thread = threading.Thread(target=_run_phase1, daemon=True)
        run._thread.start()

    def start_phase2(self, run: PipelineRun):
        """Start Phase 2 (Briefs) in a background thread."""
        run.phase = RunPhase.PHASE2_RUNNING
        run.progress["phase"] = 2
        run.progress["current_task"] = "Generating content briefs"
        run.progress["percent"] = 0
        run.progress["topics_done"] = 0

        def _run_phase2():
            try:
                from content_crew.crews.brief_crew.brief_crew import BriefCrew

                run.emit_log("System", "Phase 2 started: Content Brief Generation")

                today = datetime.now().strftime("%Y-%m-%d")
                sorted_topics = sorted(
                    run.state.topic_entries, key=lambda t: t.priority_score, reverse=True
                )
                total = len(sorted_topics)
                run.progress["topics_total"] = total

                for i, topic in enumerate(sorted_topics, 1):
                    run.emit_log("Brief Crew", f"[{i}/{total}] Creating brief: {topic.topic_name}")
                    run.progress["current_task"] = f"Brief {i}/{total}: {topic.topic_name}"

                    inputs = {
                        "topic_name": topic.topic_name,
                        "primary_keyword": topic.primary_keyword,
                        "secondary_keywords": topic.secondary_keywords,
                        "search_intent": topic.search_intent,
                        "content_type": topic.content_type,
                        "word_count_min": str(topic.word_count_min),
                        "word_count_max": str(topic.word_count_max),
                        "priority_score": str(topic.priority_score),
                        "competition_level": topic.competition_level,
                        "target_entities": topic.target_entities,
                        "questions_to_answer": topic.questions_to_answer,
                        "serp_features_opportunity": topic.serp_features_opportunity,
                        "internal_link_targets": topic.internal_link_targets,
                        "information_gain_opportunity": topic.information_gain_opportunity,
                        "rag_optimization_notes": topic.rag_optimization_notes,
                        "output_dir": run.state.output_dir,
                        "date": today,
                        "client_name": run.state.client.client_name,
                        "industry": run.state.client.industry,
                        "business_summary": run.state.client.business_summary,
                        "brand_voice": run.state.client.brand_voice,
                        "brand_tone": run.state.client.brand_tone,
                        "style_preferences": run.state.client.style_preferences,
                    }

                    BriefCrew().crew().kickoff(inputs=inputs)

                    brief = ContentBrief(
                        topic_name=topic.topic_name,
                        filename=f"{topic.topic_name} - {today}.md",
                        priority_score=topic.priority_score,
                        content_type=topic.content_type,
                        word_count_min=topic.word_count_min,
                        word_count_max=topic.word_count_max,
                    )
                    run.state.briefs.append(brief)
                    run.progress["topics_done"] = i
                    run.progress["percent"] = int((i / total) * 100)
                    run.emit_log("Brief Crew", f"✅ Brief done: {topic.topic_name}", "success")

                run.progress["percent"] = 100
                run.progress["current_task"] = "Briefs ready for review"
                run.phase = RunPhase.PHASE2_REVIEW
                run.emit_log("System", f"Phase 2 complete — {len(run.state.briefs)} briefs generated", "success")

            except Exception as e:
                run.phase = RunPhase.ERROR
                run.error = str(e)
                run.emit_log("System", f"Phase 2 error: {e}", "error")

        run._thread = threading.Thread(target=_run_phase2, daemon=True)
        run._thread.start()

    def start_phase3(self, run: PipelineRun):
        """Start Phase 3 (Production) in a background thread."""
        run.phase = RunPhase.PHASE3_RUNNING
        run.progress["phase"] = 3
        run.progress["current_task"] = "Writing articles"
        run.progress["percent"] = 0
        run.progress["topics_done"] = 0

        def _run_phase3():
            try:
                from content_crew.crews.production_crew.production_crew import ProductionCrew

                run.emit_log("System", "Phase 3 started: Content Production & QA")

                today = datetime.now().strftime("%Y-%m-%d")
                sorted_briefs = sorted(
                    run.state.briefs, key=lambda b: b.priority_score, reverse=True
                )
                total = len(sorted_briefs)
                run.progress["topics_total"] = total

                for i, brief in enumerate(sorted_briefs, 1):
                    run.emit_log("Production Crew", f"[{i}/{total}] Writing: {brief.topic_name}")
                    run.progress["current_task"] = f"Article {i}/{total}: {brief.topic_name}"

                    brief_path = os.path.join(run.state.output_dir, "briefs", brief.filename)
                    brief_content = ""
                    if os.path.exists(brief_path):
                        with open(brief_path, "r", encoding="utf-8") as f:
                            brief_content = f.read()
                    else:
                        brief_content = f"Brief for {brief.topic_name} (file not found)"

                    topic_entry = next(
                        (t for t in run.state.topic_entries if t.topic_name == brief.topic_name),
                        None,
                    )

                    inputs = {
                        "topic_name": brief.topic_name,
                        "primary_keyword": topic_entry.primary_keyword if topic_entry else brief.topic_name,
                        "secondary_keywords": topic_entry.secondary_keywords if topic_entry else "",
                        "content_type": brief.content_type,
                        "word_count_min": str(brief.word_count_min),
                        "word_count_max": str(brief.word_count_max),
                        "word_count_target": str((brief.word_count_min + brief.word_count_max) // 2),
                        "search_intent": topic_entry.search_intent if topic_entry else "informational",
                        "target_entities": topic_entry.target_entities if topic_entry else "",
                        "internal_link_targets": topic_entry.internal_link_targets if topic_entry else "",
                        "brief_content": brief_content,
                        "output_dir": run.state.output_dir,
                        "date": today,
                        "client_name": run.state.client.client_name,
                        "brand_voice": run.state.client.brand_voice,
                        "brand_tone": run.state.client.brand_tone,
                        "style_preferences": run.state.client.style_preferences,
                    }

                    max_attempts = 3
                    qa_passed = False
                    attempt = 1

                    for attempt in range(1, max_attempts + 1):
                        run.emit_log("Production Crew", f"  Attempt {attempt}/{max_attempts}...")
                        result = ProductionCrew().crew().kickoff(inputs=inputs)
                        result_text = result.raw if hasattr(result, "raw") else str(result)

                        if "QA Status: PASSED" in result_text or "PASSED" in result_text.upper():
                            qa_passed = True
                            break
                        elif attempt < max_attempts:
                            run.emit_log("QA Editor", f"  ⚠️ QA issues found, retrying...", "warning")
                            inputs["brief_content"] = (
                                brief_content + f"\n\n--- REVISION NOTES (Attempt {attempt}) ---\n"
                                f"The previous version had QA issues. Please fix:\n{result_text}"
                            )

                    article = Article(
                        topic_name=brief.topic_name,
                        filename=f"{brief.topic_name} - {today}.md",
                        qa_status="PASSED" if qa_passed else "FLAGGED",
                        qa_attempts=attempt,
                    )
                    run.state.articles.append(article)
                    run.progress["topics_done"] = i
                    run.progress["percent"] = int((i / total) * 100)

                    status_emoji = "✅" if qa_passed else "⚠️"
                    run.emit_log(
                        "Production Crew",
                        f"{status_emoji} {brief.topic_name} — {article.qa_status} (Attempts: {attempt})",
                        "success" if qa_passed else "warning",
                    )

                run.progress["percent"] = 100
                run.progress["current_task"] = "Production complete"
                run.phase = RunPhase.COMPLETE

                passed = sum(1 for a in run.state.articles if a.qa_status == "PASSED")
                flagged = sum(1 for a in run.state.articles if a.qa_status == "FLAGGED")
                run.emit_log(
                    "System",
                    f"🎉 Pipeline complete — {passed} passed, {flagged} flagged",
                    "success",
                )

            except Exception as e:
                run.phase = RunPhase.ERROR
                run.error = str(e)
                run.emit_log("System", f"Phase 3 error: {e}", "error")

        run._thread = threading.Thread(target=_run_phase3, daemon=True)
        run._thread.start()


def _parse_topic_map(run: PipelineRun) -> None:
    """Parse the topic map CSV into TopicMapEntry objects."""
    try:
        with open(run.state.topic_map_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            run.state.topic_entries = []
            for row in reader:
                entry = TopicMapEntry(
                    topic_level=row.get("topic_level", "supporting").strip(),
                    parent_cluster=row.get("parent_cluster", "").strip(),
                    topic_name=row.get("topic_name", "").strip(),
                    primary_keyword=row.get("primary_keyword", "").strip(),
                    secondary_keywords=row.get("secondary_keywords", "").strip(),
                    search_intent=row.get("search_intent", "informational").strip(),
                    content_type=row.get("content_type", "guide").strip(),
                    word_count_min=int(row.get("word_count_min", 1500)),
                    word_count_max=int(row.get("word_count_max", 2500)),
                    target_entities=row.get("target_entities", "").strip(),
                    questions_to_answer=row.get("questions_to_answer", "").strip(),
                    information_gain_opportunity=row.get("information_gain_opportunity", "").strip(),
                    rag_optimization_notes=row.get("rag_optimization_notes", "").strip(),
                    internal_link_targets=row.get("internal_link_targets", "").strip(),
                    priority_score=int(row.get("priority_score", 5)),
                    competition_level=row.get("competition_level", "medium").strip(),
                    serp_features_opportunity=row.get("serp_features_opportunity", "").strip(),
                )
                run.state.topic_entries.append(entry)
        run.emit_log("System", f"Parsed {len(run.state.topic_entries)} topics from CSV")
    except Exception as e:
        run.emit_log("System", f"Could not parse topic map CSV: {e}", "error")
