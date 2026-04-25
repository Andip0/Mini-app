# Parallel Job Runner

A demo app that shows how FastAPI, Celery, Redis and Docker work together to run background tasks in parallel.

## What it does

You submit a list of numbers through a simple web form, choose an operation (square, cube or factorial), and the app processes all the numbers in parallel in the background using Celery workers. The frontend polls for results every 800ms and displays them when done.

## How to run it

Make sure Docker Desktop is running first.

Then open a terminal inside the project folder and run:

```
docker compose up --build
```

Wait until you see these two lines in the terminal:

```
api-1     | INFO:     Application startup complete.
worker-1  | celery@... ready.
```

Then open your browser and go to:

```
http://localhost:8000
```

To stop the app press Ctrl + C in the terminal.

## Project structure

```
celery-demo/
├── docker-compose.yml        — starts all 3 services together
├── backend/
│   ├── main.py               — FastAPI endpoints
│   ├── tasks.py              — Celery tasks and chord pattern
│   ├── schemas.py            — Pydantic request and response models
│   ├── requirements.txt      — Python dependencies
│   └── Dockerfile            — builds the Python container
└── frontend/
    ├── index.html            — the web form
    ├── style.css             — styling
    └── script.js             — polling logic and result display
```

## How it works

1. You submit numbers through the frontend
2. FastAPI receives the request, validates it with Pydantic, and creates a Celery chord
3. The chord fans out one task per number — all running in parallel across Celery workers
4. Redis acts as the message broker (holds tasks in a queue) and result backend (stores finished results)
5. The frontend polls GET /job-status/{job_id} every 800ms until results are ready
6. Results and summary stats are displayed on the page

## Tech stack

- **FastAPI** — Python web framework for the API and frontend serving
- **Celery** — background task queue with parallel processing using chord pattern
- **Redis** — message broker and result backend
- **Docker Compose** — runs all three services together with one command
