import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

DATABASE = "instance/project_design.db"

def get_connection():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():
    connection = get_connection()

    with open(SCHEMA_PATH, "r")as schema_file:
        connection.executescript(schema_file.read())

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

    # Update the project's single-value design fields
    connection.execute(
        """
        UPDATE projects
        SET problem = ?,
            architecture = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (problem, architecture, project_id)
    )

    # Remove the previous list-based design data
    connection.execute(
        "DELETE FROM requirements WHERE project_id = ?",
        (project_id,)
    )

    connection.execute(
        "DELETE FROM constraints WHERE project_id = ?",
        (project_id,)
    )

    connection.execute(
        "DELETE FROM risks WHERE project_id = ?",
        (project_id,)
    )

    # Insert must-have requirements
    for position, text in enumerate(must_have):
        if text.strip():
            connection.execute(
                """
                INSERT INTO requirements (
                    project_id,
                    text,
                    type,
                    position
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    project_id,
                    text.strip(),
                    "must_have",
                    position
                )
            )

    # Insert nice-to-have requirements
    for position, text in enumerate(nice_to_have):
        if text.strip():
            connection.execute(
                """
                INSERT INTO requirements (
                    project_id,
                    text,
                    type,
                    position
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    project_id,
                    text.strip(),
                    "nice_to_have",
                    position
                )
            )

    # Insert constraints
    for position, text in enumerate(constraints):
        if text.strip():
            connection.execute(
                """
                INSERT INTO constraints (
                    project_id,
                    text,
                    position
                )
                VALUES (?, ?, ?)
                """,
                (project_id, text.strip(), position)
            )

    # Insert risks
    for position, text in enumerate(risks):
        if text.strip():
            connection.execute(
                """
                INSERT INTO risks (
                    project_id,
                    text,
                    position
                )
                VALUES (?, ?, ?)
                """,
                (project_id, text.strip(), position)
            )

    connection.commit()
    connection.close()


def get_project_design(project_id):
    '''
    This retrieves all the desing info for a particular project
    Projects: Problem, architecture
    requirements: must-have, and nice-to-have
    constraints: constraints
    risks: risks
    '''

    connection = get_connection()

    must_have = connection.execute(
        """
        SELECT *
        FROM requirements
        WHERE project_id = ?
            AND type = ?
        ORDER BY position , id
        """,
        (project_id,"must_have" )
    ).fetchall()


    nice_to_have = connection.execute(
        """
        SELECT *
        FROM requirements
        WHERE project_id = ?
            AND type = ?
        ORDER BY position , id
        """,
        (project_id, "nice_to_have")
    ).fetchall()

    constraints = connection.execute(
            """
            SELECT *
            FROM constraints
            WHERE project_id = ?
            ORDER BY position , id
            """,
            (project_id, )
        ).fetchall()

    risks = connection.execute(
                """
                SELECT *
                FROM risks
                WHERE project_id = ?
                ORDER BY position , id
                """,
                (project_id, )
            ).fetchall()

    
    connection.close()

    return {
        "must_have": must_have,
        "nice_to_have": nice_to_have,
        "constraints": constraints,
        "risks": risks
    }

def update_project(project_id, title, what, why, success):
    connection = get_connection()
    connection.execute(
        """
        UPDATE projects
        SET title = ?,
            what = ?,
            why = ?,
            success =?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (title, what, why, success, project_id)
    )
    connection.commit()
    connection.close()

def delete_project(project_id):
    connection = get_connection()
    cursor = connection.execute(
        """
        DELETE FROM projects
        WHERE id = ?
        """,
        (project_id,)
    )
    connection.commit()
    deleted = cursor.rowcount
    connection.close()
    return deleted


    

