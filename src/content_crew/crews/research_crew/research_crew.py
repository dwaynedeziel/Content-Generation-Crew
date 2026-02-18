"""Research Crew — Phase 1: Topic Map Generation."""

from __future__ import annotations

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool

from content_crew.tools.csv_writer_tool import CSVWriterTool


@CrewBase
class ResearchCrew:
    """Crew for Phase 1: SEO research and topic map generation."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def seo_research_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["seo_research_strategist"],  # type: ignore[index]
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def topic_map_architect(self) -> Agent:
        return Agent(
            config=self.agents_config["topic_map_architect"],  # type: ignore[index]
            tools=[CSVWriterTool()],
            verbose=True,
        )

    @task
    def competitor_audit_task(self) -> Task:
        return Task(
            config=self.tasks_config["competitor_audit_task"],  # type: ignore[index]
        )

    @task
    def keyword_research_task(self) -> Task:
        return Task(
            config=self.tasks_config["keyword_research_task"],  # type: ignore[index]
        )

    @task
    def topic_map_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config["topic_map_generation_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Research crew for Phase 1."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
