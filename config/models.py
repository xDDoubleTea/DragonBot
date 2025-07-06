from enum import IntEnum, StrEnum
from typing import List
from dataclasses import dataclass, field


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

    id: int
    trigger: str
    response: str
    kw_type: KeywordType
    guild_id: int
    customer_mention: bool = False
    in_ticket_only: bool = True
    allowed_channel_ids: List[int] = field(default_factory=list)

    def is_allowed_in(self, channel_id: int, is_ticket_channel: bool) -> bool:
        """
        Checks if the keyword is allowed to trigger in a given channel context.
        """
        if self.in_ticket_only and not is_ticket_channel:
            return False
        # If allowed_channel_ids is empty, it means it's allowed in all channels
        # that satisfy the ticket-only rule.
        if not self.allowed_channel_ids:
            return True

        return channel_id in self.allowed_channel_ids


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
