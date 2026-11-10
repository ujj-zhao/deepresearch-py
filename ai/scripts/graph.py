"""Minimal LangGraph tool-calling agent demo.

Runs a two-node loop: an LLM node decides whether to call arithmetic tools,
and a tool node executes the requested tool call.
"""

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph

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


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


def llm_call(state: MessagesState) -> dict:
    """Call the LLM and let it decide whether to invoke a tool."""
    response = model_with_tools.invoke(
        [
            SystemMessage(
                content=(
                    "You are a helpful assistant tasked with performing arithmetic "
                    "on a set of inputs."
                )
            ),
            *state["messages"],
        ]
    )
    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def tool_node(state: MessagesState) -> dict:
    """Execute all tool calls in the latest AI message."""
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return {"messages": []}

    result = []
    for tool_call in last_message.tool_calls:
        tool_ = tools_by_name[tool_call["name"]]
        observation = tool_.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}


def should_continue(state: MessagesState) -> Literal["tool_node", "__end__"]:
    """Route to the tool node or end based on the latest message."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_node"
    return "__end__"


agent_builder = StateGraph(MessagesState)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", END],
)
agent_builder.add_edge("tool_node", "llm_call")
agent = agent_builder.compile()


if __name__ == "__main__":
    print(agent.get_graph(xray=True).draw_mermaid())

    messages: list[AnyMessage] = [HumanMessage(content="Add 3 and 4.")]
    result = agent.invoke({"messages": messages, "llm_calls": 0})
    for message in result["messages"]:
        message.pretty_print()
