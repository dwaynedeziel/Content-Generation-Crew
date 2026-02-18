"""ContentFlow — Main orchestrator using CrewAI Flows.

Manages the 3-phase content creation pipeline with human checkpoints
between each phase. Uses structured Pydantic state to share data
across phases.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from io import StringIO

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

from content_crew.models import (
    Article,
    ClientContext,
    ContentBrief,
    ContentFlowState,
    TopicMapEntry,
)
from content_crew.crews.research_crew.research_crew import ResearchCrew
from content_crew.crews.brief_crew.brief_crew import BriefCrew
from content_crew.crews.production_crew.production_crew import ProductionCrew


class ContentFlow(Flow[ContentFlowState]):
    """Orchestrates the 3-phase content creation pipeline.

    Phase 1: Research & Topic Map Generation
    Phase 2: Content Brief Generation
    Phase 3: Content Production & QA

    Human checkpoints exist between every phase.
    """

    @start()
    def collect_client_context(self) -> str:
        """Collect client context from the user interactively."""
        print("\n" + "=" * 60)
        print("  CONTENT CREATION PIPELINE — Phase 0: Client Context")
        print("=" * 60)
        print("\nBefore we begin, I need some information about your client.\n")

        self.state.client.client_name = input("Client name: ").strip()
        self.state.client.business_summary = input(
            "Business summary (what they do, who they serve): "
        ).strip()
        self.state.client.brand_voice = input(
            "Brand voice (e.g., authoritative, friendly, technical): "
        ).strip()
        self.state.client.brand_tone = input(
            "Brand tone (e.g., professional, conversational, encouraging): "
        ).strip()
        self.state.client.style_preferences = input(
            "Style preferences (e.g., data-driven, storytelling, concise): "
        ).strip()
        self.state.client.industry = input("Industry: ").strip()
        self.state.client.competitive_landscape = input(
            "Competitive landscape (key competitors, optional): "
        ).strip()

        self.state.seed_topic = input("\nSeed topic for the content strategy: ").strip()

        # Set up output directory
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.state.output_dir = os.path.join(project_dir, "output")
        os.makedirs(os.path.join(self.state.output_dir, "topic_maps"), exist_ok=True)
        os.makedirs(os.path.join(self.state.output_dir, "briefs"), exist_ok=True)
        os.makedirs(os.path.join(self.state.output_dir, "articles"), exist_ok=True)

        print(f"\n✅ Client context saved for: {self.state.client.client_name}")
        print(f"📋 Seed topic: {self.state.seed_topic}")
        print(f"📁 Output directory: {self.state.output_dir}")

        return "client_context_collected"

    @listen(collect_client_context)
    def run_research_phase(self, _) -> str:
        """Phase 1: Run the Research Crew to generate a topic map."""
        print("\n" + "=" * 60)
        print("  PHASE 1: Research & Topic Map Generation")
        print("=" * 60)
        self.state.current_phase = 1

        today = datetime.now().strftime("%Y-%m-%d")

        inputs = {
            "seed_topic": self.state.seed_topic,
            "industry": self.state.client.industry,
            "client_name": self.state.client.client_name,
            "business_summary": self.state.client.business_summary,
            "output_dir": self.state.output_dir,
            "date": today,
        }

        result = ResearchCrew().crew().kickoff(inputs=inputs)

        # Store the topic map path
        self.state.topic_map_csv_path = os.path.join(
            self.state.output_dir, "topic_maps", f"{self.state.seed_topic} - {today}.csv"
        )
        self.state.topic_map_summary = result.raw if hasattr(result, "raw") else str(result)

        # Try to parse the CSV if it was written
        if os.path.exists(self.state.topic_map_csv_path):
            self._parse_topic_map()

        return "phase_1_complete"

    @listen(run_research_phase)
    def checkpoint_phase_1(self, _) -> str:
        """Human checkpoint after Phase 1."""
        print("\n" + "=" * 60)
        print("  ✅ PHASE 1 COMPLETE — Topic Map Generated")
        print("=" * 60)

        if self.state.topic_map_csv_path and os.path.exists(self.state.topic_map_csv_path):
            print(f"\n📄 Topic map saved to: {self.state.topic_map_csv_path}")

        print(f"\n📊 Summary:\n{self.state.topic_map_summary}")

        if self.state.topic_entries:
            pillars = sum(1 for t in self.state.topic_entries if t.topic_level == "pillar")
            clusters = sum(1 for t in self.state.topic_entries if t.topic_level == "cluster")
            supporting = sum(1 for t in self.state.topic_entries if t.topic_level == "supporting")
            print(f"\n   Pillars: {pillars} | Clusters: {clusters} | Supporting: {supporting}")
            print(f"   Total topics: {len(self.state.topic_entries)}")

        print("\n" + "-" * 60)
        response = input(
            "\nReady for Phase 2 (Content Briefs)? Or would you like to edit anything first?\n"
            "Type 'proceed' to continue, or describe what you'd like to change: "
        ).strip().lower()

        if response != "proceed":
            print(f"\n📝 Noted: {response}")
            print("Please make your edits to the CSV and type 'proceed' when ready.")
            while True:
                response = input("\nType 'proceed' when ready to continue: ").strip().lower()
                if response == "proceed":
                    break
                print(f"📝 Noted: {response}")

            # Re-parse in case the CSV was edited
            if os.path.exists(self.state.topic_map_csv_path):
                self._parse_topic_map()

        return "phase_1_approved"

    @listen(checkpoint_phase_1)
    def run_brief_phase(self, _) -> str:
        """Phase 2: Run the Brief Crew for each topic in the map."""
        print("\n" + "=" * 60)
        print("  PHASE 2: Content Brief Generation")
        print("=" * 60)
        self.state.current_phase = 2

        today = datetime.now().strftime("%Y-%m-%d")

        if not self.state.topic_entries:
            print("⚠️  No topic entries found. Attempting to parse topic map CSV...")
            self._parse_topic_map()

        if not self.state.topic_entries:
            print("❌ No topics found. Cannot generate briefs.")
            return "phase_2_failed"

        # Sort by priority (highest first)
        sorted_topics = sorted(
            self.state.topic_entries, key=lambda t: t.priority_score, reverse=True
        )

        print(f"\n📝 Generating briefs for {len(sorted_topics)} topics...\n")

        for i, topic in enumerate(sorted_topics, 1):
            print(f"\n--- Brief {i}/{len(sorted_topics)}: {topic.topic_name} ---")

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
                "output_dir": self.state.output_dir,
                "date": today,
                # Client context
                "client_name": self.state.client.client_name,
                "industry": self.state.client.industry,
                "business_summary": self.state.client.business_summary,
                "brand_voice": self.state.client.brand_voice,
                "brand_tone": self.state.client.brand_tone,
                "style_preferences": self.state.client.style_preferences,
            }

            result = BriefCrew().crew().kickoff(inputs=inputs)

            brief = ContentBrief(
                topic_name=topic.topic_name,
                filename=f"{topic.topic_name} - {today}.md",
                priority_score=topic.priority_score,
                content_type=topic.content_type,
                word_count_min=topic.word_count_min,
                word_count_max=topic.word_count_max,
            )
            self.state.briefs.append(brief)
            print(f"   ✅ Brief generated for: {topic.topic_name}")

        # Generate brief index
        self._generate_brief_index(today)

        return "phase_2_complete"

    @listen(run_brief_phase)
    def checkpoint_phase_2(self, _) -> str:
        """Human checkpoint after Phase 2."""
        print("\n" + "=" * 60)
        print("  ✅ PHASE 2 COMPLETE — Content Briefs Generated")
        print("=" * 60)

        print(f"\n📄 Briefs generated: {len(self.state.briefs)}")
        if self.state.brief_index_path:
            print(f"📋 Brief index: {self.state.brief_index_path}")

        print("\nBriefs by priority:")
        for brief in sorted(self.state.briefs, key=lambda b: b.priority_score, reverse=True):
            print(
                f"   [{brief.priority_score}] {brief.topic_name} "
                f"({brief.content_type}, {brief.word_count_min}-{brief.word_count_max} words)"
            )

        print("\n" + "-" * 60)
        response = input(
            "\nReady for Phase 3 (Content Production)? Or would you like to edit anything first?\n"
            "Type 'proceed' to continue, or describe what you'd like to change: "
        ).strip().lower()

        if response != "proceed":
            print(f"\n📝 Noted: {response}")
            print("Please make your edits and type 'proceed' when ready.")
            while True:
                response = input("\nType 'proceed' when ready to continue: ").strip().lower()
                if response == "proceed":
                    break
                print(f"📝 Noted: {response}")

        return "phase_2_approved"

    @listen(checkpoint_phase_2)
    def run_production_phase(self, _) -> str:
        """Phase 3: Run the Production Crew for each approved brief."""
        print("\n" + "=" * 60)
        print("  PHASE 3: Content Production & QA")
        print("=" * 60)
        self.state.current_phase = 3

        today = datetime.now().strftime("%Y-%m-%d")

        # Sort briefs by priority
        sorted_briefs = sorted(self.state.briefs, key=lambda b: b.priority_score, reverse=True)

        print(f"\n✍️  Writing articles for {len(sorted_briefs)} topics...\n")

        for i, brief in enumerate(sorted_briefs, 1):
            print(f"\n--- Article {i}/{len(sorted_briefs)}: {brief.topic_name} ---")

            # Read the brief content
            brief_path = os.path.join(self.state.output_dir, "briefs", brief.filename)
            brief_content = ""
            if os.path.exists(brief_path):
                with open(brief_path, "r", encoding="utf-8") as f:
                    brief_content = f.read()
            else:
                print(f"   ⚠️ Brief file not found: {brief_path}")
                brief_content = f"Brief for {brief.topic_name} (file not found, use topic data)"

            # Find the matching topic entry for additional data
            topic_entry = next(
                (t for t in self.state.topic_entries if t.topic_name == brief.topic_name),
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
                "output_dir": self.state.output_dir,
                "date": today,
                # Client context
                "client_name": self.state.client.client_name,
                "brand_voice": self.state.client.brand_voice,
                "brand_tone": self.state.client.brand_tone,
                "style_preferences": self.state.client.style_preferences,
            }

            # Run production crew with QA loop
            max_attempts = 3
            qa_passed = False

            for attempt in range(1, max_attempts + 1):
                print(f"   Attempt {attempt}/{max_attempts}...")
                result = ProductionCrew().crew().kickoff(inputs=inputs)
                result_text = result.raw if hasattr(result, "raw") else str(result)

                # Check if QA passed
                if "QA Status: PASSED" in result_text or "PASSED" in result_text.upper():
                    qa_passed = True
                    break
                elif attempt < max_attempts:
                    print(f"   ⚠️ QA issues found. Retrying ({attempt}/{max_attempts})...")
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
            self.state.articles.append(article)

            status = "✅" if qa_passed else "⚠️ FLAGGED"
            print(f"   {status} Article complete: {brief.topic_name} (Attempts: {attempt})")

        # Generate production index
        self._generate_production_index(today)

        return "phase_3_complete"

    @listen(run_production_phase)
    def finalize(self, _) -> str:
        """Final summary and session conclusion."""
        print("\n" + "=" * 60)
        print("  🎉 CONTENT PRODUCTION COMPLETE")
        print("=" * 60)

        total = len(self.state.articles)
        passed = sum(1 for a in self.state.articles if a.qa_status == "PASSED")
        flagged = sum(1 for a in self.state.articles if a.qa_status == "FLAGGED")

        print(f"\n📊 Production Summary:")
        print(f"   Total articles: {total}")
        print(f"   ✅ QA Passed: {passed}")
        print(f"   ⚠️ Flagged: {flagged}")

        if flagged > 0:
            print(f"\n⚠️  Flagged articles requiring review:")
            for article in self.state.articles:
                if article.qa_status == "FLAGGED":
                    print(f"   - {article.topic_name} (Attempts: {article.qa_attempts})")

        print(f"\n📁 All deliverables saved to: {self.state.output_dir}")
        print(f"   📄 Topic Map: {self.state.topic_map_csv_path}")
        print(f"   📋 Brief Index: {self.state.brief_index_path}")
        print(f"   📋 Production Index: {self.state.production_index_path}")

        print("\n" + "-" * 60)
        print("Options:")
        print("  1. Start a new topic map")
        print("  2. Revise flagged articles")
        print("  3. End session")

        return "session_complete"

    # -----------------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------------

    def _parse_topic_map(self) -> None:
        """Parse the topic map CSV into TopicMapEntry objects."""
        try:
            with open(self.state.topic_map_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.state.topic_entries = []
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
                    self.state.topic_entries.append(entry)
            print(f"   📊 Parsed {len(self.state.topic_entries)} topics from CSV.")
        except Exception as e:
            print(f"   ⚠️ Could not parse topic map CSV: {e}")

    def _generate_brief_index(self, date: str) -> None:
        """Generate a markdown index of all briefs."""
        index_path = os.path.join(self.state.output_dir, "briefs", f"Brief Index - {date}.md")
        lines = [
            f"# Content Brief Index — {self.state.client.client_name}",
            f"\nGenerated: {date}",
            f"Seed Topic: {self.state.seed_topic}",
            f"\n| # | Topic | Priority | Type | Word Count |",
            "|---|-------|----------|------|------------|",
        ]
        for i, brief in enumerate(
            sorted(self.state.briefs, key=lambda b: b.priority_score, reverse=True), 1
        ):
            lines.append(
                f"| {i} | {brief.topic_name} | {brief.priority_score} | "
                f"{brief.content_type} | {brief.word_count_min}-{brief.word_count_max} |"
            )

        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.state.brief_index_path = index_path
        print(f"\n📋 Brief index saved to: {index_path}")

    def _generate_production_index(self, date: str) -> None:
        """Generate a markdown index of all produced articles."""
        index_path = os.path.join(
            self.state.output_dir, "articles", f"Production Index - {date}.md"
        )
        lines = [
            f"# Production Index — {self.state.client.client_name}",
            f"\nGenerated: {date}",
            f"Seed Topic: {self.state.seed_topic}",
            f"\n| # | Topic | QA Status | Attempts | Flagged Items |",
            "|---|-------|-----------|----------|---------------|",
        ]
        for i, article in enumerate(self.state.articles, 1):
            flagged = ", ".join(article.flagged_items) if article.flagged_items else "—"
            lines.append(
                f"| {i} | {article.topic_name} | {article.qa_status} | "
                f"{article.qa_attempts}/3 | {flagged} |"
            )

        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.state.production_index_path = index_path
        print(f"\n📋 Production index saved to: {index_path}")
