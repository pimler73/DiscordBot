import io
import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
import logging

# Local Import
from database_manager import DatabaseManager
from autoresponder import Autoresponder

# Max Message length:
MAX_DISCORD_MESSAGE_LENGTH = 2000

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.message_content = True


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.db_manager = DatabaseManager()
        self.autoresponder = Autoresponder(self.db_manager)

    async def setup_hook(self):
        await self.db_manager.init_autoresponses()
        # await self.tree.sync() # Register slash commands globally
        # self.tree.add_command(addresponse)
        # self.tree.add_command(delresponse)
        # self.tree.add_command(delresponsebyid)
        # self.tree.add_command(listresponses)
        # self.tree.add_command(bulkadd)
        await self.tree.sync()
        logger.info("All commands synced")


# === Initialize the Bot ===
bot = Bot()


# === Command: Add a response ===
@bot.tree.command(
    name="addresponse", description="Add a response for a keyword."
)
@app_commands.describe(
    key="Trigger word", response="Bot response for that keyword"
)
async def addresponse(
    interaction: discord.Interaction, key: str, response: str
):
    logger.info(
        f"{interaction.user} ran /addresponse key='{key}', response='{response}'"
    )
    await bot.autoresponder.add(key, response)
    await interaction.response.send_message(
        f"Added response for key '{key}'", ephemeral=True
    )


# === Command: Delete responses for a key ===
@bot.tree.command(
    name="delresponse",
    description="Delete one or all responses for a keyword.",
)
@app_commands.describe(
    key="Keyword to delete responses from",
    response="Specific response to delete",
)
async def delresponse(
    interaction: discord.Interaction, key: str, response: str
):
    logger.info(
        f"{interaction.user} ran /delresponse key='{key}', response='{response}'"
    )
    if (
        response is not None
        and not interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "Only administrators can delete all responses for a key.",
            ephemeral=True,
        )
        logger.warning(
            f"{interaction.user} attempted to delete all responses without admin rights."
        )
        return
    await bot.autoresponder.remove(key, response)
    msg = (
        f"Removed all responses for `{key}`"
        if response is None
        else f"Removed response `{response}` from `{key}`"
    )
    await interaction.response.send_message(msg, ephemeral=True)


# === Command: Delete responses for a key given ID ===
@bot.tree.command(
    name="delresponsebyid", description="Delete a response by its ID."
)
@app_commands.describe(entry_id="The ID of the response (from /listresponses)")
async def delresponsebyid(interaction: discord.Interaction, entry_id: int):
    logger.info(
        f"{interaction.user} ran /delresponsebyid with entry_id={entry_id}"
    )
    await bot.autoresponder.remove_by_id(entry_id)
    await interaction.response.send_message(
        f"Removed response with ID `{entry_id}`", ephemeral=True
    )


# === Command: List responses for a key ===
@bot.tree.command(
    name="listresponses", description="List all responses for a keyword."
)
@app_commands.describe(key="Keyword to look up")
async def listresponses(interaction: discord.Interaction, key: str):
    logger.info(f"{interaction.user} ran /listresponses with key='{key}'")
    responses = await bot.autoresponder.list_responses_for_key(key)
    if not responses:
        await interaction.response.send_message(
            f"No responses found for `{key}`.", ephemeral=True
        )
        return

    formatted = "\n".join(f"`{row[0]}`: {row[1]}" for row in responses)
    if len(formatted) <= MAX_DISCORD_MESSAGE_LENGTH:
        # Send as a regular message if short enough
        await interaction.response.send_message(
            f"Responses for **{key}**:\n{formatted}", ephemeral=True
        )
    else:
        # Send as a file if it's too long
        logger.info(
            f"Response has {len(formatted)} characters which is greater than 2000. Sending a file."
        )
        file = discord.File(
            io.BytesIO(formatted.encode()), filename=f"{key}_responses.txt"
        )
        await interaction.response.send_message(
            content=f"Responses for **{key}** (see attached):",
            file=file,
            ephemeral=True,
        )


# === Command: Add responses in bulk ===
@bot.tree.command(
    name="bulkadd",
    description="Upload a list of responses for a key (admin only)",
)
@app_commands.describe(key="The keyword these responses should be added to")
async def bulkadd(
    interaction: discord.Interaction, key: str, file: discord.Attachment
):
    logger.info(
        f"{interaction.user} ran /bulkadd with key='{key}', file='{file.filename if file else 'None'}'"
    )

    if not interaction.user.guild_permissions.administrator:
        logger.warning(f"Unauthorized bulkadd attempt by {interaction.user}")
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return

    if not file:
        logger.error("No file was attached in the /bulkadd command.")
        await interaction.response.send_message(
            "You must upload a file.", ephemeral=True
        )
        return

    if not file.filename.endswith(".txt"):
        logger.warning(f"Invalid file type uploaded: {file.filename}")
        await interaction.response.send_message(
            "Only `.txt` files are supported.", ephemeral=True
        )
        return

    try:
        content = await file.read()
        lines = content.decode().splitlines()
        logger.debug(f"Loaded {len(lines)} lines from {file.filename}")

        added = 0
        for line in lines:
            if line.strip():
                await bot.autoresponder.add(key, line.strip())
                added += 1

        logger.info(f"Added {added} responses to key '{key}' via bulk upload.")
        await interaction.response.send_message(
            f"Added {added} responses under `{key}`.", ephemeral=True
        )
    except Exception as e:
        logger.exception(f"Error processing file upload: {e}")
        await interaction.response.send_message(
            "Something went wrong while processing the file.", ephemeral=True
        )

# ===== Bot Events =====

@bot.event
async def on_ready():
    logger.info(f"Bot is connected as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    # Don't let the bot reply to itself or other bots
    if message.author.bot:
        return

    # Let slash commands still work
    await bot.process_commands(message)

    # Check for autoresponse keys
    response = await bot.autoresponder.get_random_response_from_message(
        message.content
    )
    if response:
        
        logger.info(
            f"Responding to user {message.author} with response `{response}`"
        )
        await message.channel.send(response)


# ---------- Run the Bot ----------
# with open("secret.txt") as f:
#     TOKEN = f.read().strip()
bot.run(BOT_TOKEN)
