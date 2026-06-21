from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict


# --- State ---
class ReservationState(TypedDict):
    reservation_data: dict
    admin_response: dict
    graph_state: str


# --- Nodes ---
def chatbot_node(state: ReservationState):
    print("--- Chatbot Node ---")
    # Mocking reservation data generation
    reservation_data = {
        "name": "Diana Terzi",
        "plate": "HG67-76",
        "date": "2026-12-02",
        "time": "12:15",
        "created_at": "2026-06-21 19:38:36"
    }
    print(f"Generated reservation data: {reservation_data}")
    return {"reservation_data": reservation_data, "graph_state": "chatbot_done"}


def admin_agent_node(state: ReservationState):
    print("--- Admin Agent Node ---")
    reservation_data = state["reservation_data"]

    # Mocking admin response
    admin_response = {
        "status": "confirmed",  # Try changing this to "rejected" for testing
        "details": "Approved. Everything looks good."
    }
    print(f"Admin reviewed reservation: {reservation_data}")
    print(f"Admin response: {admin_response}")
    return {"admin_response": admin_response, "graph_state": "admin_done"}


def mcp_node(state: ReservationState):
    print("--- MCP Server Node ---")
    reservation_data = state["reservation_data"]
    admin_response = state["admin_response"]

    if admin_response["status"] == "confirmed":
        print(f"Logging reservation to MCP server: {reservation_data}")
        log_response = "Successfully logged reservation."
    else:
        print(f"Reservation rejected by admin: {admin_response['details']}")
        log_response = "Reservation was rejected by the administrator."

    return {"graph_state": "mcp_done", "log": log_response}


# --- Graph Logic ---
builder = StateGraph(ReservationState)

# Add nodes
builder.add_node("chatbot", chatbot_node)
builder.add_node("admin_agent", admin_agent_node)
builder.add_node("mcp_server", mcp_node)

# Define edges
builder.add_edge(START, "chatbot")  # Chatbot starts the workflow
builder.add_edge("chatbot", "admin_agent")  # After chatbot, go to admin
builder.add_edge("admin_agent", "mcp_server")  # Admin decision -> MCP
builder.add_edge("mcp_server", END)  # End of the workflow

# Compile the graph
graph = builder.compile()

