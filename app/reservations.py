import sqlite3
import requests
from time import sleep
from datetime import datetime
from admin_agent import AdminAgent

# Initialize AdminAgent
admin_agent = AdminAgent()

# Endpoint URL for the admin agent
ADMIN_AGENT_URL = "http://127.0.0.1:8000/"

DB_PATH = r"reservations/reservations.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        plate TEXT,
        date TEXT,
        time TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

def get_all_reservations():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, plate, date, time, created_at
        FROM reservations
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows

def save_reservation(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reservations (name, plate, date, time, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["name"],
        data["plate"],
        data["date"],
        data["time"],
        str(datetime.now())
    ))

    conn.commit()
    conn.close()

# def escalate_to_admin(reservation_details):
#     """
#     Sends a reservation request to the admin agent and waits for the admin's confirmation/refusal.
#
#     Args:
#         reservation_details (dict): Reservation details including name, plate, date, and time.
#
#     Returns:
#         dict: Combined response from admin regarding reservation status (confirmed or denied).
#     """
#     try:
#         # Step 1: Send reservation to admin agent
#         post_endpoint = f"{ADMIN_AGENT_URL}/send_reservation"
#         response = requests.post(post_endpoint, json=reservation_details)
#
#         if response.status_code != 200:
#             return {
#                 "error": f"Failed to send reservation to admin agent. "
#                          f"Status code: {response.status_code}, Response: {response.text}"
#             }
#
#         print("Reservation sent to admin agent successfully.")
#         post_response = response.json()
#
#         # Extract key details for retrieving admin's decision
#         name = reservation_details["name"]
#         date = reservation_details["date"]
#         time = reservation_details["time"]
#         plate = reservation_details["plate"]
#
#         # Step 2: Poll admin agent for decision (GET /get_admin_response)
#         get_endpoint = f"{ADMIN_AGENT_URL}/get_admin_response"
#         for _ in range(3):  # Poll up to 3 times
#             sleep(2)  # Short delay (2 seconds) before each request
#             get_response = requests.get(get_endpoint, params={
#                 "name": name,
#                 "date": date,
#                 "time": time,
#                 "plate": plate
#             })
#
#             if get_response.status_code == 200:
#                 admin_response = get_response.json()
#                 print(f"Admin response received: {admin_response}")
#                 return admin_response  # Return the admin's response once available
#             elif get_response.status_code == 404:
#                 print("Still waiting for admin's response...")
#             else:
#                 return {
#                     "error": f"Unexpected error while checking admin response. "
#                              f"Status code: {get_response.status_code}, Response: {get_response.text}"
#                 }
#
#         # If no response after polling, return timeout
#         return {
#             "error": "Admin did not respond. Please try again later."
#         }
#
#     except Exception as e:
#         return {"error": f"An exception occurred: {str(e)}"}

def handle_reservation_chatbot(message, reservation_state):

    msg = message.lower().strip()

    # start reservation
    if "reserve" in msg or "booking" in msg:
        reservation_state["active"] = True
        reservation_state["step"] = "name"
        reservation_state["data"] = {}
        return "Sure! What is your full name?"

    if reservation_state["active"]:
        step = reservation_state["step"]

        if step == "name":
            reservation_state["data"]["name"] = message
            reservation_state["step"] = "plate"
            return "Please provide your license plate number."

        if step == "plate":
            reservation_state["data"]["plate"] = message
            reservation_state["step"] = "date"
            return "What date would you like to reserve? (YYYY-MM-DD)"

        if step == "date":
            reservation_state["data"]["date"] = message
            reservation_state["step"] = "time"
            return "What arrival time? (HH:MM)"

        if step == "time":
            reservation_state["data"]["time"] = message
            reservation_state["active"] = False

            data = reservation_state["data"]

            data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Send reservation to admin agent
            print("Sending reservation data to admin agent...")
            admin_agent.create_admin_request(data)
            admin_response = admin_agent.process_admin_response("approve") #mock admin answer

            save_reservation(data)

            reservation_state["step"] = None
            reservation_state["data"] = {}

            # Handle admin agent response
            if "error" in admin_response:
                return f"Reservation process failed: {admin_response['error']}"
            elif admin_response["status"] == "confirmed":
                return (
                        "Your reservation has been **confirmed** by the administrator!\n\n" +
                        admin_response["details"]
                )
            elif admin_response["status"] == "rejected":
                return (
                        "Your reservation was **not approved** by the administrator.\n\n" +
                        admin_response["details"]
                )

            # Default case if response does not match expected format
            return "Received an unexpected response from the administrator."
    return None

