from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

class State(TypedDict):
    input: str
    user_feedback: str

def step_1(state):
    print("---Step 1---")
    pass

def step_2(state):
    print("---Step 2---")
    pass

def human_feedback(state:State):
    print("---human_feedback---")

    return {
        "user_feedback": "dupa",
    }

def step_3(state):
    print("---Step 3---")
    pass

builder = StateGraph(State)
builder.add_node("step_1", step_1)
builder.add_node("step_2", step_2)
builder.add_node("human_feedback", human_feedback)
builder.add_node("step_3", step_3)

builder.add_edge(START, "step_1")
builder.add_edge("step_1","step_2")
builder.add_edge("step_2", "human_feedback")
builder.add_edge("human_feedback", "step_3")
builder.add_edge("step_3", END)

memory = MemorySaver()

thread = {"configurable": {"thread_id":"1"}}

graph = builder.compile(checkpointer=memory)

user_input = {"input" : "hello_word"}

result = graph.invoke(user_input, thread)
print(result)

# for event in graph.stream(user_input, thread):
#     print(graph.get_state(thread).values)
#
# #graph.update_state(thread,{"user_feedback": user_input}, as_node="human_feedback")
#
# print("---state after update---")
# print(graph.get_state(thread).values)
#
# for event in graph.stream(None, thread):
#    print(graph.get_state(thread).values)




