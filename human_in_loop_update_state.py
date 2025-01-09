from typing import Annotated

from langchain_core.messages import ToolMessage, AIMessage
from typing_extensions import TypedDict
from langchain_ollama import OllamaLLM, ChatOllama
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import logging
from tools import get_current_time_and_date, save_graph_as_png, extract_tool_call_ids
from langgraph.checkpoint.memory import MemorySaver


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
memory = MemorySaver()

class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

#somehow lama3.1/3.2 is not working correctly with ollama langraph and executing tool
llm = ChatOllama(model="qwen2.5:7b")

llm_with_tools = llm.bind_tools([get_current_time_and_date])

def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=[get_current_time_and_date])
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph_builder.set_entry_point("chatbot")
graph_builder.set_finish_point("chatbot")

graph = graph_builder.compile(
    checkpointer=memory,
    # This is new!
    interrupt_before=["tools"],
    # Note: can also interrupt **after** actions, if desired.
    # interrupt_after=["tools"]
)

thread = {"configurable": {"thread_id": "1"}}

answer = (
    "Current date and time is 01 November 2025"
)


def stream_graph_updates(user_input: str):
    logger.info(user_input)
    #snapshot = graph.get_state (thread)
    #logger.info(snapshot.next)
    for event in graph.stream({"messages": [("user", user_input)]}, thread):
        snapshot = graph.get_state(thread)
        #logger.info(snapshot.values)

try:
    user_input = "What is the current time?"
    stream_graph_updates(user_input)

    snapshot = graph.get_state(thread)
    existing_message = snapshot.values["messages"][-1]

    new_messages = [
        # The LLM API expects some ToolMessage to match its tool call. We'll satisfy that here.
        ToolMessage(content=answer, tool_call_id=existing_message.tool_calls[0]["id"]),
        # And then directly "put words in the LLM's mouth" by populating its response.
        AIMessage(content=answer),
    ]

    graph.update_state(
        # Which state to update
        thread,
        # The updated values to provide. The messages in our `State` are "append-only", meaning this will be appended
        # to the existing state. We will review how to update existing messages in the next section!
        {"messages": new_messages},
    )

    graph.update_state(
        thread,
        {"messages": [AIMessage(content="I'm an AI expert!")]},
        # Which node for this function to act as. It will automatically continue
        # processing as if this node just ran.
        as_node="chatbot"
    )


    # logger.info("Last 3 messages;")
    # for message in graph.get_state(thread).values["messages"][-3:]:
    #     logger.info(message)

    stream_graph_updates("Tell me what I was asking about?")

    state = graph.get_state(thread)

    for message in state.values["messages"]:
        logger.info(message)


except Exception as e:
    logger.error(e)
