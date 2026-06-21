"""A2A (Agent-to-Agent) protocol placeholder.

Phase 2 feature — defines the interface for future implementation.

A2A enables the gateway to:
  - Publish itself as an A2A Agent Card (/.well-known/agent-card.json)
  - Accept task delegations from other agents
  - Delegate tasks to other agents
  - Discover agent capabilities via Agent Cards
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AgentAdapter(ABC):
    """Abstract adapter for Agent-to-Agent communication."""

    agent_key: str

    @abstractmethod
    async def discover(self, agent_card_url: str) -> dict:
        """Discover an agent via its Agent Card."""
        ...

    @abstractmethod
    async def send_task(self, agent_url: str, task: dict) -> dict:
        """Send a task to another agent."""
        ...

    @abstractmethod
    async def receive_task(self, task: dict) -> dict:
        """Handle an incoming task from another agent."""
        ...
