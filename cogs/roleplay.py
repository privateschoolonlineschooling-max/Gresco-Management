import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class RoleplayCog(commands.Cog):
    """Shift and training commands for roleplay-style scheduling."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shift", description="Create a promo shift announcement.")
    @app_commands.describe(
        promo_shift="Is this a promo shift?",
        shift_name="Name of the shift",
        host="Shift host",
        co_host="Shift co-host",
        time="Scheduled time for the shift",
        ping_role="Optional role to ping"
    )
    async def shift(
        self,
        interaction: discord.Interaction,
        promo_shift: bool,
        shift_name: str,
        host: discord.Member,
        co_host: Optional[discord.Member],
        time: str,
        ping_role: Optional[discord.Role] = None,
    ):
        title = "Promo Shift Scheduled" if promo_shift else "Shift Scheduled"
        embed = discord.Embed(
            title=title,
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Shift Name", value=shift_name, inline=False)
        embed.add_field(name="Hosted By", value=host.mention, inline=True)
        embed.add_field(name="Co-host", value=(co_host.mention if co_host else "None"), inline=True)
        embed.add_field(name="Time", value=time, inline=False)
        embed.set_footer(text="Use this message to coordinate your Roblox-style shift.")

        content = ping_role.mention if ping_role else None
        await interaction.response.send_message(content=content, embed=embed)

    @app_commands.command(name="training", description="Create a training session announcement.")
    @app_commands.describe(
        store_colleague="Junior store colleague",
        security="Junior security",
        host="Training host",
        co_host="Training co-host",
        trainer="Trainer",
        time="Training session time",
        ping_role="Optional role to ping"
    )
    async def training(
        self,
        interaction: discord.Interaction,
        store_colleague: str,
        security: str,
        host: discord.Member,
        co_host: Optional[discord.Member],
        trainer: discord.Member,
        time: str,
        ping_role: Optional[discord.Role] = None,
    ):
        embed = discord.Embed(
            title="Training Session Scheduled",
            color=discord.Color.green(),
        )
        embed.add_field(name="Junior Store Colleague", value=store_colleague, inline=False)
        embed.add_field(name="Junior Security", value=security, inline=False)
        embed.add_field(name="Host", value=host.mention, inline=True)
        embed.add_field(name="Co-host", value=(co_host.mention if co_host else "None"), inline=True)
        embed.add_field(name="Trainer", value=trainer.mention, inline=False)
        embed.add_field(name="Time", value=time, inline=False)
        embed.set_footer(text="Training details for your roleplay server.")

        content = ping_role.mention if ping_role else None
        await interaction.response.send_message(content=content, embed=embed)
