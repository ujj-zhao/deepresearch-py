"""使用 create_agent 构建 DeepSeek 智能体。

DeepSeek 的 API Key 从 ``ai/.env`` 中的 ``DEEPSEEK_API_KEY`` 读取。
``ChatDeepSeek`` 自动读取环境变量 ``DEEPSEEK_API_KEY``，因此需要先 ``load_dotenv``。

注意：脚本不要命名为 ``langchain.py``，否则会与 ``langchain`` 包同名冲突，
导致 ``import langchain`` 解析到脚本自身而报 "not a package"。
"""

from ast import arg
from pathlib import Path
from dataclasses import dataclass
from typing import Literal, Callable, Any, Union
from langgraph.types import Command
from urllib import response

from dotenv import load_dotenv
from langchain_openai.chat_models.base import ChatOpenAI
from pydantic import BaseModel, Field
from langchain.agents import AgentState,create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.runtime import Runtime
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain_core.utils.uuid import uuid7
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, RemoveMessage
from langchain_core.load import dumpd, load
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse, AgentMiddleware, ToolCallRequest, before_model, after_model, SummarizationMiddleware, dynamic_prompt,PIIMiddleware
from langchain.agents.structured_output import ToolStrategy

# 把 ai/.env 载入环境变量（脚本在 ai/scripts/ 下，向上两级到 ai/）
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


'''
@tool
def calculate(expression: str) -> str:
    """计算数学表达式。expression 是待计算的算式，例如 "2 + 3"、"5 * 7"、"10 / 2"。"""
    result = eval(expression)  # 仅供演示；生产环境不要直接 eval 用户输入
    return str(result)

@tool
def search(query: str) -> str:
    """搜索信息。"""
    return f"搜索结果：{query}"

class MyState(AgentState):
    user_id: str
    call_count: int


class Answer(BaseModel):
    summary: str
    confidence: float


agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[calculate,search],
    system_prompt="你是一名乐于助人的助手。回答应简洁、准确。",
    response_format=Answer,
    state_schema=MyState,
)

result = agent.invoke({
    "user_id": "123",
    "call_count": 0,
    "messages": [{"role": "user", "content": "总结 AI 趋势"}]})
print(result)
print(result["structured_response"])
'''

'''
@dataclass
class Context:
    user_id: str

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    checkpointer=InMemorySaver(),
)

config = {"configurable": {"thread_id": str(uuid7())}}

result1 = agent.invoke(
    {"messages": [{"role": "user", "content": "旧金山的天气怎么样？"}]},
    config=config,
    context=Context(user_id="123"),
)

print(result1)

'''

# 同一对话中的后续轮次：复用相同的 thread_id 以保留历史记录
'''
result2 = agent.invoke(
    {"messages": [{"role": "user", "content": "那明天呢？"}]},
    config=config,
)

print(result2)
'''

'''
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[search],
)

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "搜索 AI 新闻并总结结果"}]},
    version="v3",
)


for snapshot in stream.values:
    print("*"*50)
    print(snapshot)
    # 每个快照都包含该时刻的完整状态
    latest_message = snapshot["messages"][-1]
    if latest_message.content:
        if isinstance(latest_message, HumanMessage):
            print(f"用户：{latest_message.content}")
        elif isinstance(latest_message, AIMessage):
            print(f"智能体：{latest_message.content}")
        elif isinstance(latest_message, ToolMessage):
            print(f"工具调用：{latest_message.content}")
    elif latest_message.tool_calls:
        print(f"正在调用工具：{[tc['name'] for tc in latest_message.tool_calls]}")

'''

agent = init_chat_model(
    "deepseek:deepseek-chat",
    max_retries=10,  # 网络不稳定时提高（默认值：6）
    timeout=120,     # 单位为秒；连接较慢时提高（默认值：60）
)

# conversation = [
#     {"role": "system", "content": "你是一位将英语翻译为法语的助手。"},
#     {"role": "user", "content": "翻译：I love programming."},
#     {"role": "assistant", "content": "J'adore la programmation."},
#     {"role": "user", "content": "翻译：I love building applications."}
# ]

