from enum import IntEnum
from dataclasses import dataclass

__all__ = ["TicketStatus", "Ticket"]


class TicketStatus(IntEnum):
    """
    Represents the status of a ticket
    """

    OPEN = 0
    IN_PROGRESS = 1
    RESOLVED = 2
    CLOSED = 3


@dataclass
class Ticket:
    """
    Represents a row in the tickets table
    """

    db_id: int
    channel_id: int
    auto_timeout: int
    timed_out: int
    close_msg_id: int
    status: TicketStatus
    guild_id: int
