import aiosqlite
import logging
from pathlib import Path


class DatabaseManager:
    def __init__(self, base_dir: str = "data"):
        self.logger = logging.getLogger("bot.database")
        self.base_path = Path(base_dir)
        self.base_path.mkdir(exist_ok=True)
        self.logger.info(
            "DatabaseManager initialized with base path '%s'", self.base_path
        )

        self.db_paths = {"autoresponses": self.base_path / "autoresponses.db"}

    def get_path(self, name: str) -> Path:
        """
        Returns the path of the database.

        Parameters
        ----------
        name : str
            The name of the database to retrieve.

        Returns
        -------
        Path
            The path to the database.
        """
        return self.db_paths.get(name)

    async def get_connection(self, name: str) -> aiosqlite.Connection:
        """
        Gets the connection to the database.

        Parameters
        ----------
        name : str
            The name of the database to connect to.

        Returns
        -------
        aiosqlite.Connection
            The connection to the database.

        """
        path = self.get_path(name)
        if not path:
            self.logger.error("Requested unknown database: '%s'", name)
            raise ValueError(f"No database found for '{name}'")
        try:
            self.logger.debug("Connected to database: %s", path)
            conn = aiosqlite.connect(path)
            self.logger.debug(
                "Created DB connection %s for '%s'", id(conn), name
            )
            return conn
        except Exception as e:
            self.logger.exception(
                "Failed to connect to database '%s': %s", name, e
            )
            raise

    async def init_autoresponses(self):
        """Initializes the autoresponses database."""
        async with await self.get_connection("autoresponses") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS autoresponses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    response TEXT NOT NULL
                )
            """)
            await db.commit()
        self.logger.info("Initialized 'autoresponses' table.")
