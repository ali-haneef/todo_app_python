"""Unit tests for the task manager using only Python's standard library."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from task_manager import TaskManager, TaskStorageError


class TaskManagerTests(unittest.TestCase):
    """Verify task operations, sorting, filters, and persistence."""

    def setUp(self) -> None:
        """Create an isolated temporary task file for each test."""
        self.temp_directory = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_directory.name) / "tasks.json"
        self.manager = TaskManager(self.file_path)

    def tearDown(self) -> None:
        """Remove the temporary task file and directory."""
        self.temp_directory.cleanup()

    def test_add_and_reload_persisted_task(self) -> None:
        """Tasks should survive creation of a new manager instance."""
        task = self.manager.add_task("Write tests", "2030-01-02", "high")
        reloaded = TaskManager(self.file_path)

        self.assertEqual(reloaded.tasks[0].id, task.id)
        self.assertEqual(reloaded.tasks[0].title, "Write tests")
        self.assertEqual(reloaded.tasks[0].due_date, "2030-01-02")

    def test_sorting_and_filters(self) -> None:
        """Tasks should sort by priority and due date and filter correctly."""
        self.manager.add_task("Low", "2025-01-01", "low")
        self.manager.add_task("High late", "2025-03-01", "high")
        self.manager.add_task("High early", "2025-02-01", "high")
        self.manager.complete_task(2)

        self.assertEqual(
            [task.title for task in self.manager.list_tasks()],
            ["High early", "High late", "Low"],
        )
        self.assertEqual(
            [task.title for task in self.manager.list_tasks("completed")],
            ["High late"],
        )
        self.assertEqual(
            [task.title for task in self.manager.list_tasks("pending")],
            ["High early", "Low"],
        )

    def test_statistics_and_delete(self) -> None:
        """Statistics should update after completion and deletion."""
        self.manager.add_task("One")
        self.manager.add_task("Two")
        self.manager.complete_task(1)
        self.manager.delete_task(2)

        self.assertEqual(
            self.manager.statistics(), {"total": 1, "completed": 1, "pending": 0}
        )

    def test_corrupt_json_raises_storage_error(self) -> None:
        """Malformed JSON should produce a domain-specific error."""
        self.file_path.write_text("not json", encoding="utf-8")

        with self.assertRaises(TaskStorageError):
            TaskManager(self.file_path)

    def test_invalid_due_date_is_rejected(self) -> None:
        """Invalid due dates should fail before they are persisted."""
        with self.assertRaises(ValueError):
            self.manager.add_task("Bad date", "tomorrow")

        self.assertFalse(self.file_path.exists())


if __name__ == "__main__":
    unittest.main()
