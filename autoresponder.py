import logging
import random

# Local Imports:
from database_manager import DatabaseManager


class Autoresponder:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

        self.logger = logging.getLogger("bot.autoresponder")

    async def add(self, key: str, response: str):
        """

        Parameters
        ----------
        key : str
            The autoresponder key to add to.
        response : str
            The respond to add to the key.

        """
        async with await self.db_manager.get_connection("autoresponses") as db:
            key = key.lower()
            await db.execute(
                "INSERT INTO autoresponses (key, response) VALUES (?, ?)",
                (key, response),
            )
            await db.commit()
        self.logger.info(f"Added autoresponse to key '{key}'")

    async def remove(self, key: str, response: str = None):
        key = key.lower()
        async with await self.db_manager.get_connection("autoresponses") as db:
            if response is None:
                # Delete all responses for the key
                await db.execute(
                    "DELETE FROM autoresponses WHERE key = ?", (key,)
                )
                self.logger.info(f"Removed all responses for key '{key}'")
            else:
                # Delete specific response for the key
                await db.execute(
                    "DELETE FROM autoresponses WHERE key = ? AND response = ?",
                    (key, response),
                )
                self.logger.info(
                    f"Removed response '{response}' for key '{key}'"
                )
            await db.commit()

    async def remove_by_id(self, entry_id: int):
        async with await self.db_manager.get_connection("autoresponses") as db:
            await db.execute(
                "DELETE FROM autoresponses WHERE id = ?", (entry_id,)
            )
            await db.commit()
        self.logger.info(f"Removed response with id '{entry_id}'")

    async def get_random_response_from_message(
        self, content: str
    ) -> str | None:
        content = content.lower()

        async with await self.db_manager.get_connection("autoresponses") as db:
            async with db.execute(
                "SELECT DISTINCT key FROM autoresponses"
            ) as cursor:
                keys = [row[0] for row in await cursor.fetchall()]

        # Find the first matching key based on its position in the message
        matching_keys = [
            (key, content.find(key)) for key in keys if key in content
        ]
        matching_keys = [pair for pair in matching_keys if pair[1] != -1]

        if not matching_keys:
            return None

        # Choose the key that appears first in the message
        matching_keys.sort(key=lambda pair: pair[1])
        chosen_key = matching_keys[0][0]
        self.logger.debug(f"Chose key '{chosen_key}' from message '{content}'")

        # Now fetch only responses for that key
        async with await self.db_manager.get_connection("autoresponses") as db:
            async with db.execute(
                "SELECT response FROM autoresponses WHERE key = ?",
                (chosen_key,),
            ) as cursor:
                responses = [row[0] for row in await cursor.fetchall()]

        if not responses:
            return None

        return random.choice(responses)

    async def list_responses_for_key(self, key: str) -> list[str]:
        key = key.lower()
        async with await self.db_manager.get_connection("autoresponses") as db:
            async with db.execute(
                "SELECT id, response FROM autoresponses WHERE key = ?", (key,)
            ) as cursor:
                rows = await cursor.fetchall()
        return rows

    async def init_autoresponses(self):
        """Initializes the autoresponses table if it doesn't exist."""
        async with await self.get_connection("autoresponses") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS autoresponses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    response TEXT NOT NULL
                )
            """)
            await db.commit()
            self.logger.info("✅ Initialized 'autoresponses' table.")
