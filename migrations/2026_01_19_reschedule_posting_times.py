"""
Migration script to reschedule existing confessions to new posting times.

This script updates all scheduled confessions to use the new posting schedule:
12am, 1am, 2am, and 3am UK time instead of just 2am.
"""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

UK_TZ = ZoneInfo("Europe/London")
POSTING_HOURS = [0, 1, 2, 3]  # 12am, 1am, 2am, 3am

def get_next_available_slot(now_uk, used_slots):
	"""
	Find the next available posting slot.

	Args:
		now_uk: Current time in UK timezone
		used_slots: Set of already used datetime slots

	Returns:
		datetime: Next available slot in UK timezone
	"""
	days_ahead = 0

	while days_ahead < 365:
		for hour in POSTING_HOURS:
			candidate = now_uk.replace(
				hour=hour,
				minute=0,
				second=0,
				microsecond=0
			).replace(day=now_uk.day) + (
				__import__('datetime').timedelta(days=days_ahead)
			)

			# Skip past times
			if candidate <= now_uk:
				continue

			# Check if slot is available
			if candidate not in used_slots:
				return candidate

		days_ahead += 1

	return None


def migrate_schedules(data_file='data/confession_data.json'):
	"""
	Migrate all scheduled confessions to new time slots.

	Args:
		data_file: Path to confession data file
	"""
	# Load data
	with open(data_file, 'r', encoding='utf-8') as f:
		data = json.load(f)

	post_queue = data.get('post_queue', [])

	if not post_queue:
		print("No confessions in post queue to migrate.")
		return

	print(f"Found {len(post_queue)} confessions to reschedule")

	# Sort by current scheduled time to maintain order
	post_queue.sort(key=lambda x: x.get('scheduled_time', ''))

	now_uk = datetime.now(UK_TZ)
	used_slots = set()

	# Reschedule each confession
	for i, confession in enumerate(post_queue, 1):
		old_time = confession.get('scheduled_time')
		if not old_time:
			print(f"Confession #{confession['id']}: No scheduled time, skipping")
			continue

		# Parse old time
		old_dt = datetime.fromisoformat(old_time)
		if old_dt.tzinfo is None:
			old_dt = old_dt.replace(tzinfo=timezone.utc)
		old_dt_uk = old_dt.astimezone(UK_TZ)

		# Find next available slot
		new_dt_uk = get_next_available_slot(now_uk, used_slots)
		if not new_dt_uk:
			print(f"ERROR: Could not find slot for confession #{confession['id']}")
			continue

		# Convert back to UTC ISO format
		new_dt_utc = new_dt_uk.astimezone(timezone.utc)
		confession['scheduled_time'] = new_dt_utc.isoformat()
		used_slots.add(new_dt_uk)

		print(
			f"Confession #{confession['id']}: "
			f"{old_dt_uk.strftime('%Y-%m-%d %H:%M')} → "
			f"{new_dt_uk.strftime('%Y-%m-%d %H:%M')} UK"
		)

	# Save updated data
	with open(data_file, 'w', encoding='utf-8') as f:
		json.dump(data, f, indent=4)

	print(f"\n✅ Successfully rescheduled {len(post_queue)} confessions")
	print(f"Updated data saved to {data_file}")


if __name__ == "__main__":
	import sys

	data_file = sys.argv[1] if len(sys.argv) > 1 else 'data/confession_data.json'

	print(f"Migrating schedules in {data_file}...")
	print("=" * 60)

	migrate_schedules(data_file)
