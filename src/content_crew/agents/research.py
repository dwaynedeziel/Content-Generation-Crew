"""Research agent — replaces ResearchCrew.

Two-step process using Gemini:
1. SEO Research Strategist — searches web, builds research report
2. Topic Map Architect — organizes research into CSV topic map
"""

from __future__ import annotations

from content_crew.gemini_client import chat
from content_crew.tools.serper_search import serper_search
from content_crew.tools.csv_writer_tool import csv_writer

# ── Gemini function declarations for tool calling ──────────────────────

SEARCH_TOOL_DECL = {
    "function_declarations": [{
        "name": "serper_search",
        "description": "Search the web using Google. Returns organic results, People Also Ask, and related searches.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The search query string",
                }
            },
            "required": ["query"],
        },
    }]
}

CSV_TOOL_DECL = {
    "function_declarations": [{
        "name": "csv_writer",
        "description": "Write CSV content to a file. Creates directories if needed.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "csv_content": {
                    "type": "STRING",
                    "description": "Full CSV string with header row and data rows",
                },
                "output_path": {
                    "type": "STRING",
                    "description": "Absolute file path for the CSV file",
                },
            },
            "required": ["csv_content", "output_path"],
        },
    }]
}

SEARCH_AND_CSV_DECL = {
    "function_declarations": [
        SEARCH_TOOL_DECL["function_declarations"][0],
        CSV_TOOL_DECL["function_declarations"][0],
    ]
}


# ── Agent prompts (preserved from YAML configs) ───────────────────────

SEO_STRATEGIST_SYSTEM = """You are a Senior SEO Research Strategist with 15+ years of experience analyzing search landscapes.
You've helped hundreds of businesses dominate their niches through data-driven keyword research and competitor analysis.
You never fabricate data — every insight must come from actual web search results.
You excel at identifying content gaps that competitors miss and spotting SERP feature opportunities (featured snippets, People Also Ask, knowledge panels).
Your research is thorough, methodical, and always grounded in real search data.
You have access to a web search tool — use it extensively."""

TOPIC_MAP_ARCHITECT_SYSTEM = """You are a Content Topic Map Architect who specializes in building topic cluster architectures that dominate search results.
You understand how pillar pages, cluster content, and supporting articles work together to build topical authority.
You think in hierarchies and always create perfectly structured topic maps.
Your CSV outputs are always clean, properly formatted, and ready for production use.
You target 1-3 pillar topics, 5-8 clusters per pillar, and supporting topics to fill gaps.
You never create more than 20 topics to keep the map focused and achievable.
You have access to a csv_writer tool and a web search tool."""


def run_research(
    seed_topic: str,
    industry: str,
    client_name: str,
    business_summary: str,
    output_dir: str,
    date: str,
    on_log: callable = None,
) -> str:
    """Run the full research pipeline: web research → topic map CSV.

    Args:
        seed_topic: The main topic to research.
        industry: Client industry.
        client_name: Client name.
        business_summary: Client business description.
        output_dir: Output directory for files.
        date: Today's date string.
        on_log: Optional callback(source, message) for logging.

    Returns:
        Summary report from the topic map architect.
    """
    log = on_log or (lambda s, m: None)

    # ── Step 1: SEO Research ──────────────────────────────────────
    log("Research Agent", "Starting competitor audit & keyword research...")

    research_task = f"""Conduct comprehensive SEO research for the topic "{seed_topic}" in the {industry} industry.

Perform web searches for EACH of these patterns:
- "{seed_topic} best practices"
- "{seed_topic} guide"
- "{seed_topic} vs"
- "how to {seed_topic}"
- "{seed_topic} mistakes"
- "{seed_topic} tools"
- "{seed_topic} statistics"
- "{seed_topic} tips for beginners"
- Long-tail keyword variations
- Question-based queries (how, what, why)
- "{seed_topic} trends 2026"

For each search, document:
1. Top 3-5 ranking pages (title, URL, what they cover)
2. Content gaps — topics competitors miss or cover poorly
3. SERP features present (featured snippets, People Also Ask)
4. Content types that rank well

Also conduct deeper keyword research:
- Commercial intent queries ("best {seed_topic}", "{seed_topic} services")
- Comparison queries ("{seed_topic} vs X")
- "{seed_topic} case studies"

Produce a comprehensive research report with all findings."""

    tools = {"serper_search": serper_search}
    research_report = chat(
        system_prompt=SEO_STRATEGIST_SYSTEM,
        user_prompt=research_task,
        tools=tools,
        tool_declarations=[SEARCH_TOOL_DECL],
        temperature=0.4,
    )

    log("Research Agent", f"Research complete — {len(research_report)} chars of findings")

    # ── Step 2: Topic Map Generation ─────────────────────────────
    log("Topic Map Agent", "Building topic map from research data...")

    csv_path = f"{output_dir}/topic_maps/{seed_topic} - {date}.csv"

    topic_map_task = f"""Using this SEO research data, build a complete topic map for "{seed_topic}".

RESEARCH DATA:
{research_report}

Structure requirements:
- 1-3 Pillar topics (comprehensive, high-level guides)
- 5-8 Cluster topics per pillar (focused subtopics)
- Supporting topics to fill remaining gaps
- Target 15-20 TOTAL topics

For EACH topic, determine ALL of these fields:
- topic_level: pillar, cluster, or supporting
- parent_cluster: which pillar/cluster this belongs to (empty for pillars)
- topic_name: descriptive name
- primary_keyword: main target keyword
- secondary_keywords: pipe-separated list of 3-5 secondary keywords
- search_intent: informational, commercial, transactional, or navigational
- content_type: guide, listicle, how-to, comparison, case-study, pillar-page, FAQ, or tutorial
- word_count_min: minimum word count
- word_count_max: maximum word count
- target_entities: pipe-separated list of entities/brands/concepts to mention
- questions_to_answer: pipe-separated list of 3-5 questions
- information_gain_opportunity: what unique angle this piece can offer
- rag_optimization_notes: how to structure for AI extraction
- internal_link_targets: pipe-separated topic names from THIS map to link
- priority_score: 1-10 (10 = highest priority)
- competition_level: low, medium, or high
- serp_features_opportunity: pipe-separated (featured-snippet, people-also-ask, knowledge-panel)

Generate the complete CSV and use the csv_writer tool to save it to: {csv_path}

Sort: pillar topics first, then by priority_score descending.

Client context:
- Client: {client_name}
- Industry: {industry}
- Business: {business_summary}

After writing the CSV, provide a summary report with:
- Total topic count by level
- Top 5 priority topics
- Intent distribution
- Competition spread"""

    tools = {
        "serper_search": serper_search,
        "csv_writer": csv_writer,
    }
    summary = chat(
        system_prompt=TOPIC_MAP_ARCHITECT_SYSTEM,
        user_prompt=topic_map_task,
        tools=tools,
        tool_declarations=[SEARCH_AND_CSV_DECL],
        temperature=0.3,
    )

    log("Topic Map Agent", "Topic map generated and saved to CSV")
    return summary
