# TaskFlow

TaskFlow is a browser-based task manager built with Flask, SQLite, and vanilla JavaScript. It has no frontend build step and uses only Flask as an external Python dependency.

## Run locally

From this directory, create a virtual environment and install Flask:

python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py

Open http://127.0.0.1:5000 in your browser. The SQLite database is created automatically at instance/taskflow.db.

## Features

- Create tasks with title, notes, due date, and low/medium/high priority
- View, search, filter, and sort tasks without page reloads
- Mark tasks complete or move them back to pending
- Edit and delete tasks
- Dashboard counts for total, pending, completed, and due-today tasks
- JSON API backed by parameterized SQLite queries

## API

The browser uses these endpoints:

- GET /api/tasks
- POST /api/tasks
- PATCH /api/tasks/<id>
- DELETE /api/tasks/<id>
- GET /api/stats
