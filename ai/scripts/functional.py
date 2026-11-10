"""Minimal LangGraph tool-calling agent demo (Functional API).

Same arithmetic-tool agent as ``graph.py``, but expressed with the
``langgraph.func`` API (``@entrypoint`` / ``@task``) instead of an explicit
``StateGraph``.  Control flow is plain Python (a ``while`` loop) rather than
conditional edges, and state is passed around as ordinary function arguments.
"""

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.func import entrypoint, task

model = ChatDeepSeek(model="deepseek-chat", temperature=0)


@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`."""
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Add `a` and `b`."""
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` by `b`."""
    return a / b


tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)


@task
def llm_call(messages: list[AnyMessage]) -> AIMessage:
    """Call the LLM and let it decide whether to invoke a tool."""
    return model_with_tools.invoke(
        [
            SystemMessage(
                content=(
                    "You are a helpful assistant tasked with performing arithmetic "
                    "on a set of inputs."
                )
            ),
            *messages,
        ]
    )


@task
def tool_node(name: str, args: dict, tool_call_id: str) -> ToolMessage:
    """Execute a single tool call and wrap the result in a ToolMessage."""
    observation = tools_by_name[name].invoke(args)
    return ToolMessage(content=observation, tool_call_id=tool_call_id)


@entrypoint()
def agent(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Loop: ask the LLM, run any requested tools, until the LLM answers plainly."""
    conversation = list(messages)
    response = llm_call(conversation).result()

    while response.tool_calls:
        conversation.append(response)
        tool_messages = [
            tool_node(tc["name"], tc["args"], tc["id"]).result()
            for tc in response.tool_calls
        ]
        conversation.extend(tool_messages)
        response = llm_call(conversation).result()

    conversation.append(response)
    return conversation


if __name__ == "__main__":
    print(agent.get_graph(xray=True).draw_mermaid())

    messages: list[AnyMessage] = [HumanMessage(content="Add 3 and 4.")]
    result = agent.invoke(messages)
    for message in result:
        message.pretty_print()
