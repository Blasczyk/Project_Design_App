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



def design_project(problem, must_have, nice_to_have, 
                   constraints, architecture, risks):
    connection = get_connection()

    connection.execute(
        """
         INSERT INTO projects (
                problem,
                must_have,
                nice_to_have, 
                constraints,
                architecture,
                risks
                )
                VALUES(?, ?, ?, ?, ?, ?)
        """,
        (problem, must_have, nice_to_have, 
                   constraints, architecture, risks)
    )
    connection.commit()
    connection.close()