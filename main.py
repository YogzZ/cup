import os
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, File, UploadFile, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone, date, time
import aiofiles
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# Database configuration
DATABASE_URL = "sqlite:///./cup.db"

# Create a SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize the database
def init_db():
    # Check if database file exists, if not, create tables
    if not os.path.exists("./cup.db"):
        try:
            with engine.connect() as connection:
                with open("schema.sql") as f:
                    # Read the SQL commands from the schema file
                    schema_sql = f.read()
                    # Execute each command to create tables
                    for statement in schema_sql.split(';'):
                        statement = statement.strip()
                        if statement:
                            # Wrap the statement with text()
                            connection.execute(text(statement))
            print("Database initialized successfully.")
        except OperationalError as e:
            print(f"Error initializing database: {e}")

    # Add a default admin user if the database is empty (or admin doesn't exist)
    try:
        with engine.connect() as connection:
            # Check if the admin user already exists
            admin_username = "admin"
            existing_admin = connection.execute(text("SELECT id FROM users WHERE username = :username"), {"username": admin_username}).fetchone()

            if not existing_admin:
                # Hardcoded password - CHANGE THIS IMMEDIATELY AFTER FIRST LOGIN!
                admin_password = "changeme" # !!! SECURITY RISK - CHANGE THIS !!!
                hashed_admin_password = get_password_hash(admin_password)

                # Insert the default admin user
                connection.execute(
                    text("INSERT INTO users (username, password_hash, role) VALUES (:username, :password_hash, :role)"),
                    {"username": admin_username, "password_hash": hashed_admin_password, "role": "organizer"}
                )
                connection.commit()
                print(f"Default admin user '{admin_username}' created. PLEASE CHANGE THE PASSWORD IMMEDIATELY!")
            else:
                print(f"Admin user '{admin_username}' already exists.")

    except OperationalError as e:
        print(f"Error creating default admin user: {e}")

# Create FastAPI app
app = FastAPI()

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:5173", # Allow requests from your frontend development server
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    # Add other origins if your frontend will be hosted elsewhere
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], # Allow all headers (including Authorization)
)

