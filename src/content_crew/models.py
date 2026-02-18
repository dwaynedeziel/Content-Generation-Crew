"""Pydantic models for the content creation flow state and data structures."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ClientContext(BaseModel):
    """Client information gathered at the start of the workflow."""

    client_name: str = ""
    business_summary: str = ""
    brand_voice: str = ""
    brand_tone: str = ""
    style_preferences: str = ""
    industry: str = ""
    competitive_landscape: str = ""


class TopicMapEntry(BaseModel):
    """A single row in the topic map CSV."""

    topic_level: str = Field(description="pillar, cluster, or supporting")
    parent_cluster: str = ""
    topic_name: str = ""
    primary_keyword: str = ""
    secondary_keywords: str = Field(default="", description="Pipe-separated")
    search_intent: str = Field(
        default="informational",
        description="informational, commercial, transactional, or navigational",
    )
    content_type: str = Field(
        default="guide",
        description="guide, listicle, how-to, comparison, case-study, pillar-page, FAQ, tutorial",
    )
    word_count_min: int = 1500
    word_count_max: int = 2500
    target_entities: str = Field(default="", description="Pipe-separated")
    questions_to_answer: str = Field(default="", description="Pipe-separated")
    information_gain_opportunity: str = ""
    rag_optimization_notes: str = ""
    internal_link_targets: str = Field(default="", description="Pipe-separated topic names")
    priority_score: int = Field(default=5, ge=1, le=10)
    competition_level: str = Field(default="medium", description="low, medium, or high")
    serp_features_opportunity: str = Field(default="", description="Pipe-separated")


class ContentBrief(BaseModel):
    """Metadata for a generated content brief."""

    topic_name: str = ""
    filename: str = ""
    priority_score: int = 5
    content_type: str = ""
    word_count_min: int = 1500
    word_count_max: int = 2500


class Article(BaseModel):
    """Metadata for a generated article."""

    topic_name: str = ""
    filename: str = ""
    word_count: int = 0
    qa_status: str = "pending"
    qa_attempts: int = 0
    flagged_items: list[str] = Field(default_factory=list)


class ContentFlowState(BaseModel):
    """Structured state for the ContentFlow orchestrator."""

    # Client context
    client: ClientContext = Field(default_factory=ClientContext)

    # Phase tracking
    current_phase: int = 0
    seed_topic: str = ""

    # Phase 1 outputs
    topic_map_csv_path: str = ""
    topic_map_summary: str = ""
    topic_entries: list[TopicMapEntry] = Field(default_factory=list)

    # Phase 2 outputs
    briefs: list[ContentBrief] = Field(default_factory=list)
    brief_index_path: str = ""

    # Phase 3 outputs
    articles: list[Article] = Field(default_factory=list)
    production_index_path: str = ""

    # Output directory
    output_dir: str = ""
