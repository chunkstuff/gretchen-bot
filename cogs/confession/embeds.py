"""
Embed builders for confession notifications.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import discord

UK_TZ = ZoneInfo("Europe/London")


# Color constants
class EmbedColors:
	"""Discord embed colors."""
	SUCCESS = 0x57F287  # Discord green
	DANGER = 0xED4245   # Discord red
	WARNING = 0xFEE75C  # Discord yellow
	INFO = 0x5865F2     # Discord blurple
	PINK = 0xFFC0CB     # Gretchen pink


def format_timestamp(iso_timestamp):
	"""
	Format an ISO timestamp string into a human-readable format.

	Args:
		iso_timestamp: ISO format timestamp string (e.g., "2026-01-18T00:40:23.574855")

	Returns:
		str: Formatted string (e.g., "18 Jan 2026 at 00:40 UTC")
	"""
	try:
		dt = datetime.fromisoformat(iso_timestamp)
		return dt.strftime("%d %b %Y at %H:%M UTC")
	except (ValueError, TypeError):
		# If parsing fails, return the original string
		return iso_timestamp


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
	embed.timestamp = datetime.utcnow()
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

	# Convert submission time to UK time for display
	submission_dt = datetime.fromisoformat(confession['submission_time'])
	if submission_dt.tzinfo is None:
		submission_dt = submission_dt.replace(tzinfo=timezone.utc)
	submission_dt_uk = submission_dt.astimezone(UK_TZ)
	formatted_time = submission_dt_uk.strftime("%d %b %Y at %H:%M UK")

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
		timestamp=datetime.fromisoformat(confession["submission_time"]),
	)
	embed.add_field(name="", value="🤫🤭")
	embed.set_footer(text="Anonymously Submitted")

	return embed
