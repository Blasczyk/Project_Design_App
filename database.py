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
    risks,
    connection=None
):
    validate_design(
        problem,
        architecture_overview,
        architecture_flow,
        must_have,
        nice_to_have,
        constraints,
        risks,
        architecture_components,
        technologies
    )
    owns_connection = connection is None

    if owns_connection:
        connection = get_connection()

    try:
        if owns_connection:
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
            "constraints",
            "risks",
            "architecture_components",
        ):
            connection.execute(
                f"DELETE FROM {table} WHERE project_id = ?",
                (project_id,)
            )

        
        # 3. Save requirements while preserving IDs and completion states

        submitted_ids = set()

        for item_type, ids, texts in (
            ("must_have", must_have_ids, must_have),
            ("nice_to_have", nice_have_ids, nice_to_have),
        ):
            if len(ids) != len(texts):
                raise ValueError("Requirement IDs and text fields do not match")
            # Validate existing requirement IDs
            for requirement_id in ids:
                requirement_id = requirement_id.strip()

                if requirement_id and not requirement_id.isdecimal():
                    raise ValueError("Invalid requirement ID")
                
            for position, (requirement_id, text) in enumerate(zip(ids, texts)):
                text = text.strip()
                requirement_id = requirement_id.strip()

                

                if not text:
                    continue

                if requirement_id:
                    requirement_id = int(requirement_id)

                    if requirement_id in submitted_ids:
                        raise ValueError("Duplicate requirement ID")
                    
                    # Existing requirement: update without resetting completed
                    cursor = connection.execute(
                        """
                        UPDATE requirements
                        SET text = ?,
                            type = ?,
                            position = ?
                        WHERE id = ? AND project_id = ?
                        """,
                        (
                            text,
                            item_type,
                            position,
                            requirement_id,
                            project_id
                        )
                    )

                    if cursor.rowcount != 1:
                        raise ValueError(
                            f"Requirement {requirement_id} not found"
                        )

                    submitted_ids.add(int(requirement_id))

                else:
                    # New requirement: insert with completed = 0
                    cursor = connection.execute(
                        """
                        INSERT INTO requirements (
                            project_id,
                            text,
                            type,
                            completed,
                            position
                        )
                        VALUES (?, ?, ?, 0, ?)
                        """,
                        (project_id, text, item_type, position)
                    )

                    submitted_ids.add(cursor.lastrowid)

        # Delete requirements removed from the form
        existing_rows = connection.execute(
            """
            SELECT id
            FROM requirements
            WHERE project_id = ?
            """,
            (project_id,)
        ).fetchall()

        for row in existing_rows:
            existing_id = row["id"]

            if existing_id not in submitted_ids:
                connection.execute(
                    """
                    DELETE FROM requirements
                    WHERE id = ? AND project_id = ?
                    """,
                    (existing_id, project_id)
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


            # 8. Commit only if this function owns the connection
        if owns_connection:
            connection.commit()

    except Exception:
        if owns_connection:
            connection.rollback()
        raise

    finally:
        if owns_connection:
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



def add_architecture_diagram(
    project_id,
    diagram_data,
    connection=None
):
    owns_connection = connection is None

    if owns_connection:
        connection = get_connection()

    try:
   
        cursor = connection.execute(
            """
            INSERT INTO architecture_diagrams (
                project_id,
                original_filename,
                stored_filename,
                file_path
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                project_id,
                diagram_data["original_filename"],
                diagram_data["stored_filename"],
                diagram_data["file_path"]
            )
        )

        if owns_connection:
            connection.commit()

        return cursor.lastrowid

    except Exception:
        if owns_connection:
            connection.rollback()
        raise

    finally:
        if owns_connection:
            connection.close()


def get_architecture_diagrams(project_id):
    connection = get_connection()

    try:
        diagrams = connection.execute(
            """
            SELECT *
            FROM architecture_diagrams
            WHERE project_id = ?
            ORDER BY uploaded_at DESC, id DESC
            """,
            (project_id,)
        ).fetchall()

        return diagrams

    finally:
        connection.close()


def delete_architecture_diagram(project_id, diagram_id):
    connection = get_connection()

    try:
        with connection:
            diagram = connection.execute(
                """
                SELECT *
                FROM architecture_diagrams
                WHERE id = ? AND project_id = ?
                """,
                (diagram_id, project_id)
            ).fetchone()

            if diagram is None:
                return None

            connection.execute(
                """
                DELETE FROM architecture_diagrams
                WHERE id = ? AND project_id = ?
                """,
                (diagram_id, project_id)
            )

            return dict(diagram)

    finally:
        connection.close()


def validate_design(
    problem,
    architecture_overview,
    architecture_flow,
    must_have,
    nice_to_have,
    constraints,
    risks,
    architecture_components,
    technologies
):
    # Single-value fields
    fields = {
        "Problem statement": (problem, 5000),
        "Architecture overview": (architecture_overview, 10000),
        "Architecture flow": (architecture_flow, 10000),
    }

    for name, (value, limit) in fields.items():
        if len(value or "") > limit:
            raise ValueError(
                f"{name} exceeds {limit} characters"
            )

    # Repeatable text fields
    collections = {
        "Requirement": (must_have + nice_to_have, 500),
        "Constraint": (constraints, 500),
        "Risk": (risks, 500),
        "Architecture component": (architecture_components, 500),
    }

    for name, (items, limit) in collections.items():
        for text in items:
            if len(text) > limit:
                raise ValueError(
                    f"{name} exceeds {limit} characters"
                )

    # Technology decisions
    technology_limits = {
        "name": 100,
        "reason": 2000,
        "alternative": 2000,
        "tradeoff": 2000,
    }

    for technology in technologies:
        for field, limit in technology_limits.items():
            if len(technology[field]) > limit:
                raise ValueError(
                    f"Technology {field} exceeds {limit} characters"
                )




def update_requirement_completion(project_id, requirement_id, completed):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE requirements
            SET completed = ?
            WHERE id = ? AND project_id = ?
            """,
            (int(completed), requirement_id, project_id)
        )

        if cursor.rowcount != 1:
            raise ValueError("Requirement not found")

        connection.commit()
        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()