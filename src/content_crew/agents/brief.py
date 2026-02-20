"""Brief agent — replaces BriefCrew.

Single-step: Content Strategist generates a detailed content brief
for each topic, optionally researching competitors first.
"""

from __future__ import annotations

from content_crew.gemini_client import chat
from content_crew.tools.serper_search import serper_search
from content_crew.tools.file_writer_tool import file_writer

# ── Gemini function declarations ──────────────────────────────────────

BRIEF_TOOL_DECL = {
    "function_declarations": [
        {
            "name": "serper_search",
            "description": "Search the web using Google. Returns organic results, People Also Ask, and related searches.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "The search query string"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "file_writer",
            "description": "Write markdown content to a file.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "content": {"type": "STRING", "description": "Full markdown content"},
                    "output_path": {"type": "STRING", "description": "File path to write to"},
                },
                "required": ["content", "output_path"],
            },
        },
    ]
}


def run_brief(
    topic_name: str,
    primary_keyword: str,
    secondary_keywords: str,
    search_intent: str,
    content_type: str,
    word_count_min: int,
    word_count_max: int,
    target_entities: str,
    questions_to_answer: str,
    information_gain_opportunity: str,
    rag_optimization_notes: str,
    internal_link_targets: str,
    client_name: str,
    industry: str,
    business_summary: str,
    brand_voice: str,
    brand_tone: str,
    style_preferences: str,
    output_dir: str,
    date: str,
    on_log: callable = None,
) -> str:
    """Generate a content brief for a single topic.

    Returns:
        The brief content as a string.
    """
    log = on_log or (lambda s, m: None)
    log("Brief Agent", f"Creating brief for: {topic_name}")

    system_prompt = f"""You are an elite content strategist who has created briefs for Fortune 500 content teams.
Your briefs are legendary for being so detailed that writers can produce publication-ready content without any follow-up questions.
You understand SEO deeply — you know how to structure content for featured snippets, how to optimize for entity-based search,
and how to create information gain that competitors can't match.
You always research what's already ranking before creating an outline, so your briefs are informed by real competitive data.

Client context for this project:
- Client: {client_name}
- Industry: {industry}
- Business: {business_summary}
- Brand Voice: {brand_voice}
- Brand Tone: {brand_tone}
- Style: {style_preferences}

You have access to web search and file writing tools."""

    output_path = f"{output_dir}/briefs/{topic_name} - {date}.md"

    task_prompt = f"""Create a comprehensive content brief for this topic:

Topic: {topic_name}
Primary Keyword: {primary_keyword}
Secondary Keywords: {secondary_keywords}
Search Intent: {search_intent}
Content Type: {content_type}
Word Count: {word_count_min}-{word_count_max} words
Target Entities: {target_entities}
Questions to Answer: {questions_to_answer}
Information Gain Opportunity: {information_gain_opportunity}
RAG Optimization Notes: {rag_optimization_notes}
Internal Link Targets: {internal_link_targets}

STEPS:
1. Search for 2-3 top-ranking articles on this topic to understand what's already ranking
2. Create a detailed brief with ALL of these sections:

BRIEF STRUCTURE:
---
topic_name: "{topic_name}"
primary_keyword: "{primary_keyword}"
secondary_keywords: "{secondary_keywords}"
content_type: "{content_type}"
word_count_min: {word_count_min}
word_count_max: {word_count_max}
search_intent: "{search_intent}"
target_entities: "{target_entities}"
---

## Overview
[Brief overview paragraph]

## Competitor Analysis
[What the top-ranking articles cover and miss]

## Writing Style Guidance
[Voice, tone, style instructions based on client]

## Heading Hierarchy & Section Guide
### H1: [Title]
### H2: [Section] — [what to cover, key points, target length]
### H3: [Subsection if needed]
[Continue for all sections]

## Information Gain Strategy
[Unique angle this piece will take]

## RAG Optimization
[How to structure for AI extraction]

## Questions to Answer
[List each question with guidance on answer format]

## SEO Requirements
- Primary keyword placement: [guidance]
- Secondary keywords: [distribution plan]
- Internal links: [targets]
- Image placeholders: [suggestions]

3. Save the brief using the file_writer tool to: {output_path}"""

    tools = {
        "serper_search": serper_search,
        "file_writer": file_writer,
    }

    result = chat(
        system_prompt=system_prompt,
        user_prompt=task_prompt,
        tools=tools,
        tool_declarations=[BRIEF_TOOL_DECL],
        temperature=0.4,
    )

    log("Brief Agent", f"Brief complete for: {topic_name}")
    return result
