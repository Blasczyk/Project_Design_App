
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


    def test_create_task(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id=project_id,
            title="Implement authentication",
            description="Create login functionality",
            priority="high"
        )

        connection = database.get_connection()

        try:
            task = connection.execute(
                """
                SELECT *
                FROM tasks
                WHERE id = ? AND project_id = ?
                """,
                (task_id, project_id)
            ).fetchone()

            self.assertIsNotNone(task)

            self.assertEqual(
                task["title"],
                "Implement authentication"
            )

            self.assertEqual(
                task["description"],
                "Create login functionality"
            )

            self.assertEqual(task["status"], "todo")
            self.assertEqual(task["priority"], "high")
            self.assertEqual(task["stage"], "Implementation")

        finally:
            connection.close()



    def test_get_tasks(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        # Create two tasks for Project A
        task_1 = database.create_task(
            project_id=project_a,
            title="First task"
        )

        task_2 = database.create_task(
            project_id=project_a,
            title="Second task",
            priority="high"
        )

        # Create a task for Project B
        database.create_task(
            project_id=project_b,
            title="Other project task"
        )

        tasks = database.get_tasks(project_a)

        self.assertEqual(len(tasks), 2)

        self.assertEqual(
            [task["id"] for task in tasks],
            [task_1, task_2]
        )

        self.assertEqual(
            [task["title"] for task in tasks],
            ["First task", "Second task"]
        )

        self.assertEqual(tasks[1]["priority"], "high")

        # Verify that an unknown project has no tasks
        self.assertEqual(
            database.get_tasks(999999),
            []
        )


    def test_get_task(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        task_id = database.create_task(
            project_id=project_a,
            title="Implement task retrieval",
            description="Retrieve one task by ID",
            priority="high"
        )

        # Retrieve from the correct project
        task = database.get_task(project_a, task_id)

        self.assertIsNotNone(task)
        self.assertEqual(task["id"], task_id)
        self.assertEqual(task["project_id"], project_a)
        self.assertEqual(
            task["title"],
            "Implement task retrieval"
        )
        self.assertEqual(task["priority"], "high")

        # Task must not be accessible through another project
        self.assertIsNone(
            database.get_task(project_b, task_id)
        )

        # Nonexistent task
        self.assertIsNone(
            database.get_task(project_a, 999999)
        )


    def test_update_task(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id=project_id,
            title="Original task"
        )

        # Update task details and mark complete
        result = database.update_task(
            project_id=project_id,
            task_id=task_id,
            title="Updated task",
            description="Updated description",
            status="done",
            priority="high",
            stage="Testing"
        )

        self.assertTrue(result)

        task = database.get_task(project_id, task_id)

        self.assertEqual(task["title"], "Updated task")
        self.assertEqual(
            task["description"],
            "Updated description"
        )
        self.assertEqual(task["status"], "done")
        self.assertEqual(task["priority"], "high")
        self.assertEqual(task["stage"], "Testing")
        self.assertIsNotNone(task["completed_at"])

        original_completion = task["completed_at"]

        # Editing a completed task must preserve completion time
        database.update_task(
            project_id=project_id,
            task_id=task_id,
            title="Edited completed task",
            status="done",
            priority="high",
            stage="Testing"
        )

        task = database.get_task(project_id, task_id)

        self.assertEqual(
            task["completed_at"],
            original_completion
        )

        # Reopening the task clears completion time
        database.update_task(
            project_id=project_id,
            task_id=task_id,
            title="Reopened task",
            status="in_progress"
        )

        task = database.get_task(project_id, task_id)

        self.assertEqual(task["status"], "in_progress")
        self.assertIsNone(task["completed_at"])


    def test_delete_task(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        task_id = database.create_task(
            project_id=project_a,
            title="Task to delete"
        )

        # Verify task exists
        self.assertIsNotNone(
            database.get_task(project_a, task_id)
        )

        # Another project cannot delete this task
        with self.assertRaises(ValueError):
            database.delete_task(project_b, task_id)

        # Original task must still exist
        self.assertIsNotNone(
            database.get_task(project_a, task_id)
        )

        # Delete using the correct project
        result = database.delete_task(project_a, task_id)

        self.assertTrue(result)

        # Verify deletion
        self.assertIsNone(
            database.get_task(project_a, task_id)
        )

        # Repeated deletion must fail
        with self.assertRaises(ValueError):
            database.delete_task(project_a, task_id)


    def test_create_task_invalid_inputs(self):
        project_id = self.create_test_project()

        invalid_cases = [
            {"title": ""},
            {"title": "   "},
            {"title": "X" * 201},
            {"title": "Valid", "description": "X" * 5001},
            {"title": "Valid", "status": "invalid"},
            {"title": "Valid", "priority": "urgent"},
            {"title": "Valid", "stage": ""},
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    database.create_task(
                        project_id=project_id,
                        **case
                    )

        # No invalid tasks should have been inserted
        self.assertEqual(
            database.get_tasks(project_id),
            []
        )

        # Cannot create a task for a nonexistent project
        with self.assertRaises(ValueError):
            database.create_task(
                project_id=999999,
                title="Orphan task"
            )


    def test_update_task_invalid_inputs(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        task_id = database.create_task(
            project_id=project_a,
            title="Original task"
        )

        invalid_cases = [
            {"title": ""},
            {"title": "X" * 201},
            {"title": "Valid", "status": "invalid"},
            {"title": "Valid", "priority": "urgent"},
            {"title": "Valid", "stage": ""},
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    database.update_task(
                        project_id=project_a,
                        task_id=task_id,
                        **case
                    )

        # Another project cannot update this task
        with self.assertRaises(ValueError):
            database.update_task(
                project_id=project_b,
                task_id=task_id,
                title="Unauthorized change"
            )

        # Verify original data remains unchanged
        task = database.get_task(project_a, task_id)

        self.assertEqual(task["title"], "Original task")
        self.assertEqual(task["status"], "todo")
        self.assertEqual(task["priority"], "medium")
        self.assertIsNone(task["completed_at"])




if __name__ == "__main__":
    unittest.main()
