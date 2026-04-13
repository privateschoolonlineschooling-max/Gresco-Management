import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class RoleplayCog(commands.Cog):
    """Commands for hosting events on the Kasi Vibes studio."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="host_event", description="Host an event and post it to the selected channel.")
    @app_commands.describe(
        event_name="The name of the event",
        host="The member hosting the event",
        link="The event link for Kasi Vibes Studio",
        details="A short description or details for the event",
        channel="The channel to post the event announcement into"
    )
    async def host_event(
        self,
        interaction: discord.Interaction,
        event_name: str,
        host: discord.Member,
        link: str,
        details: str,
        channel: discord.TextChannel,
    ):
        embed = discord.Embed(
            title="Kasi Vibes Studio Event",
            description=details,
            color=discord.Color.purple(),
        )
        embed.add_field(name="Event", value=event_name, inline=False)
        embed.add_field(name="Host", value=host.mention, inline=True)
        embed.add_field(name="Link", value=link, inline=False)
        embed.set_footer(text="Posted by Kasi Vibes Studio event host.")

        if not interaction.guild or channel.guild.id != interaction.guild.id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="Please select a channel from this server.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="I do not have permission to send messages in the selected channel.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Event posted in {channel.mention}.",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )
