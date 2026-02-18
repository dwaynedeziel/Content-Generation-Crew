"""Brief Crew — Phase 2: Content Brief Generation."""

from __future__ import annotations

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool

from content_crew.tools.file_writer_tool import FileWriterTool


@CrewBase
class BriefCrew:
    """Crew for Phase 2: Content brief generation for a single topic."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def content_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["content_strategist"],  # type: ignore[index]
            tools=[SerperDevTool(), FileWriterTool()],
            verbose=True,
        )

    @task
    def competitor_research_task(self) -> Task:
        return Task(
            config=self.tasks_config["competitor_research_task"],  # type: ignore[index]
        )

    @task
    def brief_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config["brief_generation_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Brief crew for Phase 2."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