# Custom middleware for logging requests and responses
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n>>> Request: {request.method} {request.url}")

    # Log request body for relevant methods
    try:
        body = await request.body()
        if body:
            print(f"Request body: {body.decode()}")
    except Exception as e:
        print(f"Could not read request body: {e}")

    response = await call_next(request)

    print(f"<<< Response: {response.status_code}")

    # Log response body - need to read and then stream it back
    try:
        # Read the response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        # Print the response body
        print(f"Response body: {response_body.decode()}")

        # Create a new response with the same body, status, and headers
        return Response(content=response_body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

    except Exception as e:
        print(f"Could not read or process response body for logging: {e}")
        # If reading response body fails, just return the original response
        return response

# Mount static files directory
UPLOAD_DIRECTORY = "./uploads"
STATIC_URL_PATH = "/static/uploads"
MAX_FILE_SIZE = 5 * 1024 * 1024 # 5 MB in bytes
ALLOWED_FILE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"} # Allowed image extensions

# Create upload directory if it doesn't exist
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

app.mount(STATIC_URL_PATH, StaticFiles(directory=UPLOAD_DIRECTORY), name="static_uploads")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration (replace with a strong, unique secret in production)
SECRET_KEY = "YOUR_SUPER_SECRET_KEY" # CHANGE THIS IN PRODUCTION
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# Dependency to get DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic model for user registration
class UserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None

# Pydantic model for user login
class UserLogin(BaseModel):
    username: str
    password: str

# Pydantic model for event registration
class EventRegistrationCreate(BaseModel):
    event_id: int

# Pydantic model for event creation (for organizers)
class EventCreate(BaseModel):
    name: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    mode: str = "knockout" # New field with default

# Pydantic model for event response
class EventResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    mode: str # New field

    class Config:
        orm_mode = True

# Pydantic model for event update (Organizer)
class EventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    mode: str | None = None # New field

# Pydantic model for user's match history response
class UserMatchHistory(BaseModel):
    match_id: int
    event_id: int
    event_name: str
    stage: str | None = None
    match_date: date | None = None
    match_time: time | None = None
    user1_id: int | None = None
    user1_username: str | None = None
    user2_id: int | None = None
    user2_username: str | None = None
    venue: str | None = None
    user1_score: int | None = None
    user2_score: int | None = None
    winner_user_id: int | None = None

# Pydantic model for match creation (Organizer)
class MatchCreate(BaseModel):
    event_id: int
    stage: str | None = None
    match_date: date | None = None
    match_time: time | None = None
    user1_id: int # User ID for the first participant
    user2_id: int # User ID for the second participant
    venue: str | None = None
    user1_screenshot_url: str | None = None # New field
    user1_tactics_url: str | None = None # New field
    user2_screenshot_url: str | None = None # New field
    user2_tactics_url: str | None = None # New field

# Pydantic model for match update (Organizer)
class MatchUpdate(BaseModel):
    event_id: int | None = None
    stage: str | None = None
    match_date: date | None = None
    match_time: time | None = None
    user1_id: int | None = None
    user2_id: int | None = None
    venue: str | None = None
    user1_screenshot_url: str | None = None # New field
    user1_tactics_url: str | None = None # New field
    user2_screenshot_url: str | None = None # New field
    user2_tactics_url: str | None = None # New field

# Pydantic model for result creation (Organizer)
class ResultCreate(BaseModel):
    match_id: int
    user1_score: int | None = None
    user2_score: int | None = None
    winner_user_id: int | None = None # Should be one of the users in the match

# Pydantic model for result update (Organizer)
class ResultUpdate(BaseModel):
    user1_score: int | None = None
    user2_score: int | None = None
    winner_user_id: int | None = None

# Pydantic model for match response
class MatchResponse(BaseModel):
    id: int
    event_id: int
    stage: str | None = None
    match_date: date | None = None
    match_time: time | None = None
    user1_id: int | None = None
    user1_username: str | None = None
    user2_id: int | None = None
    user2_username: str | None = None
    venue: str | None = None
    user1_screenshot_url: str | None = None # New field
    user1_tactics_url: str | None = None # New field
    user2_screenshot_url: str | None = None # New field
    user2_tactics_url: str | None = None # New field

    class Config:
        orm_mode = True

# Pydantic model for result response
class ResultResponse(BaseModel):
    id: int
    match_id: int
    user1_score: int | None = None
    user2_score: int | None = None
    winner_user_id: int | None = None

    class Config:
        orm_mode = True

# Pydantic model for user response
class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    registration_date: datetime
    role: str

    class Config:
        orm_mode = True

# Pydantic model for participant response
class ParticipantResponse(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True

# Pydantic model for user update (Organizer)
class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    role: str | None = None # Be careful with role updates
    password: str | None = None # Allow password change

# Pydantic model for user profile update (Regular User)
class UserProfileUpdate(BaseModel):
    username: str | None = None
    email: str | None = None

# Pydantic model for token with role
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

# User registration endpoint
@app.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if username already exists
    existing_user = db.execute(text("SELECT id FROM users WHERE username = :username"), {"username": user.username}).fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Hash the password
    hashed_password = get_password_hash(user.password)

    # Insert new user into the database
    db.execute(
        text("INSERT INTO users (username, password_hash, email) VALUES (:username, :password_hash, :email)"),
        {"username": user.username, "password_hash": hashed_password, "email": user.email}
    )
    db.commit()

    return {"message": "User registered successfully"}

# User login endpoint
@app.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Print received username
    print(f"\nAttempting login for username: {form_data.username}")

    # Authenticate user
    # Fetch role along with id and password_hash
    user_row = db.execute(text("SELECT id, password_hash, role FROM users WHERE username = :username"), {"username": form_data.username}).fetchone()

    # Print user data fetched from DB
    print(f"Fetched user data from DB: {user_row}")

    if not user_row or not verify_password(form_data.password, user_row[1]):
        print("Authentication failed.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    print("Authentication successful.")

    # Convert user_row to dictionary for easier access
    user = dict(user_row._mapping)

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Include user role in the token data
    access_token_data = {"sub": form_data.username, "role": user['role']}
    print(f"Data included in access token: {access_token_data}")

    access_token = create_access_token(
        data=access_token_data, expires_delta=access_token_expires
    )

    # Prepare response data using the Pydantic model
    response_data = Token(access_token=access_token, token_type="bearer", role=user['role'])
    print(f"Returning login response: {response_data.model_dump_json()}") # Print JSON representation

    return response_data

# Dependency to get current user (requires authentication)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = verify_token(token, credentials_exception)
    # Fetch user with role to determine permissions
    user = db.execute(text("SELECT id, username, role FROM users WHERE username = :username"), {"username": username}).fetchone()
    if user is None:
        raise credentials_exception
    # Convert SQLAlchemy Row to dictionary for consistent access
    # Use ._mapping for reliable conversion
    return dict(user._mapping)

# Dependency to check if user is an organizer
def is_organizer(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'organizer':
        raise HTTPException(status_code=403, detail="Operation not permitted")
    return current_user

# Create a new event (Organizer only)
@app.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(event: EventCreate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Insert new event into the database
    db.execute(
        text("INSERT INTO events (name, description, start_date, end_date, mode) VALUES (:name, :description, :start_date, :end_date, :mode)"),
        {"name": event.name, "description": event.description, "start_date": event.start_date, "end_date": event.end_date, "mode": event.mode}
    )
    db.commit()

    return {"message": "Event created successfully"}

# Get all events (Currently public, could add is_organizer if needed)
@app.get("/events", response_model=list[EventResponse])
def get_events(db: Session = Depends(get_db)):
    events = db.execute(text("SELECT id, name, description, start_date, end_date, mode FROM events")).fetchall()
    return events

# Get a specific event by ID (Organizer only)
@app.get("/events/{event_id}", response_model=EventResponse)
def get_event(event_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    event = db.execute(text("SELECT id, name, description, start_date, end_date, mode FROM events WHERE id = :id"), {"id": event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

# Update an event by ID (Organizer only)
@app.put("/events/{event_id}", response_model=EventResponse)
def update_event(event_id: int, event_update: EventUpdate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if event exists
    existing_event = db.execute(text("SELECT id FROM events WHERE id = :id"), {"id": event_id}).fetchone()
    if not existing_event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_fields = event_update.model_dump(exclude_unset=True)
    if not update_fields:
        return existing_event # No fields to update

    # Construct update query dynamically
    set_clauses = [f"{key} = :{key}" for key in update_fields]
    query = text(f"UPDATE events SET {', '.join(set_clauses)} WHERE id = :id")
    update_fields["id"] = event_id

    db.execute(query, update_fields)
    db.commit()

    # Fetch the updated event to return in the response
    updated_event = db.execute(text("SELECT id, name, description, start_date, end_date, mode FROM events WHERE id = :id"), {"id": event_id}).fetchone()
    return updated_event

# Delete an event by ID (Organizer only)
@app.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if event exists
    existing_event = db.execute(text("SELECT id FROM events WHERE id = :id"), {"id": event_id}).fetchone()
    if not existing_event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
    db.commit()
    return # No content to return for 204

# Get matches for a specific event
@app.get("/events/{event_id}/matches", response_model=list[MatchResponse])
def get_event_matches(event_id: int, db: Session = Depends(get_db)):
    # Check if event exists (optional, but good practice)
    event = db.execute(text("SELECT id FROM events WHERE id = :event_id"), {"event_id": event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    matches = db.execute(text("SELECT id, event_id, stage, match_date, match_time, user1_id, user2_id, venue, user1_screenshot_url, user1_tactics_url, user2_screenshot_url, user2_tactics_url FROM matches WHERE event_id = :event_id"), {"event_id": event_id}).fetchall()
    return matches

# Get results for a specific match
@app.get("/matches/{match_id}/results", response_model=ResultResponse | None)
def get_match_results(match_id: int, db: Session = Depends(get_db)):
    # Check if match exists (optional)
    match = db.execute(text("SELECT id FROM matches WHERE id = :match_id"), {"match_id": match_id}).fetchone()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    result = db.execute(text("SELECT id, match_id, user1_score, user2_score, winner_user_id FROM results WHERE match_id = :match_id"), {"match_id": match_id}).fetchone()
    return result # Returns None if no result found for the match

# User registration for an event (individual)
@app.post("/events/{event_id}/register")
def register_for_event(event_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user['id']

    # Check if event exists
    event = db.execute(text("SELECT id FROM events WHERE id = :event_id"), {"event_id": event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if user is already registered for this event
    existing_registration = db.execute(
        text("SELECT user_id FROM event_registrations WHERE user_id = :user_id AND event_id = :event_id"),
        {"user_id": user_id, "event_id": event_id}
    ).fetchone()
    if existing_registration:
        raise HTTPException(status_code=400, detail="User already registered for this event")

    # Register user for the event
    db.execute(
        text("INSERT INTO event_registrations (user_id, event_id) VALUES (:user_id, :event_id)"),
        {"user_id": user_id, "event_id": event_id}
    )
    db.commit()

    return {"message": "Successfully registered for the event"}

# User join event endpoint (same logic as register, but perhaps a clearer name from user perspective)
# Re-using the existing register endpoint for now, but defining a separate path for clarity.
# If different logic is needed for 'join' vs 'register' in the future, this can be modified.
@app.post("/events/{event_id}/join", status_code=status.HTTP_201_CREATED)
def join_event(event_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # This endpoint is functionally identical to register_for_event based on current requirements.
    # We call the existing registration logic.
    return register_for_event(event_id=event_id, current_user=current_user, db=db)

# User leave event endpoint
@app.delete("/events/{event_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_event(event_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user['id']

    # Check if registration exists
    existing_registration = db.execute(
        text("SELECT user_id FROM event_registrations WHERE user_id = :user_id AND event_id = :event_id"),
        {"user_id": user_id, "event_id": event_id}
    ).fetchone()
    if not existing_registration:
        raise HTTPException(status_code=404, detail="User is not registered for this event")

    # Delete the registration
    db.execute(
        text("DELETE FROM event_registrations WHERE user_id = :user_id AND event_id = :event_id"),
        {"user_id": user_id, "event_id": event_id}
    )
    db.commit()

    return # No content to return for 204

# Get current user's profile
@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # current_user already contains the necessary info (id, username, role)
    # We might want to fetch full details from DB if needed, but current_user is enough for now
    # Based on the previous search results, current_user dict includes id, username, and role.
    # Let's fetch the email as well for completeness in the response model.
    # Fix for AttributeError: 'Depends' object has no attribute 'execute'
    # Ensure db is a Session object
    if not isinstance(db, Session):
         raise HTTPException(status_code=500, detail="Database session dependency injection failed.")

    user = db.execute(text("SELECT id, username, email, registration_date, role FROM users WHERE id = :id"), {"id": current_user['id']}).fetchone()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Convert the SQLAlchemy Row to a dictionary for the Pydantic model
    user_dict = dict(user)

    return UserResponse(**user_dict)

# Update current user's profile
@app.put("/users/me", response_model=UserResponse)
def update_users_me(user_update: UserProfileUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user['id']

    # Check if user exists (should always exist based on get_current_user)
    existing_user = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not existing_user:
         raise HTTPException(status_code=404, detail="User not found")

    update_fields = user_update.model_dump(exclude_unset=True)
    # Ensure role and password cannot be updated via this endpoint
    update_fields.pop('role', None)
    update_fields.pop('password', None)

    if not update_fields:
        # No fields to update, return existing user data
        updated_user = db.execute(text("SELECT id, username, email, registration_date, role FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        return updated_user

    # Construct update query dynamically for allowed fields
    set_clauses = [f"{key} = :{key}" for key in update_fields]
    query = text(f"UPDATE users SET {', '.join(set_clauses)} WHERE id = :id")

    # Add user_id to update_fields for the WHERE clause
    update_fields["id"] = user_id

    db.execute(query, update_fields)
    db.commit()

    # Fetch the updated user to return in the response
    updated_user = db.execute(text("SELECT id, username, email, registration_date, role FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    return updated_user

# Root endpoint
@app.get("/")
def read_root():
    return {"Hello": "World"}

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db() 

def create_access_token(
    data: dict, expires_delta: timedelta | None = None
):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(
    token: str,
    credentials_exception
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception 

# Create a new user (Organizer only)
@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if username already exists
    existing_user = db.execute(text("SELECT id FROM users WHERE username = :username"), {"username": user.username}).fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Hash the password
    hashed_password = get_password_hash(user.password)

    # Insert new user into the database
    result = db.execute(
        text("INSERT INTO users (username, password_hash, email) VALUES (:username, :password_hash, :email) RETURNING id"),
        {"username": user.username, "password_hash": hashed_password, "email": user.email}
    )
    new_user_id = result.fetchone()[0]
    db.commit()

    # Fetch the newly created user to return in the response
    created_user = db.execute(text("SELECT id, username, email, registration_date, role FROM users WHERE id = :id"), {"id": new_user_id}).fetchone()
    return created_user

# Get all users (Organizer only)
@app.get("/users", response_model=list[UserResponse])
def get_all_users(current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    users = db.execute(text("SELECT id, username, email, registration_date, role FROM users")).fetchall()
    return users

# Get a specific user by ID (Organizer only)
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    user = db.execute(text("SELECT id, username, email, registration_date, role FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Update a user by ID (Organizer only)
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.execute(text("SELECT id, password_hash FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_fields = user_update.model_dump(exclude_unset=True)
    if not update_fields:
        return existing_user # No fields to update

    # Handle password update separately
    if "password" in update_fields:
        update_fields["password_hash"] = get_password_hash(update_fields.pop("password"))

    # Construct update query dynamically
    set_clauses = [f"{key} = :{key}" for key in update_fields]
    if not set_clauses:
        return existing_user # Should be caught by empty update_fields check, but as a safeguard

    query = text(f"UPDATE users SET {', '.join(set_clauses)} WHERE id = :id")
    update_fields["id"] = user_id

    db.execute(query, update_fields)
    db.commit()

    # Fetch the updated user to return in the response
    updated_user = db.execute(text("SELECT id, username, email, registration_date, role FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    return updated_user

# Delete a user by ID (Organizer only)
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find all matches where this user is a participant and get file URLs
    user_matches_files = db.execute(text("""
        SELECT
            user1_id,
            user1_screenshot_url,
            user1_tactics_url,
            user2_id,
            user2_screenshot_url,
            user2_tactics_url
        FROM matches
        WHERE user1_id = :user_id OR user2_id = :user_id
    """), {"user_id": user_id}).fetchall()

    # Collect all file URLs associated with this user
    file_urls_to_delete = []
    for match in user_matches_files:
        if match['user1_id'] == user_id:
            if match['user1_screenshot_url']: file_urls_to_delete.append(match['user1_screenshot_url'])
            if match['user1_tactics_url']: file_urls_to_delete.append(match['user1_tactics_url'])
        if match['user2_id'] == user_id:
            if match['user2_screenshot_url']: file_urls_to_delete.append(match['user2_screenshot_url'])
            if match['user2_tactics_url']: file_urls_to_delete.append(match['user2_tactics_url'])

    # Delete associated files
    for file_url in file_urls_to_delete:
        if file_url:
            # Construct local file path from URL
            filename = os.path.basename(file_url)
            file_local_path = os.path.join(UPLOAD_DIRECTORY, filename)
            try:
                if os.path.exists(file_local_path):
                    os.remove(file_local_path)
                    print(f"Deleted file: {file_local_path}") # Optional: log deletion
                else:
                    print(f"File not found for deletion: {file_local_path}") # Optional: log file not found
            except OSError as e:
                print(f"Error deleting file {file_local_path}: {e}") # Optional: log error

    # Delete the user record from the database
    db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    db.commit()

    return # No content to return for 204

# Create a new match (Organizer only)
@app.post("/matches", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
def create_match(match: MatchCreate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if event exists
    event = db.execute(text("SELECT id FROM events WHERE id = :event_id"), {"event_id": match.event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if users exist
    user1 = db.execute(text("SELECT id FROM users WHERE id = :user1_id"), {"user1_id": match.user1_id}).fetchone()
    user2 = db.execute(text("SELECT id FROM users WHERE id = :user2_id"), {"user2_id": match.user2_id}).fetchone()
    if not user1 or not user2:
         raise HTTPException(status_code=404, detail="One or both users not found")

    result = db.execute(
        text("INSERT INTO matches (event_id, stage, match_date, match_time, user1_id, user2_id, venue, user1_screenshot_url, user1_tactics_url, user2_screenshot_url, user2_tactics_url) VALUES (:event_id, :stage, :match_date, :match_time, :user1_id, :user2_id, :venue, :user1_screenshot_url, :user1_tactics_url, :user2_screenshot_url, :user2_tactics_url) RETURNING id"),
        match.model_dump()
    )
    new_match_id = result.fetchone()[0]
    db.commit()

    created_match = db.execute(text("SELECT id, event_id, stage, match_date, match_time, user1_id, user2_id, venue, user1_screenshot_url, user1_tactics_url, user2_screenshot_url, user2_tactics_url FROM matches WHERE id = :id"), {"id": new_match_id}).fetchone()
    return created_match

# Get all matches (Organizer only - or public with event_id filter? Let's make it organizer only for now)
@app.get("/matches", response_model=list[MatchResponse])
def get_all_matches(current_user: dict = Depends(is_organizer), event_id: int | None = None, db: Session = Depends(get_db)):
    query = text("SELECT id, event_id, stage, match_date, match_time, user1_id, user2_id, venue, user1_screenshot_url, user1_tactics_url, user2_screenshot_url, user2_tactics_url FROM matches")
    params = {}
    where_clauses = []

    if event_id is not None:
        where_clauses.append("event_id = :event_id")
        params["event_id"] = event_id

    if where_clauses:
        query = text(f"{query} WHERE {' AND '.join(where_clauses)}")

    matches = db.execute(query, params).fetchall()
    return matches

# Get a specific match by ID (Organizer only)
@app.get("/matches/{match_id}", response_model=MatchResponse)
def get_match(match_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    match = db.execute(text("SELECT id, event_id, stage, match_date, match_time, user1_id, user2_id, venue, user1_screenshot_url, user1_tactics_url, user2_screenshot_url, user2_tactics_url FROM matches WHERE id = :id"), {"id": match_id}).fetchone()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match

# Update a match by ID (Organizer only)
@app.put("/matches/{match_id}", response_model=MatchResponse)
def update_match(match_id: int, match_update: MatchUpdate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if match exists
    existing_match = db.execute(text("SELECT id FROM matches WHERE id = :id"), {"id": match_id}).fetchone()
    if not existing_match:
        raise HTTPException(status_code=404, detail="Match not found")

    update_fields = match_update.model_dump(exclude_unset=True)
    if not update_fields:
        return existing_match # No fields to update

    # Construct update query dynamically
    set_clauses = [f"{key} = :{key}" for key in update_fields]
    query = text(f"UPDATE matches SET {', '.join(set_clauses)} WHERE id = :id")
    update_fields["id"] = match_id

    db.execute(query, update_fields)
    db.commit()

    # Fetch the updated match to return in the response
    updated_match = db.execute(text("SELECT id, event_id, stage, match_date, match_time, user1_id, user2_id, venue, user1_screenshot_url, user1_tactics_url, user2_screenshot_url, user2_tactics_url FROM matches WHERE id = :id"), {"id": match_id}).fetchone()
    return updated_match

# Delete a match by ID (Organizer only)
@app.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if match exists and get file URLs
    match = db.execute(text("SELECT user1_screenshot_url, user1_tactics_url, user2_screenshot_url, user2_tactics_url FROM matches WHERE id = :id"), {"id": match_id}).fetchone()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # List of file URLs associated with this match
    file_urls_to_delete = [
        match['user1_screenshot_url'],
        match['user1_tactics_url'],
        match['user2_screenshot_url'],
        match['user2_tactics_url'],
    ]

    # Delete associated files
    for file_url in file_urls_to_delete:
        if file_url:
            # Construct local file path from URL
            # Assuming URL is like /static/uploads/filename.ext and UPLOAD_DIRECTORY is ./uploads
            filename = os.path.basename(file_url)
            file_local_path = os.path.join(UPLOAD_DIRECTORY, filename)
            try:
                if os.path.exists(file_local_path):
                    os.remove(file_local_path)
                    print(f"Deleted file: {file_local_path}") # Optional: log deletion
                else:
                    print(f"File not found for deletion: {file_local_path}") # Optional: log file not found
            except OSError as e:
                print(f"Error deleting file {file_local_path}: {e}") # Optional: log error

    # Delete the match record from the database
    db.execute(text("DELETE FROM matches WHERE id = :id"), {"id": match_id})
    db.commit()

    return # No content to return for 204

# Create a new result (Organizer only)
@app.post("/results", response_model=ResultResponse, status_code=status.HTTP_201_CREATED)
def create_result(result: ResultCreate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if match exists and get event_id and participants
    match = db.execute(text("SELECT id, event_id, user1_id, user2_id FROM matches WHERE id = :match_id"), {"match_id": result.match_id}).fetchone()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Check if event is in league mode
    event = db.execute(text("SELECT mode FROM events WHERE id = :event_id"), {"event_id": match['event_id']}).fetchone()
    is_league_mode = event and event['mode'] == 'league'

    # Check if result already exists for this match
    existing_result = db.execute(text("SELECT id FROM results WHERE match_id = :match_id"), {"match_id": result.match_id}).fetchone()
    if existing_result:
        raise HTTPException(status_code=400, detail="Result already exists for this match")

    # Validate winner_user_id if provided
    if result.winner_user_id is not None and result.winner_user_id not in (match['user1_id'], match['user2_id']):
         raise HTTPException(status_code=400, detail="Winner user is not a participant in the match")

    # Insert new result
    result_dict = result.model_dump()
    result_dict["match_id"] = result.match_id # Ensure match_id is included

    query = text("INSERT INTO results (match_id, user1_score, user2_score, winner_user_id) VALUES (:match_id, :user1_score, :user2_score, :winner_user_id) RETURNING id")
    result_row = db.execute(query, result_dict)
    new_result_id = result_row.fetchone()[0]
    
    # Update league standings if in league mode
    if is_league_mode:
        user1_id = match['user1_id']
        user2_id = match['user2_id']
        event_id = match['event_id']
        user1_score = result.user1_score if result.user1_score is not None else 0
        user2_score = result.user2_score if result.user2_score is not None else 0

        # Determine points, wins, draws, losses
        user1_points = 0
        user2_points = 0
        user1_wins = 0
        user1_draws = 0
        user1_losses = 0
        user2_wins = 0
        user2_draws = 0
        user2_losses = 0

        if user1_score > user2_score:
            user1_points = 3
            user1_wins = 1
            user2_losses = 1
        elif user1_score < user2_score:
            user2_points = 3
            user2_wins = 1
            user1_losses = 1
        else:
            user1_points = 1
            user2_points = 1
            user1_draws = 1
            user2_draws = 1
        
        # Update user1's standings
        db.execute(text("""
            INSERT INTO league_standings (user_id, event_id, points, wins, draws, losses, goals_scored, goals_against, games_played)
            VALUES (:user_id, :event_id, :points, :wins, :draws, :losses, :goals_scored, :goals_against, :games_played)
            ON CONFLICT(user_id, event_id) DO UPDATE SET
                points = league_standings.points + :points,
                wins = league_standings.wins + :wins,
                draws = league_standings.draws + :draws,
                losses = league_standings.losses + :losses,
                goals_scored = league_standings.goals_scored + :goals_scored,
                goals_against = league_standings.goals_against + :goals_against,
                games_played = league_standings.games_played + 1
        """),
        {
            "user_id": user1_id,
            "event_id": event_id,
            "points": user1_points,
            "wins": user1_wins,
            "draws": user1_draws,
            "losses": user1_losses,
            "goals_scored": user1_score,
            "goals_against": user2_score,
            "games_played": 1
        })

        # Update user2's standings
        db.execute(text("""
            INSERT INTO league_standings (user_id, event_id, points, wins, draws, losses, goals_scored, goals_against, games_played)
            VALUES (:user_id, :event_id, :points, :wins, :draws, :losses, :goals_scored, :goals_against, :games_played)
            ON CONFLICT(user_id, event_id) DO UPDATE SET
                points = league_standings.points + :points,
                wins = league_standings.wins + :wins,
                draws = league_standings.draws + :draws,
                losses = league_standings.losses + :losses,
                goals_scored = league_standings.goals_scored + :goals_scored,
                goals_against = league_standings.goals_against + :goals_against,
                games_played = league_standings.games_played + 1
        """),
        {
            "user_id": user2_id,
            "event_id": event_id,
            "points": user2_points,
            "wins": user2_wins,
            "draws": user2_draws,
            "losses": user2_losses,
            "goals_scored": user2_score,
            "goals_against": user1_score, # Note the swap for goals against
            "games_played": 1
        })

    db.commit()

    created_result = db.execute(text("SELECT id, match_id, user1_score, user2_score, winner_user_id FROM results WHERE id = :id"), {"id": new_result_id}).fetchone()
    return created_result

# Get all results (Organizer only - or public with filters? Let's make it organizer only for now)
@app.get("/results", response_model=list[ResultResponse])
def get_all_results(current_user: dict = Depends(is_organizer), match_id: int | None = None, event_id: int | None = None, db: Session = Depends(get_db)):
    query = text("SELECT r.id, r.match_id, r.user1_score, r.user2_score, r.winner_user_id FROM results r JOIN matches m ON r.match_id = m.id")
    params = {}
    where_clauses = []

    if match_id is not None:
        where_clauses.append("r.match_id = :match_id")
        params["match_id"] = match_id
    if event_id is not None:
        where_clauses.append("m.event_id = :event_id")
        params["event_id"] = event_id

    if where_clauses:
        query = text(f"{query} WHERE {' AND '.join(where_clauses)}")

    results = db.execute(query, params).fetchall()
    return results

# Get a specific result by ID (Organizer only)
@app.get("/results/{result_id}", response_model=ResultResponse)
def get_result(result_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id, match_id, user1_score, user2_score, winner_user_id FROM results WHERE id = :id"), {"id": result_id}).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result

# Update a result by ID (Organizer only)
@app.put("/results/{result_id}", response_model=ResultResponse)
def update_result(result_id: int, result_update: ResultUpdate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if result exists
    existing_result = db.execute(text("SELECT id, match_id FROM results WHERE id = :id"), {"id": result_id}).fetchone()
    if not existing_result:
        raise HTTPException(status_code=404, detail="Result not found")

    # Check if the updated winner_user_id is valid for the match
    if result_update.winner_user_id is not None:
        match = db.execute(text("SELECT user1_id, user2_id FROM matches WHERE id = :match_id"), {"match_id": existing_result['match_id']}).fetchone()
        if result_update.winner_user_id not in (match['user1_id'], match['user2_id']):
            raise HTTPException(status_code=400, detail="Winner user is not a participant in the match")

    update_fields = result_update.model_dump(exclude_unset=True)
    if not update_fields:
        return existing_result # No fields to update

    # Construct update query dynamically
    set_clauses = [f"{key} = :{key}" for key in update_fields]
    query = text(f"UPDATE results SET {', '.join(set_clauses)} WHERE id = :id")
    update_fields["id"] = result_id

    db.execute(query, update_fields)
    db.commit()

    # Fetch the updated result to return in the response
    updated_result = db.execute(text("SELECT id, match_id, user1_score, user2_score, winner_user_id FROM results WHERE id = :id"), {"id": result_id}).fetchone()
    return updated_result

# Delete a result by ID (Organizer only)
@app.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_result(result_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if result exists
    existing_result = db.execute(text("SELECT id FROM results WHERE id = :id"), {"id": result_id}).fetchone()
    if not existing_result:
        raise HTTPException(status_code=404, detail="Result not found")

    db.execute(text("DELETE FROM results WHERE id = :id"), {"id": result_id})
    db.commit()
    return # No content to return for 204 

# Pydantic model for organizer to create event registration
class OrganizerEventRegistrationCreate(BaseModel):
    user_id: int
    event_id: int

# Pydantic model for event registration response
class EventRegistrationResponse(BaseModel):
    user_id: int
    event_id: int
    registration_date: datetime

    class Config:
        orm_mode = True

# Create a new event registration (Organizer only)
@app.post("/event-registrations", response_model=EventRegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_event_registration(reg: OrganizerEventRegistrationCreate, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if user exists
    user = db.execute(text("SELECT id FROM users WHERE id = :user_id"), {"user_id": reg.user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if event exists
    event = db.execute(text("SELECT id FROM events WHERE id = :event_id"), {"event_id": reg.event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if registration already exists
    existing_registration = db.execute(
        text("SELECT user_id FROM event_registrations WHERE user_id = :user_id AND event_id = :event_id"),
        {"user_id": reg.user_id, "event_id": reg.event_id}
    ).fetchone()
    if existing_registration:
        raise HTTPException(status_code=400, detail="User already registered for this event")

    # Insert new registration
    db.execute(
        text("INSERT INTO event_registrations (user_id, event_id) VALUES (:user_id, :event_id)"),
        {"user_id": reg.user_id, "event_id": reg.event_id}
    )
    db.commit()

    # Fetch and return the created registration
    created_reg = db.execute(
        text("SELECT user_id, event_id, registration_date FROM event_registrations WHERE user_id = :user_id AND event_id = :event_id"),
        {"user_id": reg.user_id, "event_id": reg.event_id}
    ).fetchone()
    return created_reg

# Get all event registrations (Organizer only - with optional filters)
@app.get("/event-registrations", response_model=list[EventRegistrationResponse])
def get_all_event_registrations(current_user: dict = Depends(is_organizer), user_id: int | None = None, event_id: int | None = None, db: Session = Depends(get_db)):
    query = text("SELECT user_id, event_id, registration_date FROM event_registrations")
    params = {}
    where_clauses = []

    if user_id is not None:
        where_clauses.append("user_id = :user_id")
        params["user_id"] = user_id
    if event_id is not None:
        where_clauses.append("event_id = :event_id")
        params["event_id"] = event_id

    if where_clauses:
        query = text(f"{query} WHERE {' AND '.join(where_clauses)}")

    registrations = db.execute(query, params).fetchall()
    return registrations

# Get registrations for a specific user (Organizer only)
@app.get("/users/{user_id}/registrations", response_model=list[EventRegistrationResponse])
def get_user_registrations(user_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if user exists
    user = db.execute(text("SELECT id FROM users WHERE id = :user_id"), {"user_id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    registrations = db.execute(text("SELECT user_id, event_id, registration_date FROM event_registrations WHERE user_id = :user_id"), {"user_id": user_id}).fetchall()
    return registrations

# Get registrations for a specific event (Organizer only)
@app.get("/events/{event_id}/registrations", response_model=list[EventRegistrationResponse])
def get_event_registrations(event_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if event exists
    event = db.execute(text("SELECT id FROM events WHERE id = :event_id"), {"event_id": event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    registrations = db.execute(text("SELECT user_id, event_id, registration_date FROM event_registrations WHERE event_id = :event_id"), {"event_id": event_id}).fetchall()
    return registrations

# Delete an event registration (Organizer only) - requires both user_id and event_id
@app.delete("/event-registrations/{user_id}/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_registration(user_id: int, event_id: int, current_user: dict = Depends(is_organizer), db: Session = Depends(get_db)):
    # Check if registration exists
    existing_registration = db.execute(
        text("SELECT user_id FROM event_registrations WHERE user_id = :user_id AND event_id = :event_id"),
        {"user_id": user_id, "event_id": event_id}
    ).fetchone()
    if not existing_registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    db.execute(
        text("DELETE FROM event_registrations WHERE user_id = :user_id AND event_id = :event_id"),
        {"user_id": user_id, "event_id": event_id}
    )
    db.commit()
    return # No content to return for 204 

# Get league standings for a specific event (Can be public)
@app.get("/events/{event_id}/standings", response_model=list[dict]) # Using dict for simplicity, can create a Pydantic model
def get_league_standings(event_id: int, db: Session = Depends(get_db)):
    # Check if event exists and is in league mode
    event = db.execute(text("SELECT id, mode FROM events WHERE id = :event_id"), {"event_id": event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event['mode'] != 'league':
        raise HTTPException(status_code=400, detail="Event is not in league mode")

    # Get standings, ordered by points, then goal difference (goals_scored - goals_against), then goals_scored
    standings = db.execute(text("""
        SELECT
            ls.user_id,
            u.username,
            ls.points,
            ls.wins,
            ls.draws,
            ls.losses,
            ls.goals_scored,
            ls.goals_against,
            ls.games_played,
            (ls.goals_scored - ls.goals_against) AS goal_difference
        FROM league_standings ls
        JOIN users u ON ls.user_id = u.id
        WHERE ls.event_id = :event_id
        ORDER BY ls.points DESC, goal_difference DESC, ls.goals_scored DESC
    """), {"event_id": event_id}).fetchall()

    # Add position to the results
    ranked_standings = []
    for i, row in enumerate(standings):
        standing_dict = dict(row)
        standing_dict['position'] = i + 1
        ranked_standings.append(standing_dict)

    return ranked_standings

# Get user's knockout progress for a specific event (Can be public)
@app.get("/events/{event_id}/users/{user_id}/knockout-progress", response_model=list[dict])
def get_user_knockout_progress(event_id: int, user_id: int, db: Session = Depends(get_db)):
    # Check if event exists and is in knockout mode
    event = db.execute(text("SELECT id, mode FROM events WHERE id = :event_id"), {"event_id": event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event['mode'] != 'knockout':
        raise HTTPException(status_code=400, detail="Event is not in knockout mode")

    # Check if user exists and is registered for the event
    user = db.execute(text("SELECT id FROM users WHERE id = :user_id"), {"user_id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    registration = db.execute(text("SELECT user_id FROM event_registrations WHERE user_id = :user_id AND event_id = :event_id"), {"user_id": user_id, "event_id": event_id}).fetchone()
    if not registration:
         raise HTTPException(status_code=400, detail="User is not registered for this event")

    # Get all matches for this event involving the user, with results
    matches_with_results = db.execute(text("""
        SELECT
            m.id AS match_id,
            m.stage,
            m.match_date,
            m.match_time,
            m.user1_id,
            u1.username AS user1_username,
            m.user2_id,
            u2.username AS user2_username,
            m.venue,
            r.user1_score,
            r.user2_score,
            r.winner_user_id
        FROM matches m
        JOIN users u1 ON m.user1_id = u1.id
        JOIN users u2 ON m.user2_id = u2.id
        LEFT JOIN results r ON m.id = r.match_id
        WHERE m.event_id = :event_id AND (m.user1_id = :user_id OR m.user2_id = :user_id)
        ORDER BY m.match_date, m.match_time
    """), {"event_id": event_id, "user_id": user_id}).fetchall()

    # Process matches to determine progress (basic)
    progress = []
    for match in matches_with_results:
        match_dict = dict(match)
        is_winner = match['winner_user_id'] == user_id if match['winner_user_id'] is not None else None
        match_dict['user_is_winner'] = is_winner
        progress.append(match_dict)

    return progress

# Get current user's match history
@app.get("/users/me/matches", response_model=list[UserMatchHistory])
def get_my_match_history(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user['id']

    # Get all matches involving the current user, with event name, other user's username, and results
    matches_history = db.execute(text("""
        SELECT
            m.id AS match_id,
            m.event_id,
            e.name AS event_name,
            m.stage,
            m.match_date,
            m.match_time,
            m.user1_id,
            u1.username AS user1_username,
            m.user2_id,
            u2.username AS user2_username,
            m.venue,
            r.user1_score,
            r.user2_score,
            r.winner_user_id
        FROM matches m
        JOIN events e ON m.event_id = e.id
        JOIN users u1 ON m.user1_id = u1.id
        JOIN users u2 ON m.user2_id = u2.id
        LEFT JOIN results r ON m.id = r.match_id
        WHERE m.user1_id = :user_id OR m.user2_id = :user_id
        ORDER BY m.match_date DESC, m.match_time DESC
    """), {"user_id": user_id}).fetchall()

    return matches_history 

# Upload endpoint for screenshot or tactics image
@app.post("/matches/{match_id}/upload/{user_id}")
async def upload_match_image(match_id: int, user_id: int, file: UploadFile = File(...), file_type: str = "screenshot", current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Validate file_type
    if file_type not in ["screenshot", "tactics"]:
        raise HTTPException(status_code=400, detail="Invalid file_type. Must be 'screenshot' or 'tactics'")

    # Validate file type based on extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Only {', '.join(ALLOWED_FILE_TYPES)} are allowed.")

    # Validate file size
    # Read the file content to check size and then save
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File size exceeds the maximum limit of {MAX_FILE_SIZE // 1024 // 1024}MB")

    # Reset file pointer to the beginning after reading for size check
    await file.seek(0)

    # Check if match exists and involves the user
    match = db.execute(text("SELECT id, user1_id, user2_id FROM matches WHERE id = :match_id AND (user1_id = :user_id OR user2_id = :user_id)"), {"match_id": match_id, "user_id": user_id}).fetchone()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found or user not a participant in this match")

    # Check if the uploading user is the participant user_id
    if current_user['id'] != user_id:
         raise HTTPException(status_code=403, detail="You can only upload files for yourself in this match")

    # Generate a unique filename
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_local_path = os.path.join(UPLOAD_DIRECTORY, unique_filename) # Local path
    file_url = f"{STATIC_URL_PATH}/{unique_filename}" # Public URL

    # Save the file asynchronously
    try:
        async with aiofiles.open(file_local_path, 'wb') as out_file:
            # Use the content already read for size check
            await out_file.write(content)
        # await file.seek(0) # No longer needed after writing content
        # async with aiofiles.open(file_local_path, 'wb') as out_file:
        #     while content := await file.read(1024):
        #         await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

    # Determine which column to update
    column_to_update = None
    if user_id == match['user1_id']:
        if file_type == "screenshot":
            column_to_update = "user1_screenshot_url"
        elif file_type == "tactics":
            column_to_update = "user1_tactics_url"
    elif user_id == match['user2_id']:
        if file_type == "screenshot":
            column_to_update = "user2_screenshot_url"
        elif file_type == "tactics":
            column_to_update = "user2_tactics_url"

    if column_to_update:
        # Update the database with the file URL
        db.execute(
            text(f"UPDATE matches SET {column_to_update} = :file_url WHERE id = :match_id"),
            {"file_url": file_url, "match_id": match_id}
        )
        db.commit()
    else:
         # This case should ideally not be reached if logic is correct
         raise HTTPException(status_code=500, detail="Internal server error: Could not determine column to update")

    return {"filename": unique_filename, "file_url": file_url} 

# Get participants for a specific event (Public)
@app.get("/events/{event_id}/participants", response_model=list[ParticipantResponse])
def get_event_participants(event_id: int, db: Session = Depends(get_db)):
    # Check if event exists
    event = db.execute(text("SELECT id FROM events WHERE id = :event_id"), {"event_id": event_id}).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get participants by joining event_registrations and users table
    participants = db.execute(text("""
        SELECT u.id, u.username
        FROM users u
        JOIN event_registrations er ON u.id = er.user_id
        WHERE er.event_id = :event_id
    """), {"event_id": event_id}).fetchall()

    return participants 