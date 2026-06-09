import sqlite3
from datetime import datetime

DB_PATH = r"reservations/reservations.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (сссссирлдрукасоуоавтпдрпмп
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

def handle_reservation(message, reservation_state):

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

            save_reservation(data)

            reservation_state["step"] = None
            reservation_state["data"] = {}

            return (
                "Reservation confirmed!\n\n"
                f"Name: {data['name']}\n"
                f"Plate: {data['plate']}\n"
                f"Date: {data['date']}\n"
                f"Time: {data['time']}"
            )

    return None

