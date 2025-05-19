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

## Creating an Admin User

By default, user registration creates regular 'player' users. To access administrator functionalities (like managing users, events, matches, and results), you need an 'organizer' user.

Since there is no direct registration endpoint for administrators, you need to manually insert an admin user into the database:

1.  **Stop the backend application.**

2.  **Generate a hashed password** for your desired admin password. You can use a Python script with the `passlib` library (used in `main.py`):

    First, ensure you have `passlib` installed (`poetry add passlib[bcrypt]` in the backend directory or `pip install passlib[bcrypt]` in your environment).

    Run this Python code, replacing `'your_admin_password'` with your chosen password:

    ```python
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(password):
        return pwd_context.hash(password)

    hashed_admin_password = get_password_hash('your_admin_password')
    print(hashed_admin_password)
    ```

    Copy the output (the hashed password).

3.  **Use a SQLite database tool** (like `sqlite3` or DB Browser for SQLite) to open the `cup.db` file.

4.  **Execute an SQL INSERT statement** to add the admin user. Replace `'admin_username'` with your desired username and `'hashed_password_from_step_2'` with the hashed password you generated:

    ```sql
    INSERT INTO users (username, password_hash, role) VALUES ('admin_username', 'hashed_password_from_step_2', 'organizer');
    ```

5.  **Save the changes** and close the database tool.

6.  **Restart the backend application.**

You can now log in using the admin username and password you created.

## Testing

Currently, there are no explicit automated tests included in the repository. You can perform manual testing by:

1.  Running both the backend and frontend applications as described above.
2.  Accessing the frontend in your web browser (usually `http://localhost:5173`).
3.  Testing user registration and login.
4.  Testing the functionalities available to regular users.
5.  Logging in with the admin user you created and testing the administrator features (e.g., creating events, managing users, adding match results).

If API endpoints are documented (e.g., via Swagger UI at `/docs` on the backend), you can also test them directly using tools like curl, Postman, or the interactive documentation. 