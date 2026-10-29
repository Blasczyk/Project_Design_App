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
    architecture_flow TEXT,

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
CREATE TABLE IF NOT EXISTS architecture_technology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    reason TEXT,
    alternative TEXT,
    tradeoff TEXT,
    position INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS architecture_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS architecture_diagrams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project_id INTEGER NOT NULL,

    title TEXT NOT NULL
        CHECK (length(trim(title)) > 0),

    description TEXT NOT NULL DEFAULT '',

    status TEXT NOT NULL DEFAULT 'todo'
        CHECK (
            status IN (
                'todo',
                'in_progress',
                'blocked',
                'done'
            )
        ),

    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (
            priority IN (
                'low',
                'medium',
                'high'
            )
        ),

    stage TEXT NOT NULL DEFAULT 'Implementation',

    position INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id
ON tasks(project_id);

CREATE INDEX IF NOT EXISTS idx_tasks_project_status
ON tasks(project_id, status);
        