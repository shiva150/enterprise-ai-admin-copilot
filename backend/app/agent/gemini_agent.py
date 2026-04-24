"""Real Gemini-backed agent. Used when USE_MOCK_LLM=0.

Response shape matches MockAgentExecutor exactly:
    {answer, reasoning, sources, trace, suggested_action, executed}
(plus `metrics` injected by _TimedAgent in agent.py)

Uses LangChain's model-agnostic `create_tool_calling_agent` so the same
`format_response()` handles the intermediate_steps shape regardless of
which LLM generated them.
"""

from typing import Any

from app.agent._format import db_sources, logs_source, rag_source, trace_entry


def _fmt_args(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def _fmt_obs(obs: Any) -> str:
    if isinstance(obs, list):
        return f"{len(obs)} result(s)"
    s = str(obs)
    return s if len(s) <= 80 else s[:77] + "..."


def format_response(result: dict) -> dict:
    """Convert a LangChain AgentExecutor result into the API schema."""
    steps = result.get("intermediate_steps", [])
    reasoning_lines: list[str] = []
    sources: list[str] = []
    trace: list[dict] = []
    suggested_action: dict | None = None

    for i, (action, observation) in enumerate(steps, 1):
        tool_input = (
            action.tool_input
            if isinstance(action.tool_input, dict)
            else {"input": action.tool_input}
        )
        reasoning_lines.append(
            f"Step {i}: {action.tool}({_fmt_args(tool_input)}) -> {_fmt_obs(observation)}"
        )
        trace.append(trace_entry(action.tool, tool_input, observation))

        if action.tool == "query_db":
            sources.extend(
                db_sources(
                    tool_input.get("table", ""),
                    tool_input.get("filters", {}) or {},
                    observation,
                )
            )
        elif action.tool == "fetch_logs":
            sources.append(logs_source(tool_input))
        elif action.tool == "retrieve_context":
            if isinstance(observation, list):
                sources.extend(rag_source(d) for d in observation)
        elif action.tool == "trigger_action":
            suggested_action = {
                "action": tool_input.get("action"),
                "params": tool_input.get("params", {}) or {},
            }

    sources = list(dict.fromkeys(sources))

    return {
        "answer": result.get("output", ""),
        "reasoning": "\n".join(reasoning_lines) if reasoning_lines else "(no tool calls)",
        "sources": sources,
        "trace": trace,
        "suggested_action": suggested_action,
        "executed": False,
    }


class GeminiAgentExecutor:
    """Thin wrapper around LangChain's create_tool_calling_agent + AgentExecutor,
    backed by Google Gemini via langchain-google-genai."""

    def __init__(self, tools: list) -> None:
        # Lazy imports so mock-mode runs don't pay the cost or require a working key.
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_google_genai import ChatGoogleGenerativeAI

        from app.agent.prompts import SYSTEM_PROMPT
        from app.config import settings

        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is empty. Set it in backend/.env "
                "(get one at https://aistudio.google.com/apikey) or flip USE_MOCK_LLM=1."
            )

        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0,
            google_api_key=settings.gemini_api_key,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )
        agent = create_tool_calling_agent(llm, tools, prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=tools,
            return_intermediate_steps=True,
            verbose=False,
            max_iterations=8,
            handle_parsing_errors=True,
        )

    def invoke(self, inputs: dict) -> dict:
        query = inputs["query"]
        result = self._executor.invoke({"input": query})
        return format_response(result)
