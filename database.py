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

    try:
        with open(SCHEMA_PATH, "r") as schema_file:
            connection.executescript(schema_file.read())

        connection.commit()

    finally:
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
            architecture_overview,
            architecture_components,
            architecture_flow,
            technologies,
            must_have_ids,
            must_have,
            nice_have_ids,
            nice_to_have,
            constraints,
            risks
        ):
    connection = get_connection()

    try:
        connection.execute("BEGIN")

        # 1. Update single-value design fields
        cursor = connection.execute(
            """
            UPDATE projects
            SET problem = ?,
                architecture = ?,
                architecture_flow = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                problem,
                architecture_overview,
                architecture_flow,
                project_id
            )
        )

        if cursor.rowcount != 1:
            raise ValueError("Project not found")

        # 2. Remove previous repeatable design entries
        for table in (
            "requirements",
            "constraints",
            "risks",
            "architecture_components",
        ):
            connection.execute(
                f"DELETE FROM {table} WHERE project_id = ?",
                (project_id,)
            )

        # 3. Save requirements
        for item_type, items in (
            ("must_have", must_have),
            ("nice_to_have", nice_to_have)
        ):
            for position, text in enumerate(items):
                text = text.strip()

                if text:
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
                            text,
                            item_type,
                            position
                        )
                    )

        # 4. Save constraints
        for position, text in enumerate(constraints):
            text = text.strip()

            if text:
                connection.execute(
                    """
                    INSERT INTO constraints (
                        project_id,
                        text,
                        position
                    )
                    VALUES (?, ?, ?)
                    """,
                    (project_id, text, position)
                )

        # 5. Save architecture components
        connection.execute(
            """
            DELETE FROM architecture_components
            WHERE project_id = ?
            """,
            (project_id,)
        )

        for position, text in enumerate(architecture_components):
            text = text.strip()

            if text:
                connection.execute(
                    """
                    INSERT INTO architecture_components (
                        project_id,
                        text,
                        position
                    )
                    VALUES (?, ?, ?)
                    """,
                    (project_id, text, position)
                )

        
        # 6. Save technology decisions

        # Remove previously saved technologies for this project
        connection.execute(
            """
            DELETE FROM architecture_technology
            WHERE project_id = ?
            """,
            (project_id,)
        )

        # Insert the current technology decisions
        for position, technology in enumerate(technologies):

            connection.execute(
                """
                INSERT INTO architecture_technology (
                    project_id,
                    name,
                    reason,
                    alternative,
                    tradeoff,
                    position
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    technology["name"],
                    technology["reason"],
                    technology["alternative"],
                    technology["tradeoff"],
                    position
                )
            )

        # 7. Save risks
        for position, text in enumerate(risks):
            text = text.strip()

            if text:
                connection.execute(
                    """
                    INSERT INTO risks (
                        project_id,
                        text,
                        position
                    )
                    VALUES (?, ?, ?)
                    """,
                    (project_id, text, position)
                )

        # 8. Commit all changes
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
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
    
    components = connection.execute(
            """
            SELECT id, text, position
            FROM architecture_components
            WHERE project_id = ?
            ORDER BY position ASC
            """,
            (project_id,)
        ).fetchall()

    
    connection.close()

    return {
        "must_have": must_have,
        "nice_to_have": nice_to_have,
        "constraints": constraints,
        "components": components,
        "risks": risks
    }
def get_technologies(project_id):
    conn = get_connection()

    try:
        technologies = conn.execute(
            """
            SELECT *
            FROM architecture_technology
            WHERE project_id = ?
            ORDER BY position ASC
            """,
            (project_id,)
        ).fetchall()

        return technologies

    finally:
        conn.close()


def update_requirement_completion(
    project_id,
    requirement_id,
    completed
):
    connection = get_connection()

    try:
        with connection:
            cursor = connection.execute(
                """
                UPDATE requirements
                SET completed = ?
                WHERE id = ?
                  AND project_id = ?
                """,
                (
                    int(completed),
                    requirement_id,
                    project_id
                )
            )

            return cursor.rowcount == 1

    finally:
        connection.close()


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


    

