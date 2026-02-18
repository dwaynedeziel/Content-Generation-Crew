"""Main entry point for the Content Crew pipeline.

Usage:
    python -m content_crew web       # Launch web dashboard (recommended)
    python -m content_crew run       # Run the full pipeline (CLI mode)
    python -m content_crew plot      # Generate flow visualization
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv


def setup_environment():
    """Load environment variables and configure the LLM."""
    # Load .env from the project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(project_root, ".env")
    load_dotenv(env_path)

    # Verify required keys
    gemini_key = os.environ.get("GEMINI_API_KEY")
    serper_key = os.environ.get("SERPER_API_KEY")

    if not gemini_key:
        print("❌ Missing GEMINI_API_KEY in .env file")
        sys.exit(1)
    if not serper_key:
        print("❌ Missing SERPER_API_KEY in .env file")
        sys.exit(1)

    # Configure the model for CrewAI (via LiteLLM)
    model = os.environ.get("MODEL", "gemini/gemini-3-pro-preview")
    os.environ["LITELLM_MODEL"] = model

    # Set GEMINI_API_BASE if provided
    api_base = os.environ.get("GEMINI_API_BASE")
    if api_base:
        os.environ["GEMINI_API_BASE"] = api_base

    print(f"🔧 Model: {model}")
    print(f"🔑 Gemini API Key: ...{gemini_key[-4:]}")
    print(f"🔑 Serper API Key: ...{serper_key[-4:]}")


def run():
    """Run the full content creation pipeline."""
    setup_environment()

    from content_crew.flow import ContentFlow

    print("\n🚀 Starting Content Creation Pipeline...")
    print("=" * 60 + "\n")

    flow = ContentFlow()
    result = flow.kickoff()
    print(f"\n🏁 Pipeline complete. Final result: {result}")


def plot():
    """Generate a flow visualization."""
    setup_environment()

    from content_crew.flow import ContentFlow

    flow = ContentFlow()
    flow.plot("content_flow_visualization")
    print("📊 Flow visualization saved as 'content_flow_visualization.html'")


def web():
    """Launch the Streamlit web dashboard."""
    setup_environment()

    import subprocess

    app_path = os.path.join(os.path.dirname(__file__), "streamlit_app.py")
    print("\n🌐 Launching Content Crew Dashboard...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", "8501",
        "--server.headless", "true",
    ])


def main():
    """CLI entry point."""
    args = sys.argv[1:] if len(sys.argv) > 1 else ["run"]
    command = args[0].lower()

    if command == "web":
        web()
    elif command == "run":
        run()
    elif command == "plot":
        plot()
    elif command == "help":
        print(__doc__)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
