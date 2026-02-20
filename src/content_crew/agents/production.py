"""Production agent — replaces ProductionCrew.

Two-step process for each article:
1. Content Writer — writes the article from the brief
2. QA Editor — runs QA checklist, appends report, writes file
"""

from __future__ import annotations

from content_crew.gemini_client import chat
from content_crew.tools.file_writer_tool import file_writer
from content_crew.tools.banned_phrase_checker import banned_phrase_checker

# ── Gemini function declarations ──────────────────────────────────────

WRITER_TOOL_DECL = {
    "function_declarations": [{
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
    }]
}

QA_TOOL_DECL = {
    "function_declarations": [
        {
            "name": "banned_phrase_checker",
            "description": "Scan article content for banned AI cliché phrases. Returns PASSED or FAILED with violations.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "content": {"type": "STRING", "description": "Article content to scan"},
                },
                "required": ["content"],
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


# ── Agent system prompts ──────────────────────────────────────────────

WRITER_SYSTEM = """You are a world-class SEO content writer who has published over 1,000 articles that rank on the first page of Google.
You write in a natural, engaging style that avoids all AI clichés.
You NEVER use these banned phrases: "In today's digital landscape," "game-changer," "unlock," "leverage," "dive in," "deep dive,"
"navigate," "elevate," "robust," "It's important to note," "It's worth noting," "In conclusion," "Without further ado,"
"At the end of the day," "seamless," "seamlessly," "cutting-edge," "revolutionary," "empower," "empowering," "holistic," "synergy."

Your writing rules:
- Active voice, varied sentence length
- Max 4 sentences per paragraph
- Inverted pyramid in every section (key info first)
- Each H2 is self-contained (no "as mentioned above" references)
- Bold entities on first occurrence
- Internal links as: [anchor text](link-target: {Topic Name})
- Image placeholders: ![descriptive alt text](image-placeholder)
- Tables for comparisons (never inline lists of 4+ items)
- First paragraph: primary keyword + clear definition + extractable answer (50-80 words)"""

QA_EDITOR_SYSTEM = """You are a meticulous Content QA Editor and SEO Compliance Specialist.
You have reviewed thousands of SEO articles. You have an eagle eye for compliance issues — meta tag lengths, keyword placement, banned phrases, content structure.
You never let a subpar article through. Your QA reports are thorough and actionable.

You have access to:
- banned_phrase_checker: scans for banned AI cliché phrases
- file_writer: saves the final article with QA report appended"""


def run_production(
    topic_name: str,
    primary_keyword: str,
    secondary_keywords: str,
    content_type: str,
    search_intent: str,
    word_count_min: int,
    word_count_max: int,
    target_entities: str,
    internal_link_targets: str,
    brief_content: str,
    client_name: str,
    brand_voice: str,
    brand_tone: str,
    style_preferences: str,
    output_dir: str,
    date: str,
    max_qa_attempts: int = 3,
    on_log: callable = None,
) -> tuple[str, bool, int]:
    """Write an article and run QA.

    Returns:
        Tuple of (article_text, qa_passed, attempts)
    """
    log = on_log or (lambda s, m: None)
    word_count_target = (word_count_min + word_count_max) // 2

    # ── Step 1: Write the article ────────────────────────────────
    log("Writer Agent", f"Writing article: {topic_name}")

    writer_system = WRITER_SYSTEM + f"""

Client context:
- Client: {client_name}
- Brand Voice: {brand_voice}
- Brand Tone: {brand_tone}
- Style: {style_preferences}"""

    writer_task = f"""Write a complete, publication-ready article based on this approved content brief:

Topic: {topic_name}
Primary Keyword: {primary_keyword}
Secondary Keywords: {secondary_keywords}
Content Type: {content_type}
Word Count Target: {word_count_min}-{word_count_max} words
Search Intent: {search_intent}
Target Entities: {target_entities}
Internal Link Targets: {internal_link_targets}

Brief content:
{brief_content}

ARTICLE STRUCTURE (follow exactly):

---
meta_title: "[from brief, max 60 chars, keyword in first 30 chars]"
meta_description: "[from brief, max 155 chars, compelling]"
url_slug: "[from brief]"
primary_keyword: "{primary_keyword}"
word_count: [actual count]
date_created: "{date}"
client: "{client_name}"
status: "draft"
---

# [H1 with primary keyword, different from meta_title]

[Opening paragraph: primary keyword, answer, inverted pyramid, 50-80 words]

## [H2 sections following brief outline]

## Frequently Asked Questions
### [Question from brief]
[40-60 word answer, direct answer first, snippet-optimized]

## Key Takeaways
- [5 actionable bullet points]

Write the FULL article now. Aim for approximately {word_count_target} words."""

    article = chat(
        system_prompt=writer_system,
        user_prompt=writer_task,
        temperature=0.7,
    )

    # ── Step 2: QA Review ────────────────────────────────────────
    output_path = f"{output_dir}/articles/{topic_name} - {date}.md"
    qa_passed = False

    for attempt in range(1, max_qa_attempts + 1):
        log("QA Agent", f"QA attempt {attempt}/{max_qa_attempts} for: {topic_name}")

        qa_task = f"""Run the full QA protocol on this article for: "{topic_name}"
Primary Keyword: {primary_keyword}
Word Count Range: {word_count_min}-{word_count_max}
Target Entities: {target_entities}
Internal Link Targets: {internal_link_targets}
Secondary Keywords: {secondary_keywords}
Content Type: {content_type}
Search Intent: {search_intent}

ARTICLE TO REVIEW:
{article}

Use the banned_phrase_checker tool to scan the article for banned phrases.

CHECK EVERY ITEM BELOW. For each item, mark PASS ✅ or FAIL ❌.

STRUCTURE & INTENT:
- [ ] Search intent ({search_intent}) matches content
- [ ] Inverted pyramid: key answer in first paragraph
- [ ] All H2 sections atomic and self-contained
- [ ] Key Takeaways present (exactly 5 items)
- [ ] FAQ section present (4-6 questions)

SEO & TECHNICAL:
- [ ] Meta title: present, <60 chars, has "{primary_keyword}"
- [ ] Meta description: present, <155 chars, compelling, has keyword
- [ ] URL slug: present, clean, keyword-focused
- [ ] Primary keyword in H1, first paragraph, and 2+ H2 headings
- [ ] Secondary keywords distributed: {secondary_keywords}
- [ ] Internal link placeholders for: {internal_link_targets}
- [ ] Image alt text on all placeholders
- [ ] Word count within {word_count_min}-{word_count_max} range

OPTIMIZATION:
- [ ] Information gain element present
- [ ] Comparison table (required if content type is "comparison")
- [ ] FAQ answers 40-60 words, snippet-optimized
- [ ] Target entities mentioned and bolded: {target_entities}
- [ ] No banned AI cliché phrases (use banned_phrase_checker tool)

If ALL items PASS:
- Append a QA Report table to the article
- Add: `QA Status: PASSED | Attempts: {attempt}/{max_qa_attempts} | Date: {date}`
- Save the complete article + QA report to: {output_path}

If ANY items FAIL:
- Provide the REWRITTEN article with fixes applied
- Then re-run the QA checks on the rewritten version
- After {max_qa_attempts} failed attempts on any item, mark it with ⚠️ and save anyway
- Add: `QA Status: FLAGGED | Attempts: {attempt}/{max_qa_attempts} | Date: {date}`

Always save the final article with QA report using the file_writer tool."""

        tools = {
            "banned_phrase_checker": banned_phrase_checker,
            "file_writer": file_writer,
        }

        result = chat(
            system_prompt=QA_EDITOR_SYSTEM,
            user_prompt=qa_task,
            tools=tools,
            tool_declarations=[QA_TOOL_DECL],
            temperature=0.2,
        )

        if "QA Status: PASSED" in result or "PASSED" in result.upper():
            qa_passed = True
            log("QA Agent", f"✅ QA PASSED for: {topic_name}")
            return result, True, attempt

        # Use the QA-edited version for the next attempt
        article = result
        log("QA Agent", f"QA attempt {attempt} flagged issues, {'retrying' if attempt < max_qa_attempts else 'finalizing'}")

    log("QA Agent", f"⚠️ QA FLAGGED after {max_qa_attempts} attempts: {topic_name}")
    return article, False, max_qa_attempts
