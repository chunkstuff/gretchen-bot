"""
Embed builders for confession notifications.
"""
from datetime import datetime, timezone
import discord


# Color constants
class EmbedColors:
	"""Discord embed colors."""
	SUCCESS = 0x57F287  # Discord green
	DANGER = 0xED4245   # Discord red
	WARNING = 0xFEE75C  # Discord yellow
	INFO = 0x5865F2     # Discord blurple
	PINK = 0xFFC0CB     # Gretchen pink


def parse_utc(iso_timestamp):
	"""
	Parse a stored ISO timestamp into a timezone-aware UTC datetime.

	Timestamps written before 2026-07 are naive but always UTC, so a missing
	offset is read as UTC rather than as the host's local time.

	Args:
		iso_timestamp: ISO format timestamp string

	Returns:
		datetime: Timezone-aware datetime in UTC
	"""
	dt = datetime.fromisoformat(iso_timestamp)
	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=timezone.utc)
	return dt.astimezone(timezone.utc)


def discord_time(value, style="f"):
	"""
	Render a timestamp as Discord markdown, shown in each viewer's own timezone.

	Args:
		value: Timezone-aware datetime or stored ISO timestamp string
		style: Discord timestamp style (f=long date/time, R=relative, t=time)

	Returns:
		str: Markdown such as "<t:1753173481:f>"
	"""
	if isinstance(value, str):
		value = parse_utc(value)
	return f"<t:{int(value.timestamp())}:{style}>"


def _create_base_moderation_embed(title, description, color, confession):
	"""
	Create a base moderation embed with common structure.

	Args:
		title: The embed title
		description: The embed description (can contain {id} placeholder)
		color: The embed color
		confession: The confession dict

	Returns:
		discord.Embed: Base embed with title, description, color, and timestamp
	"""
	embed = discord.Embed(
		title=title,
		description=description.format(id=confession['id']),
		color=color
	)
	embed.timestamp = datetime.now(timezone.utc)
	return embed


def _add_moderator_fields(embed, moderator, confession_id):
	"""
	Add moderator and confession ID fields to an embed.

	Args:
		embed: The discord.Embed to add fields to
		moderator: The Discord user who performed the action
		confession_id: The confession ID number
	"""
	embed.add_field(
		name="👤 Moderator",
		value=moderator.mention,
		inline=True
	)
	embed.add_field(
		name="🆔 Confession ID",
		value=f"`#{confession_id}`",
		inline=True
	)


def _set_moderator_footer(embed, moderator, action):
	"""
	Set footer with moderator info and avatar.

	Args:
		embed: The discord.Embed to add footer to
		moderator: The Discord user who performed the action
		action: Action name (e.g., "Approved", "Rejected")
	"""
	embed.set_footer(
		text=f"{action} by {moderator.display_name}",
		icon_url=moderator.display_avatar.url
	)


def create_approval_embed(confession, moderator, posting_time, queue_position):
	"""
	Create the approval notification embed.

	Args:
		confession: The confession dict that was approved
		moderator: The Discord user who approved it
		posting_time: Formatted string of when it will post
		queue_position: Position in the posting queue

	Returns:
		discord.Embed: Approval notification embed
	"""
	embed = _create_base_moderation_embed(
		title="✅ Confession Approved",
		description="Confession **#{id}** has been approved and added to the posting queue.",
		color=EmbedColors.SUCCESS,
		confession=confession
	)

	embed.add_field(
		name="📅 Will post",
		value=posting_time,
		inline=False
	)

	embed.add_field(
		name="📊 Queue position",
		value=f"#{queue_position}",
		inline=True
	)

	embed.add_field(
		name="👤 Moderator",
		value=moderator.mention,
		inline=True
	)

	embed.add_field(
		name="📝 Submitted by",
		value=f"<@{confession['user_id']}>",
		inline=True
	)

	embed.add_field(
		name="🆔 Confession ID",
		value=f"`#{confession['id']}`",
		inline=True
	)

	_set_moderator_footer(embed, moderator, "Approved")

	return embed


def create_rejection_embed(confession, moderator):
	"""
	Create the rejection notification embed.

	Args:
		confession: The confession dict that was rejected
		moderator: The Discord user who rejected it

	Returns:
		discord.Embed: Rejection notification embed
	"""
	embed = _create_base_moderation_embed(
		title="❌ Confession Rejected",
		description="Confession **#{id}** has been rejected and archived.",
		color=EmbedColors.DANGER,
		confession=confession
	)

	_add_moderator_fields(embed, moderator, confession['id'])

	embed.add_field(
		name="📁 Status",
		value="```\nArchived\n```",
		inline=True
	)

	_set_moderator_footer(embed, moderator, "Rejected")

	return embed


def create_submission_embed(confession):
	"""
	Create the moderation queue submission embed.

	Args:
		confession: The confession dict that was submitted

	Returns:
		discord.Embed: Submission notification embed for moderators
	"""
	embed = discord.Embed(
		title=f"New Confession Submitted (#{confession['id']})",
		description=f"```\n{confession['text']}\n```",
		color=EmbedColors.WARNING,
	)

	formatted_time = discord_time(confession['submission_time'])

	embed.add_field(
		name="📝 Submitted by",
		value=f"<@{confession['user_id']}>",
		inline=True
	)

	embed.add_field(
		name="🕒 Submitted on",
		value=formatted_time,
		inline=True
	)

	return embed


def create_posted_confession_embed(confession, intro_message):
	"""
	Create the public confession post embed.

	Args:
		confession: The confession dict to post
		intro_message: Random Gretchen intro message

	Returns:
		discord.Embed: Public confession embed for posting channel
	"""
	embed = discord.Embed(
		title=f"Confession #{confession['id']}",
		description=f"{intro_message}\n```\n{confession['text']}\n```",
		color=EmbedColors.PINK,
		timestamp=parse_utc(confession["submission_time"]),
	)
	embed.add_field(name="", value="🤫🤭")
	embed.set_footer(text="Anonymously Submitted")

	return embed
