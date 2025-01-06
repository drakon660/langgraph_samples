import logging
from langchain_ollama import ChatOllama

from ollama_run_graph_with_tool import get_current_time_and_date

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

tools = [get_current_time_and_date]

llm = ChatOllama(model="qwen2.5:7b")

llm_with_tools = llm.bind_tools(tools)
query = "Capital of Poland"

chain = llm_with_tools
#| PydanticToolsParser(tools=[get_current_time_and_date]))
result = chain.invoke(query)
logger.info(result)