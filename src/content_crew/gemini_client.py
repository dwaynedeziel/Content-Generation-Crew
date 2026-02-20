"""LLM client — Anthropic Claude API wrapper.

Provides a `chat()` function with system prompts, user messages,
and automatic tool-use loops. Accepts Gemini-style tool declarations
and converts them internally to Anthropic format.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import anthropic


def _get_client() -> anthropic.Anthropic:
    """Create an Anthropic client."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return anthropic.Anthropic(api_key=api_key)


def _convert_gemini_type(t: str) -> str:
    """Convert Gemini type names (OBJECT, STRING) to JSON Schema (object, string)."""
    return t.lower()


def _convert_gemini_properties(props: dict) -> dict:
    """Convert Gemini-style properties to JSON Schema properties."""
    result = {}
    for name, spec in props.items():
        converted: dict[str, Any] = {}
        if "type" in spec:
            converted["type"] = _convert_gemini_type(spec["type"])
        if "description" in spec:
            converted["description"] = spec["description"]
        if "properties" in spec:
            converted["properties"] = _convert_gemini_properties(spec["properties"])
        if "required" in spec:
            converted["required"] = spec["required"]
        if "items" in spec:
            converted["items"] = _convert_gemini_properties({"_": spec["items"]})["_"]
        result[name] = converted
    return result


def _convert_tool_declarations(gemini_decls: list[dict]) -> list[dict]:
    """Convert Gemini-format tool declarations to Anthropic format.

    Gemini format:
        {"function_declarations": [{"name": ..., "description": ..., "parameters": {...}}]}

    Anthropic format:
        [{"name": ..., "description": ..., "input_schema": {"type": "object", ...}}]
    """
    anthropic_tools = []

    for decl_group in gemini_decls:
        func_decls = decl_group.get("function_declarations", [])
        for fd in func_decls:
            params = fd.get("parameters", {})
            input_schema: dict[str, Any] = {
                "type": "object",
                "properties": _convert_gemini_properties(params.get("properties", {})),
            }
            if "required" in params:
                input_schema["required"] = params["required"]

            anthropic_tools.append({
                "name": fd["name"],
                "description": fd.get("description", ""),
                "input_schema": input_schema,
            })

    return anthropic_tools


def chat(
    system_prompt: str,
    user_prompt: str,
    tools: dict[str, Callable] | None = None,
    tool_declarations: list[dict] | None = None,
    model_name: str | None = None,
    temperature: float = 0.7,
    max_tool_rounds: int = 10,
) -> str:
    """Send a message to Claude and return the text response.

    Args:
        system_prompt: System instruction for the model.
        user_prompt: The user's message / task description.
        tools: Dict mapping function names to callables.
        tool_declarations: Gemini-format function declarations (auto-converted).
        model_name: Override the model (default: from MODEL env var).
        temperature: Sampling temperature.
        max_tool_rounds: Max tool-use round trips before stopping.

    Returns:
        The model's final text response.
    """
    client = _get_client()

    model_id = model_name or os.environ.get("MODEL", "claude-sonnet-4-20250514")
    # Strip provider prefixes if present
    for prefix in ("anthropic/", "claude/"):
        if model_id.startswith(prefix):
            model_id = model_id[len(prefix):]

    # Convert tool declarations from Gemini format to Anthropic format
    anthropic_tools = []
    if tool_declarations:
        anthropic_tools = _convert_tool_declarations(tool_declarations)

    # Build initial messages
    messages = [{"role": "user", "content": user_prompt}]

    # Create request kwargs
    create_kwargs: dict[str, Any] = {
        "model": model_id,
        "max_tokens": 16384,
        "temperature": temperature,
        "system": system_prompt,
        "messages": messages,
    }
    if anthropic_tools:
        create_kwargs["tools"] = anthropic_tools

    # Initial request
    response = client.messages.create(**create_kwargs)

    # Tool-use loop
    rounds = 0
    while rounds < max_tool_rounds and response.stop_reason == "tool_use":
        # Collect all tool use blocks
        tool_use_blocks = [
            block for block in response.content
            if block.type == "tool_use"
        ]

        if not tool_use_blocks:
            break

        # Build assistant message with full content (text + tool_use blocks)
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call and build result message
        tool_results = []
        for tool_block in tool_use_blocks:
            func_name = tool_block.name
            func_args = tool_block.input or {}

            if tools and func_name in tools:
                try:
                    result = tools[func_name](**func_args)
                    result_str = str(result)
                except Exception as e:
                    result_str = f"Error calling {func_name}: {e}"
            else:
                result_str = f"Unknown function: {func_name}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})

        # Send tool results back
        create_kwargs["messages"] = messages
        response = client.messages.create(**create_kwargs)
        rounds += 1

    # Extract final text
    text_parts = [
        block.text for block in response.content
        if hasattr(block, "text") and block.text
    ]
    return "\n".join(text_parts)
