from enum import IntEnum, StrEnum, Enum
from typing import List, Optional, Dict, Set
from dataclasses import dataclass, field
from datetime import datetime
from discord import Client, Color, Guild, TextChannel

__all__ = [
    "TicketStatus",
    "Ticket",
    "CloseMessageType",
    "KeywordType",
    "TicketType",
    "AddRemove",
    "boolean_to_str",
    "str_to_boolean",
    "PaginationViewButtonLayouts",
    "BasePaginationMetaData",
    "KeywordPaginationMetaData",
    "Keyword",
    "RoleRequestStatus",
    "RoleRequestChannelType",
    "RoleRequestData",
    "PanelMessageData",
    "FeedbackStats",
]


class TicketStatus(Enum):
    """
    Represents the status of a ticket
    """

    OPEN = (0, "待處理")
    IN_PROGRESS = (1, "處理中")
    RESOLVED = (2, "處理完畢")
    CLOSED = (3, "已關閉")

    def __init__(self, id: int, string_repr: str):
        self.id = id
        self.string_repr = string_repr

    @classmethod
    def from_id(cls, status_id: int) -> "TicketStatus":
        """
        Looks up an enum member by its integer ID.
        Returns the TicketStatus member or None if the ID is not found.
        """
        # This is an efficient reverse lookup.
        # We iterate through all members of the class (`cls`) and check their `id` attribute.
        for member in cls:
            if member.id == status_id:
                return member
        return cls.OPEN  # Defaults to OPEN if no match is found, for safety.


class RoleRequestStatus(Enum):
    NOT_SET = (0, "未設置申請以及審核頻道")
    ONLY_REQUEST = (1, "未設置申請頻道")
    ONLY_APPROVE = (2, "未設置審核頻道")
    NO_ROLE = (3, "沒有加入可申請身份組")
    SET = (4, "已啟用")

    def __init__(self, id: int, string_repr: str):
        self.id = id
        self.string_repr = string_repr


class RoleRequestChannelType(Enum):
    REQUEST = (0, "request_channel_id")
    APPROVAL = (1, "approval_channel_id")

    def __init__(self, db_id: int, column_name: str):
        self.db_id = db_id
        self.column_name = column_name


class CloseMessageType(IntEnum):
    """
    Represents the close buttons type attached to the close message.
    """

    CLOSE_TOGGLE = 0
    CLOSE = 1
    AFTER_CLOSE = 2


def boolean_to_str(value: bool) -> str:
    """
    Converts a boolean value to a string representation.
    :param value:
    :return:
    """
    return "是" if value else "否"


def str_to_boolean(value: str) -> Optional[bool]:
    """
    Converts a string representation of a boolean to a boolean value.
    Returns None if the value is not "是" or "否".
    :param value:
    :return:
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
    Represents the type of keyword.
    """

    MATCH_START = "句首"
    IS_SUBSTR = "句中"


class TicketType(StrEnum):
    """
    Represents the type of ticket.
    """

    PURCHASE = "代購"
    GUILD = "群組"
    CUSTOM_PURCHASE = "自定義代購"
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
    participants: Set[int] = field(default_factory=set)


@dataclass
class RoleRequestData:
    guild_id: int
    request_channel_id: Optional[int]
    approval_channel_id: Optional[int]
    requestable_roles: Set[int]


@dataclass
class PanelMessageData:
    """
    Represents the data for a panel message.
    """

    guild_id: int
    channel_id: int
    message_id: int


@dataclass
class FeedbackEntry:
    ticket_id: int
    guild_id: int
    customer_id: int
    rating: int
    created_at: datetime | None = None
    feedback_messages: str = ""


@dataclass
class FeedbackStats:
    average_rating: float
    total_ratings: int
    five_star_ratings: int
    four_star_ratings: int
    three_star_ratings: int
    two_star_ratings: int
    one_star_ratings: int


@dataclass
class FeedbackLeaderboardEntry:
    """Represents a single user's entry on the feedback leaderboard."""

    customer_id: int
    feedback_count: int
    average_rating: float


class FeedbackPromptMessageType(Enum):
    RATING = (0, "評價")
    SELECT = (1, "評語")

    def __init__(self, db_id: int, string_repr: str):
        self.db_id = db_id
        self.string_repr = string_repr


@dataclass
class FeedbackPrompt:
    user_id: int
    guild_id: int
    ticket_id: int
    message_id: int
    channel_id: int
    message_type: FeedbackPromptMessageType
