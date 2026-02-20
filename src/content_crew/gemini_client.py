"""Gemini API client — thin wrapper around google-generativeai.

Provides a simple `chat()` function that handles system prompts,
user messages, and automatic function calling loops.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

import google.generativeai as genai


def _configure():
    """Configure the Gemini API key."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    genai.configure(api_key=api_key)


def chat(
    system_prompt: str,
    user_prompt: str,
    tools: dict[str, Callable] | None = None,
    tool_declarations: list[dict] | None = None,
    model_name: str | None = None,
    temperature: float = 0.7,
    max_tool_rounds: int = 10,
) -> str:
    """Send a message to Gemini and return the text response.

    Args:
        system_prompt: System instruction for the model.
        user_prompt: The user's message / task description.
        tools: Dict mapping function names to callables. When the model
               requests a function call, it will be executed automatically.
        tool_declarations: Gemini function declarations for the tools.
        model_name: Override the model (default: from MODEL env var).
        temperature: Sampling temperature.
        max_tool_rounds: Max function-call round trips before stopping.

    Returns:
        The model's final text response.
    """
    _configure()

    model_id = model_name or os.environ.get("MODEL", "gemini-3-pro")
    # Strip "gemini/" prefix if present (LiteLLM convention)
    if model_id.startswith("gemini/"):
        model_id = model_id[len("gemini/"):]

    # Build generation config
    gen_config = genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=16384,
    )

    # Build model with tools if provided
    model_kwargs: dict[str, Any] = {
        "model_name": model_id,
        "system_instruction": system_prompt,
        "generation_config": gen_config,
    }

    if tool_declarations:
        model_kwargs["tools"] = tool_declarations

    model = genai.GenerativeModel(**model_kwargs)
    chat_session = model.start_chat()

    # Send initial message
    response = chat_session.send_message(user_prompt)

    # Function calling loop
    rounds = 0
    while rounds < max_tool_rounds:
        # Check if the model wants to call a function
        if not response.candidates:
            break

        candidate = response.candidates[0]

        # Check for function calls in parts
        function_calls = []
        for part in candidate.content.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                function_calls.append(part.function_call)

        if not function_calls:
            break  # No more function calls, we have the final response

        # Execute each function call and collect responses
        function_responses = []
        for fc in function_calls:
            func_name = fc.name
            func_args = dict(fc.args) if fc.args else {}

            if tools and func_name in tools:
                try:
                    result = tools[func_name](**func_args)
                    result_str = str(result)
                except Exception as e:
                    result_str = f"Error calling {func_name}: {e}"
            else:
                result_str = f"Unknown function: {func_name}"

            function_responses.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=func_name,
                        response={"result": result_str},
                    )
                )
            )

        # Send function results back to the model
        response = chat_session.send_message(function_responses)
        rounds += 1

    # Extract final text
    if response.candidates:
        parts = response.candidates[0].content.parts
        text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
        return "\n".join(text_parts)

    return ""
