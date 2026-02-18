"""Production Crew — Phase 3: Content Writing & QA."""

from __future__ import annotations

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from content_crew.tools.file_writer_tool import FileWriterTool
from content_crew.tools.banned_phrase_checker import BannedPhraseCheckerTool


@CrewBase
class ProductionCrew:
    """Crew for Phase 3: Article writing and QA review for a single topic."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def content_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["content_writer"],  # type: ignore[index]
            tools=[FileWriterTool()],
            verbose=True,
        )

    @agent
    def qa_editor(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_editor"],  # type: ignore[index]
            tools=[BannedPhraseCheckerTool(), FileWriterTool()],
            verbose=True,
        )

    @task
    def article_writing_task(self) -> Task:
        return Task(
            config=self.tasks_config["article_writing_task"],  # type: ignore[index]
        )

    @task
    def qa_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["qa_review_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Production crew for Phase 3."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
