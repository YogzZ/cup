# Cup Sports Event Website

## Project Overview

This project is a web application for managing sports events. It consists of a FastAPI backend with a SQLite database and a separate frontend application.

## Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd cup
    ```

2.  **Set up the backend:**

    Navigate to the backend directory (assuming it's the root `cup` directory where `main.py` and `pyproject.toml` are located).

    Install dependencies using Poetry:

    ```bash
    poetry install
    ```

3.  **Set up the frontend:**

    Navigate to the frontend directory:

    ```bash
    cd my-cup-frontend
    ```

    Install dependencies using npm or yarn:

    ```bash
    npm install
    # or yarn install
    ```

## Database Initialization

The project uses a SQLite database (`cup.db`). The database schema is defined in `schema.sql`.

If the `cup.db` file does not exist, it will be created and initialized with the schema when you run the backend for the first time.

To manually re-initialize the database (e.g., for development), you can delete the `cup.db` file and restart the backend.

## Running the Application

1.  **Run the backend:**

    Navigate back to the project root directory (`cup`).

    ```bash
    poetry run uvicorn main:app --reload
    ```

    The backend will run on `http://127.0.0.1:8000` by default.

2.  **Run the frontend:**

    Navigate to the frontend directory (`my-cup-frontend`).

    ```bash
    npm run dev
    # or yarn dev
    ```

    The frontend will typically run on `http://localhost:5173`.

## Testing

Currently, there are no explicit automated tests included in the repository. You can perform manual testing by:

1.  Running both the backend and frontend applications as described above.
2.  Accessing the frontend in your web browser (usually `http://localhost:5173`).
3.  Testing user registration and login.
4.  Testing the functionalities available to regular users.
5.  Logging in with the admin user you created and testing the administrator features (e.g., creating events, managing users, adding match results).

If API endpoints are documented (e.g., via Swagger UI at `/docs` on the backend), you can also test them directly using tools like curl, Postman, or the interactive documentation. 