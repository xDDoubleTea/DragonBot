"""
This file contains custom exceptions for the DragonBot application.
"""


class ChannelCreationFail(Exception):
    """
    Raised when the bot fails to create a new ticket channel.

    This can happen due to a variety of reasons, such as:
    - The bot lacks the 'Manage Channels' permission.
    - The server has reached its maximum channel limit (500).
    """

    def __init__(self, message="Failed to create ticket channel."):
        self.message = message
        super().__init__(self.message)


class ChannelNotTicket(TypeError):
    """
    Raised when the channel is not a ticket
    """

    def __init__(self, message="This channel is not a ticket channel."):
        self.message = message
        super().__init__(self.message)


class TicketNotFound(TypeError):
    def __init__(self, message="Ticket not found."):
        self.message = message
        super().__init__(self.message)


class PanelUnique(Exception):
    def __init__(
        self,
        message="There should only be only one ticket open messages in every guild.",
    ):
        self.message = message
        super().__init__(self.message)


class NoParticipants(Exception):
    def __init__(self, message="There are no participants for this ticket."):
        self.message = message
        super().__init__(self.message)
