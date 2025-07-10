from typing import Any
import discord


async def get_or_fetch(
    container: Any,
    obj_id: int,
    get_method_name: str,
    fetch_method_name: str,
) -> Any:
    """
    A generic utility to get a Discord object from cache or fetch it from the API.
    Returns the resolved object, or None if it's not found.
    """
    try:
        if (obj := getattr(container, get_method_name)(obj_id)) is not None:
            return obj
    except AttributeError:
        pass

    try:
        return await getattr(container, fetch_method_name)(obj_id)
    except (discord.errors.NotFound, discord.errors.HTTPException):
        return None
    except AttributeError:
        return None