# agent.invoke(conversation)

# for chunk in agent.stream("为什么鹦鹉的羽毛色彩鲜艳？"):
#     print(chunk.text, end="|", flush=True)

'''
responses = agent.batch([
    "为什么鹦鹉的羽毛色彩鲜艳？",
    "飞机为什么能飞？",
    "什么是量子计算？"
])
for response in responses:
    print(response)

'''

'''
@tool
def get_weather(location: str) -> str:
    """获取指定地点的天气。"""
    return f"{location} 天气晴朗。"

# 将一个或多个工具绑定到模型
tools = [get_weather]
tools_by_name = {tool.name: tool for tool in tools}
agent_with_tools = agent.bind_tools(tools)

# 第 1 步：模型生成工具调用
messages = [{"role": "user", "content": "波士顿的天气如何？"}]

'''

'''
ai_msg = agent_with_tools.invoke(messages)
messages.append(ai_msg)
print(ai_msg)
print(messages)

# 第 2 步：执行工具并收集结果
for tool_call in ai_msg.tool_calls:
    # 使用模型生成的参数执行工具
    tool = tools_by_name[tool_call["name"]]
    tool_result = tool.invoke(tool_call)
    messages.append(tool_result)

# 第 3 步：将结果传回模型以生成最终回复
final_response = agent_with_tools.invoke(messages)
print(final_response.content)


for chunk in agent_with_tools.stream(
    "波士顿和东京的天气如何？"
):
    # Tool call chunks arrive progressively
    for tool_chunk in chunk.tool_call_chunks:
        if name := tool_chunk.get("name"):
            print(f"Tool: {name}")
        if id_ := tool_chunk.get("id"):
            print(f"ID: {id_}")
        if args := tool_chunk.get("args"):
            print(f"Args: {args}")


gathered = None
for chunk in agent_with_tools.stream("波士顿的天气如何？"):
    gathered = chunk if gathered is None else gathered + chunk
    print(gathered.tool_calls)

'''

'''
class Movie(BaseModel):
    """包含详细信息的电影。"""
    title: str = Field(description="电影名称")
    year: int = Field(description="电影上映年份")
    director: str = Field(description="电影导演")
    rating: float = Field(description="电影的十分制评分")

model_with_structure = agent.with_structured_output(Movie, include_raw=True)
response = model_with_structure.invoke("提供电影《盗梦空间》的详细信息")
print(response)


def get_weather(location: str) -> str:
    """获取指定地点的天气。"""
    return f"{location} 天气晴朗。"


model_with_tools = agent.bind_tools([get_weather])
response = model_with_tools.invoke("巴黎的天气怎么样？")
print(response.content_blocks)
print("*"*50)
print(response.content)
print("*"*50)
print(response.usage_metadata)
print("*"*50)
print(response.response_metadata)

for tool_call in response.tool_calls:
    print(f"工具：{tool_call['name']}")
    print(f"参数：{tool_call['args']}")
    print(f"ID: {tool_call['id']}")

'''

'''
ai_message = AIMessage(
    content=[],
    tool_calls=[{
        "name": "get_weather",
        "args": {"location": "San Francisco"},
        "id": "call_123"
    }]
)

# 执行工具并创建结果消息
weather_result = "晴，72°F"
tool_message = ToolMessage(
    content=weather_result,
    tool_call_id="call_123"  # 必须与调用 ID 匹配
)

# 继续对话
messages = [
    HumanMessage("旧金山的天气怎么样？"),
    ai_message,  # 模型的工具调用
    tool_message,  # 工具执行结果
]
response = agent.invoke(messages)  # 模型处理结果
print(response.content_blocks)
'''

