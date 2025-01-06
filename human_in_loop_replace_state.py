from typing import Annotated

from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
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

def stream_graph_updates(user_input: str):
    logger.info(user_input)
    # snapshot = graph.get_state (thread)
    # logger.info(snapshot.next)
    for event in graph.stream({"messages": [("user", user_input)]}, thread, stream_mode="values"):
        #logger.info(event)
        for value in event.values():
           #logger.info(value)
            pass
        #snapshot = graph.get_state(thread)
        #logger.info(snapshot.values)

#PROBLEMATIC EXAMPLE SEE IT LATER

try:
    user_input = "What is the current time?"
    stream_graph_updates(user_input)

    snapshot = graph.get_state(thread)
    existing_message = snapshot.values["messages"][-1]

    #logger.info("Original")
    #logger.info(existing_message.id)
    #logger.info(existing_message.tool_calls[0])
    new_tool_call = existing_message.tool_calls[0].copy()
    #new_tool_call["args"]["query"] = "What is the current time minus one year"
    new_message = HumanMessage(
        content=existing_message.content,
        tool_calls=[new_tool_call],
        # Important! The ID is how LangGraph knows to REPLACE the message in the state rather than APPEND this messages
        id=existing_message.id,
    )

    # logger.info("Updated")
    # logger.info(new_message.tool_calls[0])
    # logger.info(new_message.id)
    graph.update_state(thread, {"messages": [new_message]})

    #logger.info("\n\nTool calls")
    #logger.info(graph.get_state(thread).values["messages"][-1].tool_calls)

    stream_graph_updates("Tell me what I was asking about?")

    now = graph.get_state(thread)
    for message in now.values["messages"]:
        logger.info(message)
    #logger.info(graph.get_state(thread).values["messages"][-4].content)


except Exception as e:
    logger.error(e)

#PROBLEMATIC EXAMPLE SEE IT LATER