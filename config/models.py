from enum import IntEnum

__all__ = ["TicketStatus"]


class TicketStatus(IntEnum):
    """
    Represents the status of a ticket
    """

    OPEN = 0
    IN_PROGRESS = 1
    RESOLVED = 2
    CLOSED = 3