'''
message = AIMessage(
    content=[
        {"type": "thinking", "thinking": "...", "signature": "WaUjzkyp..."},
        {"type": "text", "text": "..."},
    ],
    response_metadata={"model_provider": "anthropic"}
)
print(message.content)
print(message.content_blocks)

message1 = HumanMessage("法国的首都是哪里？")

# 序列化为普通字典
serialized = dumpd(message1)
print(serialized)

# 反序列化回消息对象
restored = load(serialized)
print(restored.content)
'''

"""
自定义 Schema
"""
'''
class WeatherInput(BaseModel):
    """天气查询输入。"""
    location: str = Field(description="城市名称或坐标")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="首选温度单位"
    )
    include_forecast: bool = Field(
        default=False,
        description="是否包含未来 5 天预报"
    )

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """获取当前天气和可选预报。"""
    temp = 22 if units == "celsius" else 72
    result = f"{location} 当前天气：{temp} 度 {units[0].upper()}"
    if include_forecast:
        result += "\nNext 5 days: Sunny"
    return result

tools = [get_weather]
tools_by_name = {tool.name: tool for tool in tools}
agent_with_tools = agent.bind_tools(tools)

messages = [{"role": "user", "content": "波士顿的天气如何？"}]

response = agent_with_tools.invoke(messages)
messages.append(response)
for tool_call in response.tool_calls:
    print(f"工具：{tool_call['name']}")
    print(f"参数：{tool_call['args']}")
    print(f"ID: {tool_call['id']}")

    if tool_call["name"] == "get_weather":
        tool_call["args"] = {"location": "波士顿", "units": "fahrenheit", "include_forecast": True}
        tool_result = tools_by_name["get_weather"].invoke(tool_call)
        messages.append(tool_result)

final_response = agent_with_tools.invoke(messages)
print(final_response.content_blocks)

'''


"""
短期记忆
"""

'''
@tool
def get_weather(city: str, runtime: ToolRuntime) -> str:
    """获取指定城市的天气。"""
    writer = runtime.stream_writer

    # 在工具执行时流式发送自定义更新
    writer(f"正在查询城市数据：{city}")
    writer(f"已获取城市数据：{city}")

    return f"{city} 总是阳光明媚！"

@tool
def get_second_last_user_message(runtime: ToolRuntime) -> str:
    """获取用户倒数第二次发送的消息（即上一条人类消息），用于回答'我上一次问了什么'。"""
    human_messages = [
        message.content
        for message in runtime.state["messages"]
        if isinstance(message, HumanMessage)
    ]

    if len(human_messages) >= 2:
        return human_messages[-2]

    return "历史记录不足，未找到倒数第二条用户消息"

# 访问自定义状态字段
@tool
def get_user_preference(
    pref_name: str,
    runtime: ToolRuntime
) -> str:
    """获取用户偏好值。"""
    preferences = runtime.state.get("user_preferences", {})
    return preferences.get(pref_name, "未设置")

USER_DATABASE = {
    "user123": {
        "name": "Alice Johnson",
        "account_type": "高级",
        "balance": 5000,
        "email": "alice@example.com",
    },
    "user456": {
        "name": "Bob Smith",
        "account_type": "标准",
        "balance": 1200,
        "email": "bob@example.com",
    },
}

@tool(return_direct=True)
def fetch_and_store_order(order_id: str, runtime: ToolRuntime) -> Command:
    """获取订单状态并将其存入状态。"""
    status = f"订单 {order_id} 已发货，将在 2 天内送达。"
    return Command(
        update={
            "last_order_status": status,
            # 必须包含 ToolMessage，确保消息历史有效
            "messages": [
                ToolMessage(
                    content=status,
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


@dataclass
class UserContext:
    user_id: str

class OrderState(AgentState):
    last_order_status: str

@tool
def get_account_info(runtime: ToolRuntime[UserContext]) -> str:
    """获取当前用户的账户信息。"""
    user_id = runtime.context.user_id

    if user_id in USER_DATABASE:
        user = USER_DATABASE[user_id]
        return (
            f"账户持有人：{user['name']}\n"
            f"类型：{user['account_type']}\n"
            f"余额：${user['balance']}"
        )
    return "未找到用户"


model="deepseek:deepseek-chat"
agent = create_agent(
    model,
    tools=[get_account_info, get_second_last_user_message, get_user_preference, fetch_and_store_order],
    context_schema=UserContext,
    system_prompt="你是一名财务助手。",
    checkpointer=InMemorySaver(),
)

# 同一对话复用相同的 thread_id，历史消息才会从 checkpointer 恢复到 state
config = {"configurable": {"thread_id": "conv-001"}}

agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
            {"role": "user", "content": "我当前的余额是多少？"},
        ]
    },
    config=config,
    context=UserContext(user_id="user123"),
)

agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "我上一次询问了什么问题"},
        ]
    },
    config=config,
    context=UserContext(user_id="user123"),
)
result = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "波士顿的天气如何？"},
        ]
    },
    config=config,
    context=UserContext(user_id="user123"),
)


result = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "订单 #12345 当前是什么状态？"},
        ]
    },
    config=config,
    context=UserContext(user_id="user123"),
)
for msg in result["messages"]:
    msg.pretty_print()

'''


