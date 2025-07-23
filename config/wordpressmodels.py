from dataclasses import dataclass


@dataclass
class OrderDetails:
    """Ticket Order Details from the Wordpress API."""

    ticket_id: int
    order_id: str = "N/A"
    order_status: str = "N/A"
    customer_name: str = "N/A"
    email: str = "N/A"
    phone: str = "N/A"
    payment_method: str = "N/A"
    total: str = "N/A"
    items: str = "N/A"
    customer_notes: str = "無"


@dataclass
class NewTicketPayload:
    """New Ticket Payload from Webhook Requests."""

    ticket_id: int
    channel_name: str
    ticket_title: str
    sender: str
    ticket_message: str

