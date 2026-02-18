# Content Crew — Multi-Agent SEO Content Pipeline

A CrewAI-powered multi-agent system that automates the entire SEO content creation workflow: from topic research to content briefs to publication-ready articles with QA.

## Architecture

**5 specialized agents across 3 crews**, orchestrated by a CrewAI Flow:

| Phase | Crew | Agents | Output |
|-------|------|--------|--------|
| 1. Research | ResearchCrew | SEO Research Strategist, Topic Map Architect | CSV topic map (15-20 topics) |
| 2. Briefs | BriefCrew | Content Strategist | Markdown briefs per topic |
| 3. Production | ProductionCrew | Content Writer, QA Editor | Final articles with QA reports |

Human review checkpoints exist between every phase.

## Setup

### Prerequisites
- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
# With uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

### Configure API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required keys:
- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey)
- `SERPER_API_KEY` — from [serper.dev](https://serper.dev)

## Usage

### Run the full pipeline
```bash
python -m content_crew run
```

The system will:
1. Collect client info and seed topic interactively
2. **Phase 1**: Research the topic and generate a CSV topic map
3. ⏸️ Pause for your review
4. **Phase 2**: Generate content briefs for each topic
5. ⏸️ Pause for your review
6. **Phase 3**: Write articles with QA (auto-retries up to 3x)
7. Report results and export everything

### Generate flow visualization
```bash
python -m content_crew plot
```

## Output Structure

```
output/
├── topic_maps/
│   └── {Seed Topic} - {YYYY-MM-DD}.csv
├── briefs/
│   ├── {Topic Name} - {YYYY-MM-DD}.md
│   └── Brief Index - {YYYY-MM-DD}.md
└── articles/
    ├── {Topic Name} - {YYYY-MM-DD}.md
    └── Production Index - {YYYY-MM-DD}.md
```

## Model Configuration

The system uses Gemini 3 Pro Preview by default. To change the model, edit `MODEL` in your `.env` file. Any LiteLLM-compatible model string works (e.g., `openai/gpt-4o`, `anthropic/claude-sonnet-4`).
