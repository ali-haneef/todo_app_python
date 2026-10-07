# TaskFlow

TaskFlow is a local task manager with two ways to use it:

- **Web app:** a Flask application with a browser interface and SQLite storage.
- **Command-line app:** a small terminal interface that stores tasks in `tasks.json`.

The web app has no frontend build step. Flask is its only third-party dependency.

## Requirements

- [Git](https://git-scm.com/downloads)
- Python **3.10 or newer** (check with `python --version`)
- A modern web browser for the web interface

> On some systems, use `python3` in place of `python` in the commands below.

## Clone and run the web app

1. Clone the repository and enter the project directory:

   ```bash
   git clone https://github.com/<your-account>/todo_app_python.git
   cd todo_app_python
   ```

   Replace `<your-account>` with the GitHub account or organization that owns this repository.

2. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

3. Activate it.

   **Windows PowerShell**

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   **Windows Command Prompt**

   ```bat
   .venv\Scripts\activate.bat
   ```

   **macOS/Linux**

   ```bash
   source .venv/bin/activate
   ```

   If PowerShell blocks the activation script, run this once for the current terminal and then activate again:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

4. Install the application dependency:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

5. Start the development server:

   ```bash
   python app.py
   ```

6. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. Stop the server with `Ctrl+C`.

The database is initialized automatically on first start at `instance/taskflow.db`. No environment variables or separate database server are required.

## Using the web app

- Create tasks with a title, optional notes, due date, and low/medium/high priority.
- Search, filter by status, and sort tasks without reloading the page.
- Edit tasks, mark them complete, or delete them.
- View counts for total, pending, completed, and tasks due today.

## Command-line interface (optional)

The CLI uses the standard library only and saves its data in `tasks.json` in the project directory. It does not require Flask, although installing the project dependencies as above is fine.

```bash
# Show available commands
python main.py --help

# Add a task
python main.py add "Prepare release notes" --due 2030-04-15 --priority high

# List tasks (all, pending, or completed)
python main.py list --filter pending

# Complete or delete a task by its ID
python main.py complete 1
python main.py delete 1

# Show totals
python main.py stats
```

## Run tests

With the virtual environment active and dependencies installed, run:

```bash
python -m unittest discover -s tests -v
```

The tests use temporary databases and task files, so they do not modify your normal application data.

## Data and reset behavior

- Web-app tasks are stored in `instance/taskflow.db`.
- CLI tasks are stored in `tasks.json`.
- The two interfaces use separate storage and do not share tasks.
- To reset the web app, stop the server and delete `instance/taskflow.db`; it will be recreated the next time `python app.py` runs.
- To reset the CLI, replace the contents of `tasks.json` with `[]`.

## Project layout

```text
app.py              Flask application and JSON API
templates/          Web page template
static/             Browser JavaScript and styles
instance/           SQLite database created/used by the web app
main.py             Command-line entry point
task_manager.py     CLI task-management logic
tasks.json          CLI task storage
tests/              Automated tests
requirements.txt    Python dependencies
```

## API endpoints

The browser interface calls these JSON endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/tasks` | List tasks; supports `filter`, `search`, and `sort` query parameters |
| `POST` | `/api/tasks` | Create a task |
| `PATCH` | `/api/tasks/<id>` | Update a task |
| `DELETE` | `/api/tasks/<id>` | Delete a task |
| `GET` | `/api/stats` | Get task totals |

For development only, `app.py` runs Flask with debug mode enabled. Use a production WSGI server and appropriate configuration before exposing the application publicly.
