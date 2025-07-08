from discord import app_commands, Interaction
from discord.app_commands import Choice
from enum import Enum
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
        # The 'value' from Discord will be the enum member's name (e.g., "CLOSE_PROMPT").
        # We find the corresponding enum member and return it.
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
        # We iterate through all members of our enum.
        for member in self._enum_type:
            # For each choice, we set:
            # - name: The user-friendly string (member.value).
            # - value: The programmatic key (member.name) that gets sent back to us.
            choice = Choice(name=str(member.value), value=member.name)
            choices.append(choice)

        # We can also add some basic filtering for a better UX.
        # If the user starts typing, we only show choices that match.
        if value and isinstance(value, str):
            return [c for c in choices if value.lower() in c.name.lower()][:25]
        else:
            return choices[:25]  # Discord limits choices to 25

    def __init__(self, enum_type: Type[Enum]):
        self._enum_type = enum_type
        super().__init__()
