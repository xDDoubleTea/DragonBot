from discord.ext import commands
from typing import Dict, Optional, Set

from config.models import RoleRequestChannelType, RoleRequestData
from db.database_manager import AsyncDatabaseManager


class NoRequestableRolestoRemove(Exception):
    def __init__(self, message: str = "沒有可以移除的身份組") -> None:
        self.message = message
        super().__init__()


class RoleAlreadyNotRequestable(Exception):
    def __init__(self, message: str = "身份組不是可申請的身份組") -> None:
        self.message = message
        super().__init__(message)


class RoleRequestManager:
    def __init__(
        self, bot: commands.Bot, database_manager: AsyncDatabaseManager
    ) -> None:
        self.bot = bot
        self.database_manager = database_manager
        self.role_request_table_name = "role_request"
        self.guild_requestable_roles_table_name = "guild_requestable_roles"
        self.role_request_cache: Dict[int, RoleRequestData] = dict()
        # key: guild_id, value: RoleRequestData dataclass

    async def init_cache(self):
        role_request_data = await self.database_manager.select(
            table_name=self.role_request_table_name
        )
        if not role_request_data:
            return
        assert isinstance(role_request_data, list)
        for data in role_request_data:
            print(
                f"Found guild ID {data['guild_id']} in table {self.role_request_table_name}, adding to role_request_cache."
            )
            self.role_request_cache[data["guild_id"]] = RoleRequestData(
                guild_id=data["guild_id"],
                request_channel_id=data["request_channel_id"],
                approval_channel_id=data["approval_channel_id"],
                requestable_roles=await self.get_requestable_roles(
                    guild_id=data["guild_id"]
                ),
            )

    async def _get_or_create_config(self, guild_id: int) -> RoleRequestData:
        """
        The single source of truth for getting a guild's config.
        Checks cache first, then DB. If not found, creates a new entry in both.
        """
        if config := self.role_request_cache.get(guild_id):
            return config

        # Not in cache, check DB
        config_data = await self.database_manager.select(
            table_name=self.role_request_table_name,
            criteria={"guild_id": guild_id},
            fetch_one=True,
        )

        if config_data:
            # Found in DB, populate cache
            roles_data = await self.database_manager.select(
                table_name=self.guild_requestable_roles_table_name,
                criteria={"guild_id": guild_id},
            )
            requestable_roles = (
                {role["role_id"] for role in roles_data} if roles_data else set()
            )

            config = RoleRequestData(
                guild_id=guild_id,
                request_channel_id=config_data["request_channel_id"],
                approval_channel_id=config_data["approval_channel_id"],
                requestable_roles=requestable_roles,
            )
        else:
            # Not in DB either, create a new blank config
            await self.database_manager.insert(
                table_name=self.role_request_table_name,
                data={"guild_id": guild_id},
                returning_col="guild_id",
            )
            config = RoleRequestData(
                guild_id=guild_id,
                request_channel_id=None,
                approval_channel_id=None,
                requestable_roles=set(),
            )

        self.role_request_cache[guild_id] = config
        return config

    async def get_typed_channel_id(
        self, guild_id: int, cnl_type: RoleRequestChannelType
    ) -> Optional[int]:
        config = await self._get_or_create_config(guild_id=guild_id)
        return getattr(config, f"{cnl_type.column_name}", None)

    async def set_typed_channel_id(
        self, guild_id: int, cnl_type: RoleRequestChannelType, channel_id: int
    ) -> Optional[int]:
        config = await self._get_or_create_config(guild_id=guild_id)
        await self.database_manager.update(
            table_name=self.role_request_table_name,
            data={cnl_type.column_name: channel_id},
            criteria={"guild_id": guild_id},
        )
        setattr(config, cnl_type.column_name, channel_id)

    async def role_requestable(self, guild_id: int, role_id: int) -> bool:
        return role_id in await self.get_requestable_roles(guild_id=guild_id)

    async def add_requestable_role(self, guild_id: int, role_id: int) -> int | None:
        """Adds a role to the requestable list for a guild."""
        config = await self._get_or_create_config(guild_id)
        if role_id in config.requestable_roles:
            # Role already exists, do nothing
            return

        await self.database_manager.insert(
            table_name=self.guild_requestable_roles_table_name,
            data={"guild_id": guild_id, "role_id": role_id},
            returning_col="guild_id",
        )
        # Update cache
        config.requestable_roles.add(role_id)

    async def remove_requestable_role(self, guild_id: int, role_id: int):
        config = await self._get_or_create_config(guild_id=guild_id)
        # If the role is not requestable, we raise an exception
        if not config.requestable_roles:
            raise NoRequestableRolestoRemove()
        if role_id not in config.requestable_roles:
            raise RoleAlreadyNotRequestable()
        # If the role is requestable, we remove it from the cache and database
        await self.database_manager.delete(
            table_name=self.guild_requestable_roles_table_name,
            criteria={"guild_id": guild_id, "role_id": role_id},
        )
        # Remove from cache
        config.requestable_roles.remove(role_id)

    async def get_requestable_roles(self, guild_id: int) -> Set[int]:
        config = await self._get_or_create_config(guild_id=guild_id)
        return config.requestable_roles

    async def is_system_configured(self, guild_id: int) -> bool:
        config = await self._get_or_create_config(guild_id=guild_id)
        return bool(config.request_channel_id and config.approval_channel_id)
