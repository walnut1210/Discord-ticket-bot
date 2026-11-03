import os
import re
import logging

import discord
from discord import app_commands
from discord.ext import commands

# Read configuration from environment variables.
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ROLE_ID = int(os.getenv("MOD_ROLE_ID", "0"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("ticket-bot")


def clean_channel_name(username: str) -> str:
    """Convert a Discord username into a safe channel-name fragment."""
    name = username.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return (name or "user")[:80]


def get_ticket_creator(channel: discord.abc.GuildChannel) -> int | None:
    """Read the creator ID stored in a ticket channel's topic."""
    topic = getattr(channel, "topic", None) or ""
    match = re.fullmatch(r"creator:(\d+)", topic)
    return int(match.group(1)) if match else None


def can_close_ticket(
    member: discord.Member,
    channel: discord.abc.GuildChannel,
) -> bool:
    """Allow the ticket creator, configured moderator role, or channel managers."""
    creator_id = get_ticket_creator(channel)
    has_moderator_role = any(role.id == MOD_ROLE_ID for role in member.roles)
    return (
        member.id == creator_id
        or has_moderator_role
        or member.guild_permissions.manage_channels
    )


async def close_ticket(interaction: discord.Interaction) -> None:
    channel = interaction.channel
    member = interaction.user

    if not isinstance(channel, discord.TextChannel) or not isinstance(member, discord.Member):
        await interaction.response.send_message(
            "この操作はチケットチャンネル内で実行してください。",
            ephemeral=True,
        )
        return

    if get_ticket_creator(channel) is None:
        await interaction.response.send_message(
            "このチャンネルはチケットとして認識できません。",
            ephemeral=True,
        )
        return

    if not can_close_ticket(member, channel):
        await interaction.response.send_message(
            "チケットを閉じる権限がありません。",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        "チケットを閉じます。このチャンネルは5秒後に削除されます。",
        ephemeral=False,
    )
    await channel.delete(
        reason=f"Ticket closed by {member} ({member.id})",
        delay=5,
    )


class CloseView(discord.ui.View):
    """Persistent view containing the ticket close button."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="チケットを閉じる",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close",
        emoji="🔒",
    )
    async def close_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await close_ticket(interaction)


class TicketView(discord.ui.View):
    """Persistent view used on the public ticket panel."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="チケットを作成",
        style=discord.ButtonStyle.primary,
        custom_id="ticket:create",
        emoji="🎫",
    )
    async def create_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        guild = interaction.guild
        member = interaction.user

        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "サーバー内でのみ利用できます。",
                ephemeral=True,
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "チケットカテゴリが見つかりません。管理者に設定を確認してもらってください。",
                ephemeral=True,
            )
            return

        # Prevent a member from opening multiple tickets in the same category.
        for channel in category.text_channels:
            if get_ticket_creator(channel) == member.id:
                await interaction.response.send_message(
                    f"すでにチケットがあります: {channel.mention}",
                    ephemeral=True,
                )
                return

        moderator_role = guild.get_role(MOD_ROLE_ID)
        if moderator_role is None:
            await interaction.response.send_message(
                "モデレーターロールが見つかりません。管理者に設定を確認してもらってください。",
                ephemeral=True,
            )
            return

        bot_member = guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "Botのメンバー情報を取得できませんでした。",
                ephemeral=True,
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            moderator_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            ),
        }

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{clean_channel_name(member.name)}",
                category=category,
                topic=f"creator:{member.id}",
                overwrites=overwrites,
                reason=f"Ticket opened by {member} ({member.id})",
            )
            embed = discord.Embed(
                title="お問い合わせ",
                description=(
                    f"{member.mention} さんのチケットを作成しました。\n"
                    "こちらにお問い合わせ内容を送信してください。\n"
                    "対応が終了したら、下のボタンからチケットを閉じられます。"
                ),
                color=discord.Color.blurple(),
            )
            await channel.send(
                content=member.mention,
                embed=embed,
                view=CloseView(),
            )
            await interaction.followup.send(
                f"チケットを作成しました: {channel.mention}",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "チャンネルを作成できませんでした。Botにチャンネル管理権限があるか確認してください。",
                ephemeral=True,
            )
        except discord.HTTPException:
            log.exception("Failed to create ticket channel")
            await interaction.followup.send(
                "チケットの作成中にエラーが発生しました。",
                ephemeral=True,
            )


class TicketBot(commands.Bot):
    def __init__(self) -> None:
        # This bot uses slash commands and buttons; no privileged intents are required.
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

    async def setup_hook(self) -> None:
        # Register persistent views so their buttons continue working after restarts.
        self.add_view(TicketView())
        self.add_view(CloseView())
        await self.tree.sync()
        log.info("Application commands synchronized")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "unknown")


bot = TicketBot()


@bot.tree.command(
    name="ticket-panel",
    description="チケット作成パネルを設置します。",
)
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def ticket_panel(interaction: discord.Interaction) -> None:
    if not interaction.permissions.manage_guild:
        await interaction.response.send_message(
            "このコマンドを実行するにはサーバー管理権限が必要です。",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="お問い合わせ",
        description=(
            "お問い合わせがある場合は、下のボタンを押してチケットを作成してください。\n"
            "作成したチケットは、本人とサポート担当者だけが閲覧できます。"
        ),
        color=discord.Color.blurple(),
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message(
        "チケットパネルを設置しました。",
        ephemeral=True,
    )


@bot.tree.command(
    name="ticket-close",
    description="現在のチケットを閉じます。",
)
@app_commands.guild_only()
async def ticket_close(interaction: discord.Interaction) -> None:
    await close_ticket(interaction)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN が設定されていません。.env.example を参考に環境変数を設定してください。"
        )
    if not MOD_ROLE_ID or not TICKET_CATEGORY_ID:
        raise RuntimeError("MOD_ROLE_ID と TICKET_CATEGORY_ID を設定してください。")

    bot.run(TOKEN)