"""动态工具"""

'''
@tool
def get_weather(city: str, runtime: ToolRuntime) -> str:
    """获取指定城市的天气。"""
    writer = runtime.stream_writer

    # 在工具执行时流式发送自定义更新
    writer(f"正在查询城市数据：{city}")
    writer(f"已获取城市数据：{city}")

    return f"{city} 总是阳光明媚！"

@tool
def calculate_tip(bill_amount: float, tip_percentage: float = 20.0) -> str:
    """计算账单的小费金额。"""
    tip = bill_amount * (tip_percentage / 100)
    return f"Tip: ${tip:.2f}, Total: ${bill_amount + tip:.2f}"

class DynamicToolMiddleware(AgentMiddleware):
    """注册并处理动态工具的中间件。"""

    def wrap_model_call(self, request: ModelRequest, handler):
        # 将动态工具添加到请求中
        # 该工具可以从 MCP 服务器、数据库等来源加载
        updated = request.override(tools=[*request.tools, calculate_tip])
        return handler(updated)

    def wrap_tool_call(self, request: ToolCallRequest, handler):
        # 处理动态工具的执行
        if request.tool_call["name"] == "calculate_tip":
            return handler(request.override(tool=calculate_tip))
        return handler(request)


agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[get_weather],
    middleware=[DynamicToolMiddleware()]
)

# 智能体现在可以同时使用 get_weather 和 calculate_tip
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "波士顿的天气如何？"},
        {"role": "user", "content": "计算 85 美元账单的 20% 小费"}
    ]
})
for msg in result["messages"]:
    msg.pretty_print()

'''
# 中间件示例：在模型调用前和后处理消息
'''
@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) <= 3:
        return None  # No changes needed

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

agent = create_agent(
    "deepseek:deepseek-chat",
    tools=[],
    middleware=[trim_messages],
    checkpointer=InMemorySaver(),
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()

'''

#删除和摘要

'''
@after_model
def delete_old_messages(state: AgentState, runtime: Runtime) -> dict | None:
    """Remove old messages to keep conversation manageable."""
    messages = state["messages"]
    if len(messages) > 2:
        # remove the earliest two messages
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}
    return None


agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    system_prompt="Please be concise and to the point.",
    middleware=[SummarizationMiddleware(
        model="deepseek:deepseek-chat",
        temperature=0.8,
        trigger={"tokens": 100},
        keep= ("messages", 20)
    )],
    checkpointer=InMemorySaver(),
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
    config,
    version="v3",
)
for snapshot in stream.values:
    print([(message.type, message.content) for message in snapshot["messages"]])

agent.stream_events(
    {"messages": [{"role": "user", "content": "write a short poem about cats"}]},
    config,
    version="v3",
)
# for snapshot in stream.values:
#     print([(message.type, message.content) for message in snapshot["messages"]])

result = agent.invoke(
    {"messages": [{"role": "user", "content": "what's my name?"}]},
    config,
)
# for snapshot in stream.values:
#     print([(message.type, message.content) for message in snapshot["messages"]])

result["messages"][-1].pretty_print()

'''

