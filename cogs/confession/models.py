"""
Data models and persistence for confessions.
"""
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ConfessionData:
	"""Handles confession data persistence and management."""

	def __init__(self, persistence_file: str, archive_file: str):
		"""
		Initialize the confession data manager.

		Args:
			persistence_file: Path to the main data persistence file
			archive_file: Path to the archive file for processed confessions
		"""
		self.persistence_file = persistence_file
		self.archive_file = archive_file
		self.submission_queue: List[Dict] = []
		self.post_queue: List[Dict] = []
		self.embed_message_id: Optional[int] = None
		self.confession_counter: int = 1

	def load(self):
		"""Load all data from persistence file."""
		try:
			with open(self.persistence_file, "r", encoding="utf-8") as f:
				data = json.load(f)
				self.submission_queue = data.get("submission_queue", [])
				self.post_queue = data.get("post_queue", [])
				self.embed_message_id = data.get("embed_message_id", None)
				self.confession_counter = data.get("confession_counter", 1)
			logger.info(
				"Loaded data: %s submissions, %s scheduled posts",
				len(self.submission_queue),
				len(self.post_queue)
			)
		except (FileNotFoundError, json.JSONDecodeError) as e:
			logger.warning(
				"Persistence file not found or corrupted: %s. Starting fresh.",
				e
			)

	def save(self):
		"""Save all data to persistence file."""
		data = {
			"submission_queue": self.submission_queue,
			"post_queue": self.post_queue,
			"embed_message_id": self.embed_message_id,
			"confession_counter": self.confession_counter,
		}
		try:
			with open(self.persistence_file, "w", encoding="utf-8") as f:
				json.dump(data, f, indent=4)
			logger.debug("Data saved to persistence file")
		except Exception as e:
			logger.error("Failed to save data: %s", e)

	def archive(self, confession: Dict):
		"""
		Archive a confession to the archive file.

		Args:
			confession: The confession dict to archive
		"""
		try:
			with open(self.archive_file, "a", encoding="utf-8") as f:
				json.dump(confession, f, indent=4)
				f.write("\n")
			logger.info("Archived confession #%s", confession['id'])
		except Exception as e:
			logger.error(
				"Failed to archive confession #%s: %s",
				confession['id'],
				e
			)

	def add_submission(self, confession: Dict):
		"""
		Add a confession to the submission queue.

		Args:
			confession: The confession dict to add
		"""
		self.submission_queue.append(confession)
		self.confession_counter += 1
		self.save()

	def remove_submission(self, confession: Dict):
		"""
		Remove a confession from the submission queue.

		Args:
			confession: The confession dict to remove
		"""
		if confession in self.submission_queue:
			self.submission_queue.remove(confession)
			self.save()

	def add_to_post_queue(self, confession: Dict):
		"""
		Add an approved confession to the post queue.

		Args:
			confession: The approved confession dict to add
		"""
		self.post_queue.append(confession)
		self.save()

	def remove_from_post_queue(self, confession: Dict):
		"""
		Remove a confession from the post queue.

		Args:
			confession: The confession dict to remove
		"""
		if confession in self.post_queue:
			self.post_queue.remove(confession)
			self.save()
