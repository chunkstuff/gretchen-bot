"""
Self-check for confession post scheduling rollover.

Run: python test_scheduling.py
"""
from datetime import datetime, timedelta, timezone

from cogs.confession.embeds import discord_time, parse_utc
from cogs.confession.services import next_post_time


def _utc(*args):
	return datetime(*args, tzinfo=timezone.utc)


CASES = [
	# (label, now, expected next post)
	("before :15 same hour", _utc(2026, 7, 22, 10, 3), _utc(2026, 7, 22, 10, 15)),
	("exactly :15 rolls forward", _utc(2026, 7, 22, 10, 15), _utc(2026, 7, 22, 11, 15)),
	("after :15 next hour", _utc(2026, 7, 22, 10, 34), _utc(2026, 7, 22, 11, 15)),
	("day rollover", _utc(2026, 7, 22, 23, 30), _utc(2026, 7, 23, 0, 15)),
	("week rollover sun->mon", _utc(2026, 7, 26, 23, 30), _utc(2026, 7, 27, 0, 15)),
	("month rollover 31 days", _utc(2026, 7, 31, 23, 30), _utc(2026, 8, 1, 0, 15)),
	("month rollover 30 days", _utc(2026, 6, 30, 23, 30), _utc(2026, 7, 1, 0, 15)),
	("feb non-leap year", _utc(2026, 2, 28, 23, 30), _utc(2026, 3, 1, 0, 15)),
	("feb leap year", _utc(2028, 2, 28, 23, 30), _utc(2028, 2, 29, 0, 15)),
	("feb 29 leap year", _utc(2028, 2, 29, 23, 30), _utc(2028, 3, 1, 0, 15)),
	("year rollover", _utc(2026, 12, 31, 23, 30), _utc(2027, 1, 1, 0, 15)),
]


def test_cases():
	for label, now, expected in CASES:
		got = next_post_time(now)
		assert got == expected, f"{label}: got {got}, want {expected}"


def test_every_minute_of_a_year():
	"""Sweep a full leap year: result is always in the future and <= 1h away."""
	now = _utc(2028, 1, 1, 0, 0)
	end = _utc(2029, 1, 1, 0, 0)
	while now < end:
		nxt = next_post_time(now)
		delta = (nxt - now).total_seconds()
		assert nxt.minute == 15 and nxt.second == 0, f"{now} -> {nxt} not on :15"
		assert 0 < delta <= 3600, f"{now} -> {nxt} is {delta}s away"
		now += timedelta(minutes=1)


def test_queue_offset():
	"""Queue position N posts N-1 hours after the next :15, across a day boundary."""
	now = _utc(2026, 7, 22, 23, 30)
	for position, expected in [
		(1, _utc(2026, 7, 23, 0, 15)),
		(2, _utc(2026, 7, 23, 1, 15)),
		(25, _utc(2026, 7, 24, 0, 15)),
	]:
		got = next_post_time(now) + timedelta(hours=position - 1)
		assert got == expected, f"position {position}: got {got}, want {expected}"


def test_parse_utc():
	"""Stored timestamps read as UTC whether or not they carry an offset."""
	naive = parse_utc("2026-07-22T08:38:01.013429")          # legacy rows
	aware = parse_utc("2026-07-22T08:38:01.013429+00:00")    # written since 2026-07
	assert naive == aware, f"{naive} != {aware}"
	assert naive.tzinfo is not None and naive.hour == 8


def test_discord_time():
	"""Embeds emit Discord markdown so each viewer sees their own timezone."""
	# 2026-07-22T08:38:00Z is epoch 1784709480
	assert discord_time("2026-07-22T08:38:00+00:00") == "<t:1784709480:f>"
	# A legacy naive row is UTC, so it renders identically to its aware form
	assert discord_time("2026-07-22T08:38:00") == "<t:1784709480:f>"
	assert discord_time(_utc(2026, 7, 22, 8, 38), "R") == "<t:1784709480:R>"
	# No hardcoded zone leaks into the output
	for style in ("f", "R", "t"):
		assert "UK" not in discord_time(_utc(2026, 7, 22, 8, 38), style)


if __name__ == "__main__":
	test_cases()
	test_every_minute_of_a_year()
	test_queue_offset()
	test_parse_utc()
	test_discord_time()
	print(f"ok: {len(CASES)} cases + full-year sweep + queue/tz checks")