# 修改短期记忆
'''
class CustomState(AgentState):  # [!code highlight]
    user_name: str

class CustomContext(BaseModel):
    user_id: str

@tool
def update_user_info(
    runtime: ToolRuntime[CustomContext, CustomState],
) -> Command:
    """Look up and update user info."""
    user_id = runtime.context.user_id
    name = "John Smith" if user_id == "user_123" else "Unknown user"
    return Command(update={  # [!code highlight]
        "user_name": name,
        # update the message history
        "messages": [
            ToolMessage(
                "Successfully looked up user information",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })

@tool
def greet(
    runtime: ToolRuntime[CustomContext, CustomState]
) -> str | Command:
    """Use this to greet the user once you found their info."""
    user_name = runtime.state.get("user_name", None)
    if user_name is None:
       return Command(update={
            "messages": [
                ToolMessage(
                    "Please call the 'update_user_info' tool it will get and update the user's name.",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })
    return f"Hello {user_name}!"

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[update_user_info, greet],
    state_schema=CustomState, # [!code highlight]
    context_schema=CustomContext,
)

agent.invoke(
    {"messages": [{"role": "user", "content": "greet the user"}]},
    context=CustomContext(user_id="user_123"),
)
'''

'''
class CustomContext(TypedDict):
    user_name: str


def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is always sunny!"


@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context["user_name"]
    system_prompt = f"You are a helpful assistant. Address the user as {user_name}."
    return system_prompt


agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
    middleware=[dynamic_system_prompt],
    context_schema=CustomContext,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    context=CustomContext(user_name="John Smith"),
)
for msg in result["messages"]:
    msg.pretty_print()

'''

# 结构化输出
'''
class ContactInfo(BaseModel):
    name: str = Field(description="Person's name")
    email: str = Field(description="Email address")

class EventDetails(BaseModel):
    event_name: str = Field(description="Name of the event")
    date: str = Field(description="Event date")


agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    response_format=ToolStrategy(Union[ContactInfo, EventDetails])
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract info: John Doe (john@email.com) is organizing Tech Conference on March 15th"}]
})
for msg in result["messages"]:
    msg.pretty_print()
'''

# 护栏
'''
agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    middleware=[
        # Redact emails in user input before sending to model
        PIIMiddleware(
            "email",
            strategy="redact",
            apply_to_input=True,
        ),
        # Mask credit cards in user input
        PIIMiddleware(
            "credit_card",
            strategy="mask",
            apply_to_input=True,
        ),
        # Block API keys - raise error if detected
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{32}",
            strategy="block",
            apply_to_input=True,
        ),
    ],
)

# When user provides PII, it will be handled according to the strategy
result = agent.invoke({
    "messages": [{"role": "user", "content": "My email is john.doe@example.com and card is 5105-1051-0510-5100"}]
})
for msg in result["messages"]:
    msg.pretty_print()

'''

@dataclass
class Context:
    user_name: str

# Dynamic prompts
@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context.user_name  # [!code highlight]
    system_prompt = f"You are a helpful assistant. Address the user as {user_name}."
    return system_prompt

# Before model hook
@before_model
def log_before_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:  # [!code highlight]
    print(f"Processing request for user: {runtime.context.user_name}")  # [!code highlight]
    return None

# After model hook
@after_model
def log_after_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:  # [!code highlight]
    print(f"Completed request for user: {runtime.context.user_name}")  # [!code highlight]
    return None

agent = create_agent(
    model="deepseek:deepseek-chat",
    tools=[],
    middleware=[dynamic_system_prompt, log_before_model, log_after_model],  # [!code highlight]
    context_schema=Context
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")
)
for msg in result["messages"]:
    msg.pretty_print()
