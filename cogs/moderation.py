import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
from utils.data_manager import DataManager

class ModerationCog(commands.Cog):
    """Moderation commands for warnings, timeouts, bans, event logging, and action lookup."""

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

    async def _dm_user(self, member: discord.Member, action: str, reason: str, moderator: str, extra_info: str = "") -> None:
        embed = discord.Embed(
            title=f"You have been {action} in {member.guild.name}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=moderator, inline=False)
        if extra_info:
            embed.add_field(name="Details", value=extra_info, inline=False)
        try:
            await member.send(embed=embed)
        except discord.HTTPException:
            pass  # DM failed, but action still taken

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

        warning_count = len(self.data_manager.get_user_actions(member)["warnings"])
        await self._dm_user(member, "warned", reason, str(interaction.user), f"This is warning #{warning_count}")

        auto_timeout_embed = None
        if warning_count == 3:
            auto_duration = "30m"
            until = datetime.utcnow() + self._format_duration(auto_duration)
            try:
                await member.edit(timeout=until, reason="Automatic timeout after 3 warnings")
                self.data_manager.add_timeout(member, "System", "Automatic timeout after 3 warnings", auto_duration)
                await self._dm_user(
                    member,
                    "timed out",
                    "Automatic timeout after reaching 3 warnings.",
                    "System",
                    f"This timeout will last {auto_duration}. An automatic action has been taken.",
                )
                auto_timeout_embed = discord.Embed(
                    title="Automatic Timeout Applied",
                    color=discord.Color.gold(),
                    timestamp=datetime.utcnow(),
                )
                auto_timeout_embed.add_field(name="User", value=member.mention, inline=True)
                auto_timeout_embed.add_field(name="Duration", value=auto_duration, inline=True)
                auto_timeout_embed.add_field(name="Reason", value="Reached 3 warnings", inline=False)
                auto_timeout_embed.add_field(name="Moderator", value="System", inline=True)
                auto_timeout_embed.add_field(name="Expires", value=until.strftime("%Y-%m-%d %H:%M UTC"), inline=False)
            except discord.HTTPException:
                auto_timeout_embed = None

        embed = discord.Embed(
            title="User Warned",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Warning Count", value=str(warning_count), inline=True)
        embed.add_field(name="Date", value=entry["date"], inline=False)

        await interaction.response.send_message(embed=embed)
        await self.log_embed(embed)
        if auto_timeout_embed:
            await interaction.followup.send(embed=auto_timeout_embed)
            await self.log_embed(auto_timeout_embed)

    @app_commands.command(name="timeout", description="Temporarily mute a member for a duration.")
    @app_commands.checks.has_permissions(moderate_members=True)
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
        await self._dm_user(member, "timed out", reason, str(interaction.user), f"Duration: {duration}")

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
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.describe(member="The member to ban", reason="Reason for the ban")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if not interaction.guild:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="This command can only be used inside a server.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        bot_member = interaction.guild.get_member(self.bot.user.id) or interaction.guild.me
        if bot_member is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="I cannot verify my server role hierarchy, so I cannot ban this member.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        if bot_member.top_role <= member.top_role or member == bot_member:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="I cannot ban this member because their role is equal to or higher than mine.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

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
        await self._dm_user(member, "banned", reason, str(interaction.user), "This ban is permanent.")
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

        if isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="I do not have permission to perform this command. Please make sure my role has the required permissions.",
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
