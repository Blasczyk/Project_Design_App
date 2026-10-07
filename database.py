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