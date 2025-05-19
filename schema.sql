-- Create the users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    role TEXT DEFAULT 'player' -- 'player' or 'organizer'
);

-- Create the events table
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    mode TEXT DEFAULT 'knockout' -- 'knockout' or 'league'
);

-- Create the matches table
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    stage TEXT, -- e.g., 'group', 'quarter-final'
    match_date DATE,
    match_time TIME,
    user1_id INTEGER, -- Now references users(id)
    user2_id INTEGER, -- Now references users(id)
    venue TEXT,
    user1_screenshot_url TEXT, -- URL for user1's screenshot
    user1_tactics_url TEXT, -- URL for user1's tactics
    user2_screenshot_url TEXT, -- URL for user2's screenshot
    user2_tactics_url TEXT, -- URL for user2's tactics
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create the results table
CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL UNIQUE,
    user1_score INTEGER, -- Score for user1
    user2_score INTEGER, -- Score for user2
    winner_user_id INTEGER, -- Winner is a user (references users(id))
    FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
    FOREIGN KEY (winner_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create the event_registrations table (for individual user registration to events)
CREATE TABLE event_registrations (
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, event_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Create the league_standings table (for tracking league mode progress)
CREATE TABLE league_standings (
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    points INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    position INTEGER, -- Could be calculated dynamically or stored
    PRIMARY KEY (user_id, event_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
); 