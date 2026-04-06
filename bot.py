import os
import discord
from discord.ext import commands
from cogs.moderation import ModerationCog
from cogs.roleplay import RoleplayCog
from utils.data_manager import DataManager

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
if LOG_CHANNEL_ID:
    try:
        LOG_CHANNEL_ID = int(LOG_CHANNEL_ID)
    except ValueError:
        LOG_CHANNEL_ID = None

if not TOKEN:
    raise RuntimeError("The DISCORD_TOKEN environment variable is required.")

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

data_manager = DataManager("data.json")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        await bot.tree.sync()
        print("Slash commands synced successfully.")
    except Exception as error:
        print(f"Sync failed: {error}")

@bot.event
async def setup_hook():
    await bot.add_cog(ModerationCog(bot, data_manager, LOG_CHANNEL_ID))
    await bot.add_cog(RoleplayCog(bot))

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if interaction.response.is_done():
        return

    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message(
            embed=discord.Embed(
                description="You do not have permission to use this command.",
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )
        return

    if isinstance(error, discord.app_commands.CommandInvokeError):
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"An error occurred while executing the command: {error.__cause__ or error}",
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        embed=discord.Embed(
            description="An unexpected error occurred.",
            color=discord.Color.red(),
        ),
        ephemeral=True,
    )

if __name__ == "__main__":
    bot.run(TOKEN)
