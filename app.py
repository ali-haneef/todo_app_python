"""TaskFlow: a small Flask and SQLite task manager web application."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
VALID_PRIORITIES = frozenset({"low", "medium", "high"})
VALID_FILTERS = frozenset({"all", "pending", "completed"})


class APIError(Exception):
    """Represent an expected API error with an HTTP status code."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        """Create an API error with a client-safe message."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code


app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    DATABASE=str(Path(app.instance_path) / "taskflow.db"),
    JSON_SORT_KEYS=False,
)


def get_db() -> sqlite3.Connection:
    """Return the request-scoped SQLite connection."""
    if "db" not in g:
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(exception: BaseException | None) -> None:
    """Close the request-scoped database connection when the context ends."""
    del exception
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    """Create the application database and tasks table if needed."""
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    connection = get_db()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            due_date TEXT,
            priority TEXT NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high')),
            completed INTEGER NOT NULL DEFAULT 0
                CHECK (completed IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def serialize_task(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a SQLite task row into a JSON-ready dictionary."""
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "due_date": row["due_date"],
        "priority": row["priority"],
        "completed": bool(row["completed"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def require_json_object() -> dict[str, Any]:
    """Read a JSON object from the request or raise a readable API error."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise APIError("Request body must be a JSON object.")
    return payload


def validate_task_fields(
    payload: dict[str, Any],
    partial: bool = False,
) -> dict[str, Any]:
    """Validate task input and return normalized values for database writes."""
    allowed_fields = {"title", "description", "due_date", "priority", "completed"}
    unknown_fields = set(payload) - allowed_fields
    if unknown_fields:
        names = ", ".join(sorted(unknown_fields))
        raise APIError(f"Unknown field(s): {names}.")
    if partial and not payload:
        raise APIError("At least one task field is required.")

    values: dict[str, Any] = {}

    if not partial or "title" in payload:
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            raise APIError("Title is required.")
        if len(title.strip()) > 200:
            raise APIError("Title must be 200 characters or fewer.")
        values["title"] = title.strip()

    if not partial or "description" in payload:
        description = payload.get("description", "")
        if not isinstance(description, str):
            raise APIError("Description must be text.")
        if len(description) > 2000:
            raise APIError("Description must be 2,000 characters or fewer.")
        values["description"] = description.strip()

    if not partial or "due_date" in payload:
        due_date = payload.get("due_date") or None
        if due_date is not None:
            if not isinstance(due_date, str):
                raise APIError("Due date must be a date or empty.")
            try:
                date.fromisoformat(due_date)
            except ValueError as error:
                raise APIError("Due date must use YYYY-MM-DD format.") from error
        values["due_date"] = due_date

    if not partial or "priority" in payload:
        priority = payload.get("priority", "medium")
        if priority not in VALID_PRIORITIES:
            raise APIError("Priority must be low, medium, or high.")
        values["priority"] = priority

    if "completed" in payload:
        completed = payload["completed"]
        if not isinstance(completed, bool):
            raise APIError("Completed must be true or false.")
        values["completed"] = completed

    return values


def fetch_task(task_id: int) -> sqlite3.Row:
    """Fetch a task by ID or raise a 404 API error."""
    row = get_db().execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        raise APIError("Task not found.", 404)
    return row


def build_task_order(sort_by: str) -> str:
    """Return a safe SQL ORDER BY clause for the requested sort mode."""
    orderings = {
        "priority": (
            "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 "
            "WHEN 'low' THEN 3 END, "
            "CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, id DESC"
        ),
        "due_date": (
            "CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, "
            "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 "
            "WHEN 'low' THEN 3 END, id DESC"
        ),
        "newest": "created_at DESC, id DESC",
        "oldest": "created_at ASC, id ASC",
    }
    return orderings.get(sort_by, orderings["priority"])


@app.get("/")
def index() -> str:
    """Render the TaskFlow single-page application."""
    return render_template("index.html")


@app.get("/api/tasks")
def list_tasks() -> Any:
    """Return tasks filtered by status and optional search text."""
    status = request.args.get("filter", "all")
    if status not in VALID_FILTERS:
        raise APIError("Filter must be all, pending, or completed.")

    search = request.args.get("search", "").strip()
    if len(search) > 100:
        raise APIError("Search text must be 100 characters or fewer.")
    sort_by = request.args.get("sort", "priority")
    conditions: list[str] = []
    parameters: list[Any] = []

    if status == "pending":
        conditions.append("completed = 0")
    elif status == "completed":
        conditions.append("completed = 1")
    if search:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        search_pattern = f"%{search}%"
        parameters.extend([search_pattern, search_pattern])

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM tasks{where_clause} ORDER BY {build_task_order(sort_by)}"
    rows = get_db().execute(query, parameters).fetchall()
    return jsonify({"tasks": [serialize_task(row) for row in rows]})


@app.post("/api/tasks")
def create_task() -> tuple[Any, int]:
    """Validate and create a task, returning it with HTTP 201."""
    values = validate_task_fields(require_json_object())
    timestamp = utc_now()
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO tasks
            (title, description, due_date, priority, completed, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["title"],
            values["description"],
            values["due_date"],
            values["priority"],
            int(values.get("completed", False)),
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    row = fetch_task(cursor.lastrowid)
    return jsonify({"task": serialize_task(row)}), 201


@app.patch("/api/tasks/<int:task_id>")
def update_task(task_id: int) -> Any:
    """Update any supplied task fields and return the updated task."""
    fetch_task(task_id)
    values = validate_task_fields(require_json_object(), partial=True)
    assignments = [f"{field} = ?" for field in values]
    parameters = [
        int(value) if field == "completed" else value
        for field, value in values.items()
    ]
    assignments.append("updated_at = ?")
    parameters.append(utc_now())
    parameters.append(task_id)
    connection = get_db()
    connection.execute(
        f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?", parameters
    )
    connection.commit()
    return jsonify({"task": serialize_task(fetch_task(task_id))})


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id: int) -> tuple[Any, int]:
    """Delete a task by ID and return a confirmation response."""
    fetch_task(task_id)
    connection = get_db()
    connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    connection.commit()
    return jsonify({"message": "Task deleted."}), 200


@app.get("/api/stats")
def task_stats() -> Any:
    """Return task counts for the dashboard summary cards."""
    connection = get_db()
    counts = connection.execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(completed), 0) AS completed,
            COALESCE(SUM(completed = 0), 0) AS pending,
            COALESCE(SUM(completed = 0 AND due_date = date('now')), 0) AS due_today
        FROM tasks
        """
    ).fetchone()
    return jsonify(
        {
            "total": counts["total"],
            "completed": counts["completed"],
            "pending": counts["pending"],
            "due_today": counts["due_today"],
        }
    )


@app.errorhandler(APIError)
def handle_api_error(error: APIError) -> tuple[Any, int]:
    """Return expected API errors as consistent JSON responses."""
    return jsonify({"error": error.message}), error.status_code


@app.errorhandler(404)
def handle_not_found(error: Any) -> Any:
    """Return JSON for missing API routes and the normal page for web routes."""
    del error
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found."}), 404
    return render_template("index.html"), 200


@app.errorhandler(405)
def handle_method_not_allowed(error: Any) -> Any:
    """Return method errors in the same JSON format as other API errors."""
    del error
    if request.path.startswith("/api/"):
        return jsonify({"error": "Method not allowed."}), 405
    return "Method not allowed.", 405


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
