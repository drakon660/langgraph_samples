from typing import TypedDict, Annotated, List, Literal
from langgraph.graph import StateGraph
from langgraph.graph.graph import END, START, CompiledGraph
from langgraph.graph.message import add_messages
import random, operator
from IPython.display import Image, display


class TestState(TypedDict):
    messages: Annotated[List[str], operator.add()]

test_workflow = StateGraph(TestState)

def node1(state: TestState):
    return {"messages": ["Hello from node 1"]}

def node2(state: TestState):
    return {"messages": ["Hello from node 2"]}

def node3(state: TestState):
    return {"messages": ["Hello from node 3"]}

def node4(state: TestState):
    return {"messages": ["Hello from node 4"]}

def node5(state: TestState):
    return {"messages": ["Hello from node 5"]}

def route(state: TestState)->Literal["node5", "__end__"]:
    if random.choice([True, False]):
        return "node5"
    return "__end__"

test_workflow.add_node("node1", node1)
test_workflow.add_node("node2", node2)
test_workflow.add_node("node3", node3)
test_workflow.add_node("node4", node4)
test_workflow.add_node("node5", node5)

test_workflow.add_edge(START, "node1")
test_workflow.add_edge("node1", "node2")
test_workflow.add_edge("node2", "node3")
test_workflow.add_edge("node3", "node4")
test_workflow.add_edge("node5", "node4")

#test_workflow.add_conditional_edges("node4", route, {"node5": "node5", "__end__": "__end__"})
test_workflow.add_conditional_edges("node4", route)
flo = test_workflow.compile()

result = flo.invoke({"messages":["Mysadd"]})
print(result)

