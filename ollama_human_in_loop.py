from typing import Annotated
from typing_extensions import TypedDict
from langchain_ollama import OllamaLLM, ChatOllama
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import logging
from tools import get_current_time_and_date, save_graph_as_png
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

# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.set_entry_point("chatbot")
graph_builder.set_finish_point("chatbot")

#config and checkpoint goes together always
thread = {"configurable": {"thread_id": "1"}}
graph = graph_builder.compile(checkpointer=memory, interrupt_before=["tools"])


#tuple error before or after interrupt

def stream_graph_updates(user_input: str):
    logger.info(user_input)
    snapshot = graph.get_state (thread)
    logger.info(snapshot.next)
    for event in graph.stream({"messages": [("user", user_input)]}, thread):
        snapshot = graph.get_state(thread)
        logger.info(snapshot.values)
        for value in event.values():
            response = value["messages"][-1].content
            logger.info(response)

while True:
    try:
        # user_input = input("User: ")
        # if user_input.lower() in ["quit", "exit", "q"]:
        #     print("Goodbye!")
        #     break

        user_input = "What is the current time?"

        stream_graph_updates(user_input)
    except Exception as e:
        logger.error(e)
        break