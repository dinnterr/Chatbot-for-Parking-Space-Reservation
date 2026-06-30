from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from langchain_core.messages import HumanMessage

from chatbot import llm, retriever

from app.guardrails import guardrail_check

from app.reservations import (
    handle_reservation_chatbot,
    get_all_reservations,
    save_reservation
)

from admin_agent import AdminAgent
from mcp_textlog import log_reservation

import os
from dotenv import load_dotenv

load_dotenv()

MCP_API_KEY = os.getenv("MCP_API_KEY")


class ParkingState(TypedDict):

    message: str

    response: Optional[str]

    route: Optional[str]

    reservation_state: dict

    reservation_complete: bool

    reservation_data: dict

    admin_result: dict

    knowledge: str


def input_guardrail_node(state: ParkingState):

    if guardrail_check(state["message"]):

        return {

            "route": "blocked",

            "response":
                "Your message was blocked due to safety policy."

        }

    return {

        "route": "ok"

    }

def router_node(state: ParkingState):

    reservation_state = state["reservation_state"]

    message = state["message"].lower().strip()

    if reservation_state.get("active"):

        return {

            "route": "reservation"

        }

    if message.startswith("reserve"):

        return {

            "route": "reservation"

        }

    if message in (

            "show reservations",

            "list reservations",

            "all reservations"

    ):

        return {

            "route": "database"

        }

    return {

        "route": "rag"

    }

def reservation_agent_node(state: ParkingState):

    response = handle_reservation_chatbot(

        state["message"],

        state["reservation_state"],

        auto_process=False

    )

    completed = (
            response == "__LANGGRAPH_READY__"
            or (
                    not state["reservation_state"].get("active")
                    and bool(state["reservation_state"].get("data"))
            )
    )

    return {

        "response": response,

        "reservation_complete": completed,

        "reservation_data":
            state["reservation_state"].get(
                "data",
                {}
            )

    }

def reservation_router(state: ParkingState):

    if state["reservation_complete"]:

        return "admin"

    return "finish"


def show_reservations_node(state: ParkingState):

    rows = get_all_reservations()

    if not rows:

        return {

            "response":
                "No reservations found."

        }

    result = "All reservations:\n\n"

    for row in rows:

        name, plate, date, time, created = row

        result += (

            f"Name: {name}\n"

            f"Plate: {plate}\n"

            f"{date} at {time}\n"

            f"Created: {created}\n"

            "--------------------------\n"

        )

    return {

        "response": result

    }

def admin_agent_node(state: ParkingState):

    admin = AdminAgent()

    reservation = state["reservation_data"]

    # Generate request for administrator
    request = admin.create_admin_request(
        reservation
    )

    print("\n")
    print("=" * 60)
    print("ADMIN REQUEST")
    print("=" * 60)
    print(request)
    print("=" * 60)

    admin_reply = input(
        "\nAdministrator response: "
    )

    result = admin.process_admin_response(
        admin_reply
    )

    return {

        "admin_result": result

    }

def admin_router(state: ParkingState):

    result = state["admin_result"]

    if result["status"] == "confirmed":

        return "confirmed"

    if result["status"] == "rejected":

        return "rejected"

    return "error"

def confirmed_node(state: ParkingState):

    reservation = state["reservation_data"]

    save_reservation(
        reservation
    )

    log_reservation(

        reservation,

        MCP_API_KEY

    )

    details = state["admin_result"].get(
        "details",
        ""
    )

    return {

        "response":
            "Your reservation has been confirmed.\n\n"
            + details

    }


def rejected_node(state: ParkingState):


    details = state["admin_result"].get(

        "details",

        ""

    )

    return {

        "response":
            "Your reservation was rejected.\n\n"
            + details

    }

def admin_error_node(state: ParkingState):

    return {

        "response":
            "Unable to process administrator response."

    }


# RETRIEVAL
def retrieval_node(state: ParkingState):

    docs = retriever.invoke(

        state["message"]

    )

    knowledge = "\n\n".join(

        doc.page_content

        for doc in docs

    )

    return {

        "knowledge": knowledge

    }


# RAG

def rag_node(state: ParkingState):

    prompt = f"""
You are a parking assistant chatbot.

Question:
{state["message"]}

Knowledge:
{state["knowledge"]}
"""

    response = llm.invoke(

        [HumanMessage(content=prompt)]

    )

    text = response.content

    if "<|assistant|>" in text:

        text = text.split(

            "<|assistant|>"

        )[-1].strip()

    return {

        "response": text

    }


# OUTPUT GUARDRAIL

def output_guardrail_node(state: ParkingState):

    if guardrail_check(

        state["response"]

    ):

        return {

            "response":
                "Response blocked due to safety policy."

        }

    return {}


# GRAPH
builder = StateGraph(ParkingState)

builder.add_node(
    "input_guardrail",
    input_guardrail_node
)

builder.add_node(
    "router",
    router_node
)

builder.add_node(
    "reservation_agent",
    reservation_agent_node
)

builder.add_node(
    "admin_agent",
    admin_agent_node
)

builder.add_node(
    "confirmed",
    confirmed_node
)

builder.add_node(
    "rejected",
    rejected_node
)

builder.add_node(
    "admin_error",
    admin_error_node
)

builder.add_node(
    "database",
    show_reservations_node
)

builder.add_node(
    "retrieval",
    retrieval_node
)

builder.add_node(
    "rag",
    rag_node
)

builder.add_node(
    "output_guardrail",
    output_guardrail_node
)

builder.add_edge(
    START,
    "input_guardrail"
)

builder.add_edge(
    "input_guardrail",
    "router"
)

builder.add_conditional_edges(

    "router",

    lambda s: s["route"],

    {

        "reservation":
            "reservation_agent",

        "database":
            "database",

        "rag":
            "retrieval",

        "blocked":
            END

    }

)

builder.add_conditional_edges(

    "reservation_agent",

    reservation_router,

    {

        "admin":
            "admin_agent",

        "finish":
            END

    }

)

builder.add_conditional_edges(

    "admin_agent",

    admin_router,

    {

        "confirmed":
            "confirmed",

        "rejected":
            "rejected",

        "error":
            "admin_error"

    }

)

builder.add_edge(
    "confirmed",
    "output_guardrail"
)

builder.add_edge(
    "rejected",
    "output_guardrail"
)

builder.add_edge(
    "admin_error",
    "output_guardrail"
)

builder.add_edge(
    "retrieval",
    "rag"
)

builder.add_edge(
    "rag",
    "output_guardrail"
)

builder.add_edge(
    "database",
    END
)

builder.add_edge(
    "output_guardrail",
    END)

parking_graph = builder.compile()


# ENTRY POINT

def process_message(
    message: str,
    reservation_state: dict
):

    state = {

        "message": message,

        "response": None,

        "route": None,

        "reservation_state": reservation_state,

        "reservation_complete": False,

        "reservation_data": {},

        "admin_result": {},

        "knowledge": ""

    }

    result = parking_graph.invoke(
        state
    )

    return result["response"]