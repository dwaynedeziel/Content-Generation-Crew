"""Constants for the content creation system — banned phrases, CSV schema, SEO rules, QA checklist."""

# ---------------------------------------------------------------------------
# CSV Topic Map Schema
# ---------------------------------------------------------------------------
CSV_HEADERS = [
    "topic_level",
    "parent_cluster",
    "topic_name",
    "primary_keyword",
    "secondary_keywords",
    "search_intent",
    "content_type",
    "word_count_min",
    "word_count_max",
    "target_entities",
    "questions_to_answer",
    "information_gain_opportunity",
    "rag_optimization_notes",
    "internal_link_targets",
    "priority_score",
    "competition_level",
    "serp_features_opportunity",
]

# ---------------------------------------------------------------------------
# Banned AI Cliché Phrases — NEVER use in content
# ---------------------------------------------------------------------------
BANNED_PHRASES = [
    "In today's digital landscape",
    "game-changer",
    "unlock",
    "leverage",
    "dive in",
    "deep dive",
    "navigate",
    "elevate",
    "robust",
    "It's important to note",
    "It's worth noting",
    "In conclusion",
    "Without further ado",
    "At the end of the day",
    "seamless",
    "seamlessly",
    "cutting-edge",
    "revolutionary",
    "empower",
    "empowering",
    "holistic",
    "synergy",
]

# ---------------------------------------------------------------------------
# SEO Standards
# ---------------------------------------------------------------------------
SEO_STANDARDS = {
    "meta_title_max_chars": 60,
    "meta_title_keyword_within_chars": 30,
    "meta_description_max_chars": 155,
    "url_slug_min_words": 3,
    "url_slug_max_words": 6,
    "keyword_density_min": 0.005,
    "keyword_density_max": 0.015,
    "internal_links_min": 3,
    "internal_links_max": 5,
    "featured_snippet_min_words": 40,
    "featured_snippet_max_words": 60,
    "faq_answer_min_words": 40,
    "faq_answer_max_words": 60,
    "default_word_count_target": 2200,
}

# ---------------------------------------------------------------------------
# QA Checklist Items
# ---------------------------------------------------------------------------
QA_CHECKLIST = {
    "structure_and_intent": [
        "Search intent matches brief",
        "Inverted pyramid: key answer in first paragraph",
        "All H2 sections atomic and self-contained",
        "Key Takeaways present (5 items)",
        "FAQ section present (4-6 questions from brief)",
    ],
    "seo_and_technical": [
        "Meta title: present, <60 chars, has primary keyword",
        "Meta description: present, <155 chars, compelling, has keyword",
        "URL slug: present, clean, keyword-focused",
        "Primary keyword in H1, first paragraph, and 2+ H2 headings",
        "Secondary keywords distributed naturally",
        "Internal link placeholders for all brief targets",
        "Image alt text on all placeholders",
        "Word count within brief's min-max range",
    ],
    "optimization": [
        "Information gain element present (from brief)",
        "Comparison table (if content type warrants)",
        "FAQ answers 40-60 words, snippet-optimized",
        "Target entities mentioned and bolded first occurrence",
        "No banned AI cliché phrases",
    ],
}

# ---------------------------------------------------------------------------
# Search patterns used in Phase 1 research
# ---------------------------------------------------------------------------
RESEARCH_SEARCH_PATTERNS = [
    "{topic} best practices",
    "{topic} guide",
    "{topic} vs",
    "how to {topic}",
    "{topic} mistakes",
    "{topic} tools",
    "{topic} statistics",
    "{topic} tips for beginners",
    "{topic} trends 2026",
    "{topic} case studies",
]
