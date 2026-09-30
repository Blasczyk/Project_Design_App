import sqlite3

DATABASE = "instance/project_design.db"

def get_connection():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            what TEXT,
            why TEXT,
            success TEXT,
            status TEXT NOT NULL DEFAULT 'Not Started',
            current_stage TEXT NOT NULL DEFAULT 'Overview',
            progress INTEGER NOT NULL DEFAULT 0,
            next_action TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS project_design (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL UNIQUE,
            problem TEXT,
            architecture TEXT,

            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS design_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            text TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            position INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE CASCADE
        )
    """)

    connection.commit()
    connection.close()

def create_project(title, what, why, success):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO projects (
        title,
        what,
        why,
        success
        )
        VALUES(?, ?, ?, ?)
        """,
        (title, what, why, success)
    )

    connection.commit()
    project_id = cursor.lastrowid

    connection.close()

    return project_id

def get_project(project_id):
    connection = get_connection()

    project = connection.execute(
        """
        SELECT *
        FROM projects
        WHERE id = ?
        """,
        (project_id,)
    ).fetchone()
    connection.close()
    return project


def get_all_projects():

    connection = get_connection()

    projects = connection.execute(
        """
        SELECT *
        FROM projects
        ORDER BY  updated_at DESC
        """
    ).fetchall()

    connection.close()
    return projects



def design_project(
    project_id,
    problem,
    architecture,
    must_have,
    nice_to_have,
    constraints,
    risks
):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO project_design (
            project_id,
            problem,
            architecture
        )
        VALUES (?, ?, ?)
        """,
        (
            project_id,
            problem,
            architecture
        )
    )

    for position, item in enumerate(must_have):
        connection.execute(
            """
            INSERT INTO design_items (
                project_id,
                item_type,
                text,
                position
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                project_id,
                "must_have",
                item,
                position
            )
        )

        for position, item in enumerate(nice_to_have):
            connection.execute(
                """
                INSERT INTO design_items (
                    project_id,
                    item_type,
                    text,
                    position
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    project_id,
                    "nice_to_have",
                    item,
                    position
                )
            )

        for position, item in enumerate(constraints):
            connection.execute(
                """
                INSERT INTO design_items (
                    project_id,
                    item_type,
                    text,
                    position
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    project_id,
                    "constraint",
                    item,
                    position
                )
            )
    connection.commit()
    connection.close()