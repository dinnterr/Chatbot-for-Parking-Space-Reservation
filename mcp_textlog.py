from fastmcp import FastMCP
from datetime import datetime
from dotenv import load_dotenv
import threading
import re
import os


load_dotenv()
# Retrieve the API key from environment variables
MCP_API_KEY = os.getenv("MCP_API_KEY")
if not MCP_API_KEY:
    raise ValueError("Missing API key! Please set MCP_API_KEY in .env.")

# Create an instance of FastMCP
mcp = FastMCP("SecureReservationLogger")

# Lock for thread-safe file writes
file_lock = threading.Lock()

# File to store reservation logs
LOG_FILE = "reservations.txt"

# Regular expressions to validate input
NAME_REGEX = r"^[a-zA-Z\s]+$"  # Allow names with letters and spaces
CAR_NUMBER_REGEX = r"^[A-Z0-9-]+$"  # Uppercase letters, numbers, hyphens
PERIOD_REGEX = r"^\d{4}-\d{2}-\d{2}\sto\s\d{4}-\d{2}-\d{2}$"  # Format: YYYY-MM-DD to YYYY-MM-DD


def validate_inputs(name, car_number, reservation_period):
    """
    Validate reservation inputs to prevent malformed or malicious data.
    Raise ValueError if validation fails.
    """
    if not re.match(NAME_REGEX, name):
        raise ValueError(f"Invalid name: {name}. Names must only contain letters and spaces.")
    if not re.match(CAR_NUMBER_REGEX, car_number):
        raise ValueError(f"Invalid car number: {car_number}. Must contain uppercase letters, numbers, and hyphens.")
    if not re.match(PERIOD_REGEX, reservation_period):
        raise ValueError(f"Invalid reservation period: {reservation_period}. Must match 'YYYY-MM-DD to YYYY-MM-DD'.")


@mcp.tool()
def log_reservation(reservation: dict, api_key: str) -> str:
    """
    Securely log a reservation to the reservation log.

    Args:
        reservation (dict): The reservation details as a dictionary:
            {
                'name': str,
                'plate': str,
                'date': str,
                'time': str,
                'created_at': str
            }
        api_key (str): The API key for authorization.

    Returns:
        str: Success message or error message.
    """
    # Security check: Validate API key
    if api_key != MCP_API_KEY:
        return "Unauthorized access. Invalid API key."

    try:
        # Extract and format reservation details
        name = reservation.get("name", "").strip()
        car_number = reservation.get("plate", "").strip()
        date = reservation.get("date", "").strip()
        time = reservation.get("time", "").strip()
        created_at = reservation.get("created_at", "").strip()

        reservation_period = f"{date} {time}"

        # Validate inputs
        validate_inputs(name, car_number, f"{date} to {date}")

        # Construct the log entry
        entry = f"{name} | {car_number} | {reservation_period} | {created_at}\n"

        # Securely write the log entry to the file
        with file_lock:
            with open(LOG_FILE, "a", encoding="utf-8") as file:
                file.write(entry)

        return f"Successfully logged reservation for: {name}, {car_number}"

    except ValueError as ve:
        # Handle validation errors
        return f"Input validation error: {ve}"
    except Exception as e:
        # Handle general unexpected errors
        return f"Failed to log reservation: {str(e)}"


if __name__ == "__main__":
    # Ensure the log file exists with a header
    with file_lock:
        try:
            with open(LOG_FILE, "x", encoding="utf-8") as file:
                file.write("Name | Car Number | Reservation Period | Approval Time\n")
        except FileExistsError:
            pass  # File already exists

    # Run the MCP server
    mcp.run(transport="stdio")