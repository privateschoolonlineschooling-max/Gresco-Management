import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
from utils.data_manager import DataManager

class ModerationCog(commands.Cog):
    """Moderation commands for warnings, timeouts, bans, and action lookup."""

    def __init__(self, bot: commands.Bot, data_manager: DataManager, log_channel_id: Optional[int] = None):
        self.bot = bot
        self.data_manager = data_manager
        self.log_channel_id = log_channel_id

    async def log_embed(self, embed: discord.Embed) -> None:
        if not self.log_channel_id:
            return
        channel = self.bot.get_channel(self.log_channel_id)
        if channel:
            await channel.send(embed=embed)

    @staticmethod
    def _format_duration(value: str) -> timedelta:
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if len(value) < 2:
            raise ValueError("Duration too short.")
        amount = int(value[:-1])
        unit = value[-1].lower()
        if unit not in units:
            raise ValueError("Invalid duration unit.")
        return timedelta(seconds=amount * units[unit])

    @app_commands.command(name="warn", description="Warn a member and record the reason.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(member="The member to warn", reason="Reason for the warning")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        entry = self.data_manager.add_warning(member, str(interaction.user), reason)

        embed = discord.Embed(
            title="User Warned",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Date", value=entry["date"], inline=False)

        await interaction.response.send_message(embed=embed)
        await self.log_embed(embed)

    @app_commands.command(name="timeout", description="Temporarily mute a member for a duration.")
    @app_commands.checks.has_permissions(timeout_members=True)
    @app_commands.describe(member="The member to timeout", duration="Duration like 10m or 1h", reason="Reason for timeout")
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str,
    ):
        try:
            delta = self._format_duration(duration)
        except (ValueError, TypeError):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="Please enter a valid duration, for example `10m`, `1h`, or `30s`.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        until = datetime.utcnow() + delta
        try:
            await member.edit(timeout=until, reason=reason)
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Could not timeout this member: {error}",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        entry = self.data_manager.add_timeout(member, str(interaction.user), reason, duration)
        embed = discord.Embed(
            title="User Timed Out",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Expires", value=until.strftime("%Y-%m-%d %H:%M UTC"), inline=False)
        embed.add_field(name="Logged", value=entry["date"], inline=False)

        await interaction.response.send_message(embed=embed)
        await self.log_embed(embed)

    @app_commands.command(name="ban", description="Permanently ban a member from the server.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(member="The member to ban", reason="Reason for the ban")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        try:
            await member.ban(reason=reason)
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Could not ban this member: {error}",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        entry = self.data_manager.add_ban(member, str(interaction.user), reason)
        embed = discord.Embed(
            title="User Banned",
            color=discord.Color.dark_red(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Date", value=entry["date"], inline=False)

        await interaction.response.send_message(embed=embed)
        await self.log_embed(embed)

    @app_commands.command(name="actions", description="View moderation actions for a member.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(member="The user to lookup")
    async def actions(self, interaction: discord.Interaction, member: discord.Member):
        reports = self.data_manager.get_user_actions(member)
        embed = discord.Embed(
            title=f"Moderation Actions for {member.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )

        def build_section(entries, fallback):
            if not entries:
                return fallback
            return "\n".join(
                f"**{i+1}.** {item.get('type','warning').capitalize()} — {item['reason']} (by {item['moderator']})"
                for i, item in enumerate(entries)
            )

        embed.add_field(name="Warnings", value=build_section(reports["warnings"], "No warnings."), inline=False)
        embed.add_field(name="Timeouts", value=build_section(reports["timeouts"], "No timeouts."), inline=False)
        embed.add_field(name="Bans", value=build_section(reports["bans"], "No bans."), inline=False)

        if reports["actions"]:
            latest = reports["actions"][-1]
            embed.set_footer(text=f"Last action: {latest['type'].capitalize()} on {latest['date']}")

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You do not have permission to use this command.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        if isinstance(error, app_commands.CommandInvokeError):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"An error occurred while running this command: {error.__cause__ or error}",
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
