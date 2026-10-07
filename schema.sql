CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    what TEXT,
    why TEXT,
    success TEXT,


    status TEXT NOT NULL DEFAULT 'Not Started',
    current_stage TEXT NOT NULL DEFAULT 'Overview',
    problem TEXT,
    architecture TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    type TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);