import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_current_time_and_date():
    """
    Returns the current date and time as a formatted string.
    """
    now = datetime.now()
    formatted_date_time = now.strftime("%Y-%m-%d %H:%M:%S")  # Format: YYYY-MM-DD HH:MM:SS
    logger.debug(f"Current Date and Time: {formatted_date_time}")
    return formatted_date_time

def save_graph_as_png(graph, filename):
    """
    Generate a PNG image from a graph and save it to a specified filename.

    Args:
        graph: The input graph object with a `get_graph()` method.
        filename: The name of the file to save the PNG image.

    Returns:
        str: The path to the saved file if successful, otherwise None.
    """
    try:
        # Generate the PNG content using the graph's method
        png_content = graph.get_graph().draw_mermaid_png()

        # Save the PNG content to the specified file
        with open(filename, "wb") as file:
            file.write(png_content)

        # Optionally display the image (uncomment if needed)
        # display(Image(filename=filename))

        print(f"Graph successfully saved to {filename}")
        return filename
    except Exception as e:
        # Log the error and return None
        print(f"Failed to save graph as PNG: {e}")
        return None



def extract_tool_call_ids(ai_message):
    """
    Extracts tool call IDs from an AIMessage object.
    """
    if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
        return [tool_call["id"] for tool_call in ai_message.tool_calls if "id" in tool_call]
    return []