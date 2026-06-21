from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from datetime import datetime
app = FastAPI()

# Model to define reservation details
class ReservationRequest(BaseModel):
    name: str
    plate: str
    date: str
    time: str
    created_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Storage to simulate admin responses in this example
admin_reservations: Dict[str, Dict[str, str]] = {}

@app.post("/send_reservation")
async def send_reservation(request: ReservationRequest):
    """
    This endpoint receives reservation requests and forwards them to the administrator.
    Each reservation is uniquely stored based on a composite key generated from name, date, and time.
    """
    # Create a unique composite key for the reservation (based on name, plate, date, and time)
    reservation_key = f"{request.name}_{request.date}_{request.time}_{request.plate}"

    # Format the reservation details for the admin
    reservation_summary = (
        f"Name: {request.name}\n"
        f"Plate: {request.plate}\n"
        f"{request.date} at {request.time}\n"
        f"Created: {request.created_at}\n"
        f"----------------------\n"
    )

    # Store the reservation in the admin_reservations dictionary
    admin_reservations[reservation_key] = {
        "status": "pending",
        "details": reservation_summary
    }

    # Simulate sending reservation details to the admin
    print("\nReservation sent to Admin:\n")
    print(reservation_summary)

    return {
        "message": "Reservation request sent to the administrator.",
        "status": "pending",
        "details": reservation_summary
    }


@app.get("/get_admin_response")
async def get_admin_response(name: str, date: str, time: str, plate: str):
    """
    This endpoint gets the admin decision for a specific reservation based on the composite key.
    """
    # Generate the composite key from the query parameters
    reservation_key = f"{name}_{date}_{time}_{plate}"

    # Retrieve the reservation details and status
    reservation = admin_reservations.get(reservation_key)
    if not reservation:
        raise HTTPException(status_code=404, detail="No reservation found with the given details.")

    # Prompt admin for decision dynamically
    decision = input(
        f"Please provide a status for reservation {reservation_key} ('confirmed' or 'rejected' and any details): ").strip().lower()

    # Update the reservation status based on admin's decision
    admin_reservations[reservation_key]["status"] = decision
    print(f"Provided decision for {reservation_key} : {decision}.")

    # Return the reservation details and updated status
    return {
        "status": admin_reservations[reservation_key]["status"],
        "details": admin_reservations[reservation_key]["details"],
    }