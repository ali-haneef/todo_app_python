"""Tests for TaskFlow's Flask API using Python's standard unittest module."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import app, init_db


class TaskFlowAPITests(unittest.TestCase):
    """Exercise the main browser-facing API workflows."""

    def setUp(self) -> None:
        """Create an isolated database and Flask test client."""
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "taskflow.db"
        app.config.update(TESTING=True, DATABASE=str(database_path))
        with app.app_context():
            init_db()
        self.client = app.test_client()

    def tearDown(self) -> None:
        """Remove the isolated test database."""
        self.temp_directory.cleanup()

    def test_index_and_empty_state_api(self) -> None:
        """The home page and initial API responses should be available."""
        page = self.client.get("/")
        tasks = self.client.get("/api/tasks")
        stats = self.client.get("/api/stats")

        self.assertEqual(page.status_code, 200)
        self.assertIn(b"TaskFlow", page.data)
        self.assertEqual(tasks.json, {"tasks": []})
        self.assertEqual(stats.json["total"], 0)

    def test_create_update_complete_and_delete(self) -> None:
        """A task should support its complete lifecycle through the API."""
        created = self.client.post(
            "/api/tasks",
            json={
                "title": "Ship the release",
                "description": "Review the final checklist.",
                "due_date": "2030-04-15",
                "priority": "high",
            },
        )
        self.assertEqual(created.status_code, 201)
        task_id = created.json["task"]["id"]

        updated = self.client.patch(
            f"/api/tasks/{task_id}",
            json={"completed": True, "title": "Ship the release today"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(updated.json["task"]["completed"])

        completed = self.client.get("/api/tasks?filter=completed")
        self.assertEqual(len(completed.json["tasks"]), 1)

        stats = self.client.get("/api/stats")
        self.assertEqual(stats.json["completed"], 1)
        self.assertEqual(stats.json["pending"], 0)

        deleted = self.client.delete(f"/api/tasks/{task_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/tasks").json["tasks"], [])

    def test_validation_and_missing_task_errors(self) -> None:
        """Invalid input and unknown IDs should return readable JSON errors."""
        invalid = self.client.post(
            "/api/tasks",
            json={"title": " ", "priority": "urgent"},
        )
        missing = self.client.patch("/api/tasks/99999", json={"completed": True})

        self.assertEqual(invalid.status_code, 400)
        self.assertIn("error", invalid.json)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json["error"], "Task not found.")


if __name__ == "__main__":
    unittest.main()
