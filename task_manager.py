"""Task model and JSON-backed business logic for the CLI task manager."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, ClassVar


DEFAULT_TASK_FILE = Path(__file__).resolve().with_name("tasks.json")
PRIORITIES = ("low", "medium", "high")
FILTERS = ("all", "pending", "completed")
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class TaskManagerError(Exception):
    """Base exception for expected task manager errors."""


class TaskNotFoundError(TaskManagerError):
    """Raised when a requested task ID does not exist."""


class TaskStorageError(TaskManagerError):
    """Raised when the task file cannot be read or written safely."""


@dataclass
class Task:
    """Represent a task and its persisted state."""

    id: int
    title: str
    due_date: str | None = None
    priority: str = "medium"
    completed: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    VALID_PRIORITIES: ClassVar[tuple[str, ...]] = PRIORITIES

    def __post_init__(self) -> None:
        """Validate fields whenever a task object is created."""
        if self.id <= 0:
            raise ValueError("task ID must be positive")
        if not self.title.strip():
            raise ValueError("task title cannot be empty")
        if self.priority not in self.VALID_PRIORITIES:
            raise ValueError("priority must be low, medium, or high")
        if self.due_date is not None:
            validate_due_date(self.due_date)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Build a task from one JSON object, rejecting malformed data."""
        if not isinstance(data, dict):
            raise ValueError("each task must be a JSON object")
        required_fields = {"id", "title", "due_date", "priority", "completed"}
        if not required_fields.issubset(data):
            missing = sorted(required_fields - data.keys())
            raise ValueError(f"missing fields: {', '.join(missing)}")

        task_id = data["id"]
        if isinstance(task_id, bool) or not isinstance(task_id, int):
            raise ValueError("task ID must be an integer")
        if not isinstance(data["title"], str):
            raise ValueError("task title must be a string")
        if data["due_date"] is not None and not isinstance(data["due_date"], str):
            raise ValueError("due date must be a string or null")
        if not isinstance(data["priority"], str):
            raise ValueError("priority must be a string")
        if not isinstance(data["completed"], bool):
            raise ValueError("completed must be true or false")

        created_at = data.get("created_at", "")
        if not isinstance(created_at, str):
            raise ValueError("created_at must be a string")

        return cls(
            id=task_id,
            title=data["title"],
            due_date=data["due_date"],
            priority=data["priority"],
            completed=data["completed"],
            created_at=created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert this task into a JSON-serializable dictionary."""
        return asdict(self)


def validate_due_date(value: str) -> str:
    """Validate and return a due date in ISO ``YYYY-MM-DD`` format."""
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("due date must use YYYY-MM-DD format") from error
    return value


class TaskManager:
    """Manage tasks and persist them to a local JSON file."""

    def __init__(self, file_path: Path | str = DEFAULT_TASK_FILE) -> None:
        """Create a manager and load existing tasks from ``file_path``."""
        self.file_path = Path(file_path)
        self.tasks = self.load_tasks()

    def load_tasks(self) -> list[Task]:
        """Load tasks from JSON, treating a missing file as an empty list."""
        if not self.file_path.exists():
            return []

        try:
            raw_data = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise TaskStorageError(
                f"could not read task file '{self.file_path}': {error}"
            ) from error

        if not isinstance(raw_data, list):
            raise TaskStorageError("task file must contain a JSON list")

        try:
            return [Task.from_dict(item) for item in raw_data]
        except (TypeError, ValueError) as error:
            raise TaskStorageError(f"task file contains invalid data: {error}") from error

    def save_tasks(self) -> None:
        """Save all current tasks to the configured JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(
                [task.to_dict() for task in self.tasks], indent=2
            )
            self.file_path.write_text(f"{content}\n", encoding="utf-8")
        except (OSError, TypeError, ValueError) as error:
            raise TaskStorageError(
                f"could not write task file '{self.file_path}': {error}"
            ) from error

    def add_task(
        self,
        title: str,
        due_date: str | None = None,
        priority: str = "medium",
    ) -> Task:
        """Create, persist, and return a new task."""
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("task title cannot be empty")
        if priority not in PRIORITIES:
            raise ValueError("priority must be low, medium, or high")
        if due_date is not None:
            validate_due_date(due_date)

        task = Task(
            id=self._next_id(),
            title=clean_title,
            due_date=due_date,
            priority=priority,
        )
        self.tasks.append(task)
        self.save_tasks()
        return task

    def list_tasks(self, status: str = "all") -> list[Task]:
        """Return filtered tasks sorted by priority and then due date."""
        if status not in FILTERS:
            raise ValueError("filter must be all, pending, or completed")

        filtered = [
            task
            for task in self.tasks
            if status == "all"
            or (status == "completed" and task.completed)
            or (status == "pending" and not task.completed)
        ]
        return sorted(
            filtered,
            key=lambda task: (
                PRIORITY_ORDER[task.priority],
                task.due_date is None,
                task.due_date or "",
                task.id,
            ),
        )

    def complete_task(self, task_id: int) -> Task:
        """Mark a task complete, persist the change, and return it."""
        task = self._find_task(task_id)
        task.completed = True
        self.save_tasks()
        return task

    def delete_task(self, task_id: int) -> Task:
        """Delete a task, persist the change, and return the deleted task."""
        task = self._find_task(task_id)
        self.tasks.remove(task)
        self.save_tasks()
        return task

    def statistics(self) -> dict[str, int]:
        """Return total, completed, and pending task counts."""
        completed = sum(task.completed for task in self.tasks)
        return {
            "total": len(self.tasks),
            "completed": completed,
            "pending": len(self.tasks) - completed,
        }

    def _find_task(self, task_id: int) -> Task:
        """Find a task by ID or raise a user-friendly error."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise TaskNotFoundError(f"task #{task_id} was not found")

    def _next_id(self) -> int:
        """Return the next available positive task ID."""
        return max((task.id for task in self.tasks), default=0) + 1
