from discord import app_commands, Interaction
from discord.app_commands import Choice
from enum import Enum
from config.canned_response import ReplyKeys
from config.models import CurrencyIndex
from typing import Any, List, Type, Union


class CannedResponseTransformer(app_commands.Transformer):
    """
    A custom transformer to display an Enum's user-friendly value in Discord's UI,
    while using its programmatic name in the bot's code.
    """

    async def transform(self, interaction: Interaction, value: Any) -> Enum:
        """
        This is called when transforming the value from the user's input.
        In the case of an enum, this is what converts the string value from Discord
        back into the enum member.
        """
        enum_member = self._enum_type[value]
        return enum_member

    async def autocomplete(
        self, interaction: Interaction, value: Union[str, int, float]
    ) -> List[Choice]:
        """
        This is the core of the solution. It defines what choices are displayed
        to the user in the autocomplete dropdown.
        """
        choices = []
        for member in self._enum_type:
            choice = Choice(name=str(member.value), value=member.name)
            choices.append(choice)

        if value and isinstance(value, str):
            return [c for c in choices if value.lower() in c.name.lower()][:25]
        else:
            return choices[:25]  # Discord limits choices to 25

    def __init__(self, enum_type: Type[ReplyKeys]):
        self._enum_type = enum_type
        super().__init__()


class CurrencyTransformer(app_commands.Transformer):
    """
    A custom transformer to display an Enum's user-friendly value in Discord's UI,
    while using its programmatic name in the bot's code.
    """

    async def transform(self, interaction: Interaction, value: Any) -> Enum:
        """
        This is called when transforming the value from the user's input.
        In the case of an enum, this is what converts the string value from Discord
        back into the enum member.
        """
        enum_member = self._enum_type[value]
        return enum_member

    async def autocomplete(
        self, interaction: Interaction, value: Union[str, int, float]
    ) -> List[Choice]:
        """
        This is the core of the solution. It defines what choices are displayed
        to the user in the autocomplete dropdown.
        """
        choices = []
        for member in self._enum_type:
            choice = Choice(name=str(member.string_repr), value=member.name)
            choices.append(choice)

        # If the user starts typing, we only show choices that match.
        if value and isinstance(value, str):
            return [c for c in choices if value.lower() in c.name.lower()][:25]
        else:
            return choices[:25]  # Discord limits choices to 25

    def __init__(self, enum_type: Type[CurrencyIndex]):
        self._enum_type = enum_type
        super().__init__()
