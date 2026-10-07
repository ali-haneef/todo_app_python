"""Command-line interface for the task manager."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from task_manager import Task, TaskManager, TaskManagerError


def positive_integer(value: str) -> int:
    """Convert a command-line value to a positive integer."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error

    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Build and return the application's argument parser."""
    parser = argparse.ArgumentParser(
        description="Manage tasks stored in a local tasks.json file."
    )
    commands = parser.add_subparsers(dest="command", title="commands")

    add_parser = commands.add_parser("add", help="add a new task")
    add_parser.add_argument("title", help="task description")
    add_parser.add_argument(
        "--due",
        "--due-date",
        dest="due_date",
        help="due date in YYYY-MM-DD format",
    )
    add_parser.add_argument(
        "--priority",
        choices=("low", "medium", "high"),
        default="medium",
        help="task priority (default: medium)",
    )

    list_parser = commands.add_parser("list", help="list tasks")
    list_parser.add_argument(
        "--filter",
        choices=("all", "pending", "completed"),
        default="all",
        help="tasks to show (default: all)",
    )

    complete_parser = commands.add_parser(
        "complete", help="mark a task as complete"
    )
    complete_parser.add_argument("task_id", type=positive_integer)

    delete_parser = commands.add_parser("delete", help="delete a task")
    delete_parser.add_argument("task_id", type=positive_integer)

    commands.add_parser("stats", help="show task statistics")
    return parser


def format_task(task: Task) -> str:
    """Format one task for terminal output."""
    status = "x" if task.completed else " "
    due_date = task.due_date or "no due date"
    return (
        f"[{status}] #{task.id} [{task.priority.upper():6}] "
        f"{due_date:10} {task.title}"
    )


def print_tasks(tasks: list[Task]) -> None:
    """Print a collection of tasks or a helpful empty-state message."""
    if not tasks:
        print("No tasks found.")
        return

    for task in tasks:
        print(format_task(task))


def run_command(args: argparse.Namespace) -> int:
    """Execute a parsed command and return its process exit code."""
    manager = TaskManager()

    if args.command == "add":
        task = manager.add_task(args.title, args.due_date, args.priority)
        print(f"Added task #{task.id}: {task.title}")
    elif args.command == "list":
        print_tasks(manager.list_tasks(args.filter))
    elif args.command == "complete":
        task = manager.complete_task(args.task_id)
        print(f"Completed task #{task.id}: {task.title}")
    elif args.command == "delete":
        task = manager.delete_task(args.task_id)
        print(f"Deleted task #{task.id}: {task.title}")
    elif args.command == "stats":
        statistics = manager.statistics()
        print(f"Total: {statistics['total']}")
        print(f"Completed: {statistics['completed']}")
        print(f"Pending: {statistics['pending']}")
    else:
        return 0

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line arguments, run the requested command, and exit."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        return run_command(args)
    except (TaskManagerError, ValueError) as error:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
