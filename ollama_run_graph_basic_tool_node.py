from datetime import datetime
from typing import Annotated
from langchain_core.tools import Tool, StructuredTool
from sqlalchemy import TryCast
from typing_extensions import TypedDict
from langchain_ollama import OllamaLLM, ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import ToolMessage
import logging
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict | None):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:

            tool = self.tools_by_name.get(tool_call["name"])

            if not tool:
                raise ValueError(f"Tool {tool_call['name']} not found.")

            tool_result = ""

            try:
                # Check if the tool expects arguments
                args = tool_call.get("args", {})

                if not args and hasattr(tool, "args_schema") and tool.args_schema is None:
                    # For tools without arguments, invoke without args
                    logger.info("no args")

                    #BaseTool.invoke() missing 1 required positional argument: 'input'
                    tool_result = tool.invoke()
                else:
                    # Otherwise, pass arguments
                    logger.info("args")
                    tool_result = tool.invoke(args)

            except Exception as e:
                logger.error(e)

            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                )
            )
        return {"messages": outputs}

# Configure logging


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


def route_tools(
    state: State,
):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END

graph_builder = StateGraph(State)

def get_current_time_and_date():
    """
    Returns the current date and time as a formatted string.
    """
    now = datetime.now()
    formatted_date_time = now.strftime("%Y-%m-%d %H:%M:%S")  # Format: YYYY-MM-DD HH:MM:SS
    logger.debug(f"Current Date and Time: {formatted_date_time}")
    return formatted_date_time


current_time_tool = Tool(
    name="get_current_time_and_date",
    func=get_current_time_and_date,
    description="Provides the current date and time as a formatted string.",
    #Indicate that this tool does not take any arguments        # Indicate that this tool does not take any arguments
)

# tool2 = StructuredTool.from_function(func=get_current_time_and_date,
#                                      name="get_current_time_and_date",
#                                      description="Provides the current date and time as a formatted string.",
#                                      )

#print(tool2.invoke(''))


llm = ChatOllama(model="qwen2.5:7b")

#llmChain = llm
llmChain = llm.bind_tools([get_current_time_and_date])

def chatbot(state: State):
    return {"messages": [llmChain.invoke(state["messages"])]}


# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.

tool_node = BasicToolNode(tools=[current_time_tool])
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)
#graph_builder.add_node("tools", tool_node)
# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "END" if
# it is fine directly responding. This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges(
    "chatbot",
    route_tools,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
    {"tools": "tools", END: END},
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph_builder.set_finish_point("chatbot")
graph = graph_builder.compile()

def stream_graph_updates(user_input: str):
    logger.info(user_input)
    for event in graph.stream({"messages": [("user", user_input)]}):
        logger.info(event)
        for value in event.values():
            response = value["messages"][-1].content
            logger.info(response)
            #print("Assistant:",response)


while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What do you know about LangGraph?"
        #print("User: " + user_input)
        logger.error('error')
        stream_graph_updates(user_input)
        break