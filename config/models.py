from enum import IntEnum, StrEnum
from dataclasses import dataclass


__all__ = ["TicketStatus", "Ticket", "CloseMessageType", "KeywordType", "TicketType"]


class TicketStatus(IntEnum):
    """
    Represents the status of a ticket
    """

    OPEN = 0
    IN_PROGRESS = 1
    RESOLVED = 2
    CLOSED = 3


class CloseMessageType(IntEnum):
    """
    Represents the close buttons type attached to the close message.
    """

    CLOSE_TOGGLE = 0
    CLOSE = 1
    AFTER_CLOSE = 2


class KeywordType(StrEnum):
    """
    Represents the type of a keyword.
    """

    MATCH_START = "句首"
    IS_SUBSTR = "句中"


class TicketType(StrEnum):
    """
    Represents the type of a ticket.
    """

    PURCHASE = "代購"
    GUILD = "群組"
    OTHERS = "其他"


@dataclass
class Keyword:
    """Represents a row in the keywords table"""

    word: str
    response: str
    kw_type: KeywordType
    in_ticket_only: bool


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
    close_msg_type: CloseMessageType
