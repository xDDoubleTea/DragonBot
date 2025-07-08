from enum import IntEnum, StrEnum
from typing import List, Optional, Dict
from dataclasses import dataclass, field

from discord import Client, Color, Guild, TextChannel

__all__ = [
    "TicketStatus",
    "Ticket",
    "CloseMessageType",
    "KeywordType",
    "TicketType",
    "AddRemove",
    "BooleanToStr",
    "StrToBoolean",
    "PaginationViewButtonLayouts",
    "BasePaginationMetaData",
    "KeywordPaginationMetaData",
    "Keyword",
]


class TicketStatus(IntEnum):
    """
    Represents the status of a ticket
    """

    OPEN = 0
    IN_PROGRESS = 1
    RESOLVED = 2
    CLOSED = 3


ticket_status_name_chinese = {
    TicketStatus.OPEN: "待處理",
    TicketStatus.IN_PROGRESS: "處理中",
    TicketStatus.RESOLVED: "處理完畢",
    TicketStatus.CLOSED: "已關閉",
}


class CloseMessageType(IntEnum):
    """
    Represents the close buttons type attached to the close message.
    """

    CLOSE_TOGGLE = 0
    CLOSE = 1
    AFTER_CLOSE = 2


def BooleanToStr(value: bool) -> str:
    """
    Converts a boolean value to a string representation.
    """
    return "是" if value else "否"


def StrToBoolean(value: str) -> Optional[bool]:
    """
    Converts a string representation of a boolean to a boolean value.
    Returns None if the value is not "是" or "否".
    """
    return True if value == "是" else False if value == "否" else None


class AddRemove(StrEnum):
    """
    Represents the action of adding or removing a keyword.
    """

    ADD = "加入"
    REMOVE = "移除"


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


class PaginationViewButtonLayouts(IntEnum):
    FIRST_PAGE = 0
    PREV_PAGE = 1
    PAGE_DISPLAY = 2
    NEXT_PAGE = 3
    LAST_PAGE = 4


@dataclass
class BasePaginationMetaData:
    """The metadata used by the pagination view."""

    guild_name: str
    guild_id: int
    channel_name: str
    channel_id: int
    user_name: str
    user_id: int

    # Because we have to pass client to the embed_utils
    client: Client
    theme_color: Optional[Color]


@dataclass
class KeywordPaginationMetaData(BasePaginationMetaData):
    guild: Guild
    keyword_channel_obj: Dict[str, List[TextChannel]]


@dataclass
class Keyword:
    """Represents a row in the keywords table"""

    id: int
    trigger: str
    response: str
    kw_type: KeywordType
    guild_id: int
    mention_participants: bool = False
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

        return channel_id in self.allowed_channel_ids or is_ticket_channel


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
    ticket_type: TicketType
    guild_id: int
    close_msg_type: CloseMessageType
