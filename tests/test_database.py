
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for this test
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create a database path inside the temporary directory
        self.test_db_path = (
            Path(self.temp_dir.name) / "test_project_design.db"
        )

        # Redirect database.py to the temporary database
        self.database_patch = patch.object(
            database,
            "DATABASE",
            str(self.test_db_path)
        )
        self.database_patch.start()

        # Initialize the test database using the real schema
        database.init_db()

    def tearDown(self):
        # Restore the original DATABASE variable
        self.database_patch.stop()

        # Delete the temporary database and directory
        self.temp_dir.cleanup()

    
    def create_test_project(self, title="Test Project"):
        connection = database.get_connection()

        try:
            cursor = connection.execute(
                "INSERT INTO projects (title) VALUES (?)",
                (title,)
            )
            connection.commit()
            return cursor.lastrowid

        finally:
            connection.close()

    def save_test_design(
        self,
        project_id,
        must_have=None,
        must_have_ids=None,
        nice_to_have=None,
        nice_have_ids=None
    ):
        database.design_project(
            project_id=project_id,
            problem="Automated test problem",
            architecture_overview="Automated test architecture",
            architecture_components=["Test component"],
            architecture_flow="Input to output",
            technologies=[],
            must_have_ids=must_have_ids or [],
            must_have=must_have or [],
            nice_have_ids=nice_have_ids or [],
            nice_to_have=nice_to_have or [],
            constraints=[],
            risks=[]
        )


    def get_project_requirements(self, project_id):
        connection = database.get_connection()

        try:
            rows = connection.execute(
                """
                SELECT id, text, type, completed, position
                FROM requirements
                WHERE project_id = ?
                ORDER BY id
                """,
                (project_id,)
            ).fetchall()

            return [tuple(row) for row in rows]

        finally:
            connection.close()


    def test_database_connection(self):
        connection = database.get_connection()

        try:
            result = connection.execute(
                "PRAGMA foreign_keys"
            ).fetchone()

            self.assertEqual(result[0], 1)

        finally:
            connection.close()

    def test_schema_created(self):
        connection = database.get_connection()

        try:
            tables = {
                row["name"]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }

            expected_tables = {
                "projects",
                "requirements",
                "constraints",
                "risks",
                "architecture_components",
                "architecture_technology",
                "architecture_diagrams"
            }

            self.assertTrue(
                expected_tables.issubset(tables),
                f"Missing tables: {expected_tables - tables}"
            )

        finally:
            connection.close()


    def test_requirement_completion(self):
        connection = database.get_connection()

        try:
            # Create a test project
            cursor = connection.execute(
                """
                INSERT INTO projects (title)
                VALUES (?)
                """,
                ("Automated Test Project",)
            )
            project_id = cursor.lastrowid

            # Create an incomplete requirement
            cursor = connection.execute(
                """
                INSERT INTO requirements (
                    project_id, text, type, completed, position
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    "Test requirement",
                    "must_have",
                    0,
                    0
                )
            )
            requirement_id = cursor.lastrowid
            connection.commit()

        finally:
            connection.close()

        # Mark requirement as completed
        database.update_requirement_completion(
            project_id,
            requirement_id,
            True
        )

        connection = database.get_connection()

        try:
            requirement = connection.execute(
                """
                SELECT completed
                FROM requirements
                WHERE id = ? AND project_id = ?
                """,
                (requirement_id, project_id)
            ).fetchone()

            self.assertEqual(requirement["completed"], 1)

        finally:
            connection.close()

        # Mark requirement as incomplete
        database.update_requirement_completion(
            project_id,
            requirement_id,
            False
        )

        connection = database.get_connection()

        try:
            requirement = connection.execute(
                """
                SELECT completed
                FROM requirements
                WHERE id = ? AND project_id = ?
                """,
                (requirement_id, project_id)
            ).fetchone()

            self.assertEqual(requirement["completed"], 0)

        finally:
            connection.close()
    
    def test_requirement_id_preserved_on_edit(self):
        project_id = self.create_test_project()

        # Create requirement
        self.save_test_design(
            project_id,
            must_have=["Original requirement"],
            must_have_ids=[""]
        )

        connection = database.get_connection()

        try:
            original = connection.execute(
                """
                SELECT id
                FROM requirements
                WHERE project_id = ?
                """,
                (project_id,)
            ).fetchone()

            requirement_id = original["id"]

        finally:
            connection.close()

        # Mark requirement complete
        database.update_requirement_completion(
            project_id,
            requirement_id,
            True
        )

        # Edit existing requirement
        self.save_test_design(
            project_id,
            must_have=["Updated requirement"],
            must_have_ids=[str(requirement_id)]
        )

        # Verify ID and completion preserved
        connection = database.get_connection()

        try:
            updated = connection.execute(
                """
                SELECT id, text, completed
                FROM requirements
                WHERE project_id = ?
                """,
                (project_id,)
            ).fetchone()

            self.assertEqual(updated["id"], requirement_id)
            self.assertEqual(
                updated["text"],
                "Updated requirement"
            )
            self.assertEqual(updated["completed"], 1)

        finally:
            connection.close()



    def test_duplicate_requirement_id_rejected(self):
        project_id = self.create_test_project()

        self.save_test_design(
            project_id,
            must_have=["Original requirement"],
            must_have_ids=[""]
        )

        before = self.get_project_requirements(project_id)
        requirement_id = before[0][0]

        with self.assertRaises(ValueError):
            self.save_test_design(
                project_id,
                must_have=["Changed first", "Changed second"],
                must_have_ids=[
                    str(requirement_id),
                    str(requirement_id)
                ]
            )

        after = self.get_project_requirements(project_id)
        self.assertEqual(before, after)

    def test_invalid_requirement_id_rejected(self):
        project_id = self.create_test_project()

        self.save_test_design(
            project_id,
            must_have=["Original requirement"],
            must_have_ids=[""]
        )

        before = self.get_project_requirements(project_id)

        with self.assertRaises(ValueError):
            self.save_test_design(
                project_id,
                must_have=["Modified requirement"],
                must_have_ids=["invalid-id"]
            )

        after = self.get_project_requirements(project_id)
        self.assertEqual(before, after)

    def test_cross_project_requirement_id_rejected(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        self.save_test_design(
            project_a,
            must_have=["Project A requirement"],
            must_have_ids=[""]
        )

        self.save_test_design(
            project_b,
            must_have=["Project B requirement"],
            must_have_ids=[""]
        )

        before_a = self.get_project_requirements(project_a)
        before_b = self.get_project_requirements(project_b)

        foreign_requirement_id = before_b[0][0]

        with self.assertRaises(ValueError):
            self.save_test_design(
                project_a,
                must_have=["Unauthorized modification"],
                must_have_ids=[str(foreign_requirement_id)]
            )

        after_a = self.get_project_requirements(project_a)
        after_b = self.get_project_requirements(project_b)

        self.assertEqual(before_a, after_a)
        self.assertEqual(before_b, after_b)


    def test_design_transaction_rollback(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        # Establish valid initial designs
        self.save_test_design(
            project_a,
            must_have=["Original A requirement"],
            must_have_ids=[""]
        )

        self.save_test_design(
            project_b,
            must_have=["Original B requirement"],
            must_have_ids=[""]
        )

        connection = database.get_connection()

        try:
            # Capture original project and component state
            original_project = connection.execute(
                """
                SELECT problem, architecture, architecture_flow
                FROM projects
                WHERE id = ?
                """,
                (project_a,)
            ).fetchone()

            original_project = tuple(original_project)

            original_components = [
                tuple(row)
                for row in connection.execute(
                    """
                    SELECT text, position
                    FROM architecture_components
                    WHERE project_id = ?
                    ORDER BY position
                    """,
                    (project_a,)
                ).fetchall()
            ]

            foreign_requirement = connection.execute(
                """
                SELECT id
                FROM requirements
                WHERE project_id = ?
                """,
                (project_b,)
            ).fetchone()

            foreign_requirement_id = foreign_requirement["id"]

        finally:
            connection.close()

        # Trigger failure after earlier SQL updates
        with self.assertRaises(ValueError):
            database.design_project(
                project_id=project_a,
                problem="This change must roll back",
                architecture_overview="Modified architecture",
                architecture_components=["Modified component"],
                architecture_flow="Modified data flow",
                technologies=[],
                must_have_ids=[str(foreign_requirement_id)],
                must_have=["Unauthorized requirement update"],
                nice_have_ids=[],
                nice_to_have=[],
                constraints=[],
                risks=[]
            )

        # Verify the transaction was rolled back
        connection = database.get_connection()

        try:
            current_project = connection.execute(
                """
                SELECT problem, architecture, architecture_flow
                FROM projects
                WHERE id = ?
                """,
                (project_a,)
            ).fetchone()

            current_components = [
                tuple(row)
                for row in connection.execute(
                    """
                    SELECT text, position
                    FROM architecture_components
                    WHERE project_id = ?
                    ORDER BY position
                    """,
                    (project_a,)
                ).fetchall()
            ]

            self.assertEqual(
                tuple(current_project),
                original_project
            )

            self.assertEqual(
                current_components,
                original_components
            )

        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
