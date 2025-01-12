from typing import Annotated, Literal

from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from typing_extensions import TypedDict
from langchain_ollama import OllamaLLM, ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import logging
from tools import get_current_time_and_date, save_graph_as_png, extract_tool_call_ids
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
memory = MemorySaver()

class RequestAssistance(BaseModel):
    """Escalate the conversation to an expert. Use this if you are unable to assist directly or if the user requires support beyond your permissions.

    To use this function, relay the user's 'request' so the expert can provide the right guidance.
    """

    request: str

class State(TypedDict):
    messages: Annotated[list, add_messages]
    ask_human: bool

graph_builder = StateGraph(State)

#somehow lama3.1/3.2 is not working correctly with ollama langraph and executing tool
llm = ChatOllama(model="qwen2.5:7b")

llm_with_tools = llm.bind_tools([get_current_time_and_date] + [RequestAssistance])

def chatbot(state: State):
    response = llm_with_tools.invoke(state["messages"])
    ask_human = False
    if (
        response.tool_calls
        and response.tool_calls[0]["name"] == RequestAssistance.__name__
    ):
        ask_human = True
    return {"messages": [response], "ask_human": ask_human}

def create_response(response: str, ai_message: AIMessage):
    return ToolMessage(
        content=response,
        tool_call_id=ai_message.tool_calls[0]["id"],
    )

def human_node(state: State) -> dict[str, list[ToolMessage] | bool]:
    new_messages = []
    if not isinstance(state["messages"][-1], ToolMessage):
        # Typically, the user will have updated the state during the interrupt.
        # If they choose not to, we will include a placeholder ToolMessage to
        # let the LLM continue.
        new_messages.append(
            create_response("No response from human.", state["messages"][-1])
        )
    return {
        # Append the new messages
        "messages": new_messages,
        # Unset the flag
        "ask_human": False,
    }

def select_next_node(state: State):
    if state["ask_human"]:
        return "human"
    # Otherwise, we can route as before
    return tools_condition(state)

graph_builder.add_node("human", human_node)

graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=[get_current_time_and_date])
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    select_next_node,
    {"human": "human", "tools": "tools", END: END},
)

graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph_builder.set_entry_point("chatbot")
graph_builder.set_finish_point("chatbot")

graph = graph_builder.compile(
    checkpointer=memory,
    # This is new!
    interrupt_before=["human"],
    # Note: can also interrupt **after** actions, if desired.
    # interrupt_after=["tools"]
)

thread = {"configurable": {"thread_id": "1"}}

def stream_graph_updates(user_input: str):
    logger.info(user_input)
    #snapshot = graph.get_state (thread)
    #logger.info(snapshot.next)
    for event in graph.stream({"messages": [("user", user_input)]}, thread):
        g = event
        snapshot = graph.get_state(thread)
        #logger.info(snapshot.values)

try:

    stream_graph_updates("What time is it?")
    stream_graph_updates("I need assistance with that date and time")

    state = graph.get_state(thread)

    events = graph.stream(None, thread, stream_mode="values")

    to_replay = None
    for state in graph.get_state_history(thread):
        logger.info(f"Num Messages: {len(state.values['messages'])}, Next: {state.next}")
        logger.info("-" * 80)
        if len(state.values["messages"]) == 6:
            pass
            # We are somewhat arbitrarily selecting a specific state based on the number of chat messages in the state.
            # to_replay = state  # Complete the assignment here

    for message in state.values["messages"]:
        logger.info(message)

except Exception as e:
    logger.error(e)
