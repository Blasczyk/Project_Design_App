
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app as app_module

from io import BytesIO
from PIL import Image
from werkzeug.datastructures import FileStorage

import sqlite3
import database
from app import app


class TestRoutes(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.test_db_path = (
            Path(self.temp_dir.name) / "test_routes.db"
        )

        self.database_patch = patch.object(
            database,
            "DATABASE",
            str(self.test_db_path)
        )
        self.database_patch.start()

        database.init_db()

        app.config.update(
            TESTING=True
        )

        self.client = app.test_client()

        # Create disposable test project and requirement
        connection = database.get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO projects (title)
                VALUES (?)
                """,
                ("Route Test Project",)
            )
            self.project_id = cursor.lastrowid

            cursor = connection.execute(
                """
                INSERT INTO requirements (
                    project_id, text, type, completed, position
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self.project_id,
                    "Test requirement",
                    "must_have",
                    0,
                    0
                )
            )
            self.requirement_id = cursor.lastrowid

            connection.commit()

        finally:
            connection.close()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def completion_url(self, project_id=None, requirement_id=None):
        if project_id is None:
            project_id = self.project_id

        if requirement_id is None:
            requirement_id = self.requirement_id

        return (
            f"/projects/{project_id}/requirements/"
            f"{requirement_id}/completion"
        )

    def get_completion_status(self):
        connection = database.get_connection()

        try:
            row = connection.execute(
                """
                SELECT completed
                FROM requirements
                WHERE id = ? AND project_id = ?
                """,
                (self.requirement_id, self.project_id)
            ).fetchone()

            return row["completed"]

        finally:
            connection.close()

    def test_dashboard_loads(self):
        response = self.client.get(
            f"/projects/{self.project_id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Route Test Project",
            response.data
        )

    def test_nonexistent_dashboard(self):
        response = self.client.get(
            "/projects/999999"
        )

        self.assertEqual(response.status_code, 404)

    def test_requirement_completion_route(self):
        response = self.client.post(
            self.completion_url(),
            json={"completed": True}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_completion_status(), 1)

        response = self.client.post(
            self.completion_url(),
            json={"completed": False}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_completion_status(), 0)

    def test_invalid_completion_payload(self):
        response = self.client.post(
            self.completion_url(),
            json={"completed": "yes"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_completion_status(), 0)

    def test_cross_project_completion_rejected(self):
        other_project_id = self.project_id + 1000

        response = self.client.post(
            self.completion_url(
                project_id=other_project_id
            ),
            json={"completed": True}
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_completion_status(), 0)


    def test_valid_design_submission(self):
        response = self.client.post(
            f"/projects/{self.project_id}/design",
            data={
                "problem": "Automated design test",
                "architecture_system_overview": "Test architecture",
                "data_flow": "Input to output",
                "must_have_id": [str(self.requirement_id)],
                "must_have": ["Updated test requirement"],
                "nice_have_id": [],
                "nice_have": [],
                "constraints": [],
                "component": ["Test component"],
                "risks": [],
                "technology_name": [],
                "technology_reason": [],
                "technology_alternative": [],
                "technology_tradeoff": []
            },
            follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)

        connection = database.get_connection()

        try:
            project = connection.execute(
                """
                SELECT problem, architecture, architecture_flow
                FROM projects
                WHERE id = ?
                """,
                (self.project_id,)
            ).fetchone()

            requirement = connection.execute(
                """
                SELECT id, text
                FROM requirements
                WHERE id = ? AND project_id = ?
                """,
                (self.requirement_id, self.project_id)
            ).fetchone()

            self.assertEqual(
                project["problem"],
                "Automated design test"
            )

            self.assertEqual(
                project["architecture"],
                "Test architecture"
            )

            self.assertEqual(
                project["architecture_flow"],
                "Input to output"
            )

            self.assertEqual(
                requirement["id"],
                self.requirement_id
            )

            self.assertEqual(
                requirement["text"],
                "Updated test requirement"
            )

        finally:
            connection.close()


    def test_invalid_design_submission(self):
        # Capture the existing project state
        connection = database.get_connection()

        try:
            original = connection.execute(
                """
                SELECT problem, architecture, architecture_flow
                FROM projects
                WHERE id = ?
                """,
                (self.project_id,)
            ).fetchone()

            original_state = tuple(original)

        finally:
            connection.close()

        # Submit an invalid design
        response = self.client.post(
            f"/projects/{self.project_id}/design",
            data={
                "problem": "X" * 5001,
                "architecture_system_overview": "Test architecture",
                "data_flow": "Input to output",
                "must_have_id": [str(self.requirement_id)],
                "must_have": ["Test requirement"],
                "nice_have_id": [],
                "nice_have": [],
                "constraints": [],
                "component": ["Test component"],
                "risks": [],
                "technology_name": [],
                "technology_reason": [],
                "technology_alternative": [],
                "technology_tradeoff": []
            },
            follow_redirects=False
        )

        # Invalid submissions must be rejected
        self.assertEqual(response.status_code, 400)

        # Verify no project changes persisted
        connection = database.get_connection()

        try:
            current = connection.execute(
                """
                SELECT problem, architecture, architecture_flow
                FROM projects
                WHERE id = ?
                """,
                (self.project_id,)
            ).fetchone()

            self.assertEqual(
                tuple(current),
                original_state
            )

        finally:
            connection.close()


    def test_diagram_deletion(self):
        # Use a disposable upload directory
        upload_folder = Path(self.temp_dir.name) / "uploads"
        project_folder = upload_folder / f"project_{self.project_id}"
        project_folder.mkdir(parents=True)

        stored_filename = "test_diagram.png"
        file_path = project_folder / stored_filename
        file_path.write_bytes(b"temporary test image")

        # Create the matching SQLite record
        connection = database.get_connection()

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
                    self.project_id,
                    "test_diagram.png",
                    stored_filename,
                    str(file_path)
                )
            )

            diagram_id = cursor.lastrowid
            connection.commit()

        finally:
            connection.close()

        # Patch the upload folder for this request
        with patch.object(
            app_module,
            "UPLOAD_FOLDER",
            upload_folder
        ):
            response = self.client.post(
                f"/projects/{self.project_id}/diagrams/"
                f"{diagram_id}/delete",
                follow_redirects=False
            )

        # Successful deletion redirects to Design
        self.assertEqual(response.status_code, 302)

        # Physical file should be removed
        self.assertFalse(file_path.exists())

        # SQLite record should also be removed
        connection = database.get_connection()

        try:
            diagram = connection.execute(
                """
                SELECT id
                FROM architecture_diagrams
                WHERE id = ? AND project_id = ?
                """,
                (diagram_id, self.project_id)
            ).fetchone()

            self.assertIsNone(diagram)

        finally:
            connection.close()


    def test_valid_diagram_file_save(self):
        # Create a temporary upload directory
        upload_folder = Path(self.temp_dir.name) / "uploads"

        # Generate a real PNG image in memory
        image_buffer = BytesIO()

        image = Image.new("RGB", (10, 10), "white")
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        uploaded_file = FileStorage(
            stream=image_buffer,
            filename="architecture.png",
            content_type="image/png"
        )

        # Redirect file storage to our temporary directory
        with patch.object(
            app_module,
            "UPLOAD_FOLDER",
            upload_folder
        ):
            result = app_module.save_architecture_diagram(
                uploaded_file,
                self.project_id
            )

        # Verify returned metadata
        self.assertIsNotNone(result)
        self.assertEqual(
            result["original_filename"],
            "architecture.png"
        )

        self.assertTrue(
            result["stored_filename"].endswith(".png")
        )

        # Verify the physical file exists
        saved_file = (
            upload_folder
            / f"project_{self.project_id}"
            / result["stored_filename"]
        )

        self.assertTrue(saved_file.is_file())

        # Verify the saved file is a valid PNG
        with Image.open(saved_file) as saved_image:
            self.assertEqual(saved_image.format, "PNG")
            self.assertEqual(saved_image.size, (10, 10))


    def test_invalid_diagram_file_rejected(self):
        upload_folder = Path(self.temp_dir.name) / "uploads"

        # PNG filename, but the contents are not an image
        uploaded_file = FileStorage(
            stream=BytesIO(b"This is not a real PNG image"),
            filename="invalid.png",
            content_type="image/png"
        )

        with patch.object(
            app_module,
            "UPLOAD_FOLDER",
            upload_folder
        ):
            with self.assertRaises(ValueError):
                app_module.save_architecture_diagram(
                    uploaded_file,
                    self.project_id
                )

        # No physical file should have been created
        project_folder = (
            upload_folder / f"project_{self.project_id}"
        )

        if project_folder.exists():
            self.assertEqual(
                list(project_folder.iterdir()),
                []
            )


    def test_diagram_upload_transaction(self):
        upload_folder = Path(self.temp_dir.name) / "uploads"

        # Generate a valid PNG in memory
        image_buffer = BytesIO()
        image = Image.new("RGB", (10, 10), "white")
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        # Submit through the actual Flask route
        with patch.object(
            app_module,
            "UPLOAD_FOLDER",
            upload_folder
        ):
            response = self.client.post(
                f"/projects/{self.project_id}/design",
                data={
                    "problem": "Diagram upload test",
                    "architecture_system_overview": "Test architecture",
                    "data_flow": "Input to output",
                    "must_have_id": [str(self.requirement_id)],
                    "must_have": ["Test requirement"],
                    "component": ["Test component"],
                    "architecture_diagram": (
                        image_buffer,
                        "architecture.png"
                    )
                },
                content_type="multipart/form-data",
                follow_redirects=False
            )

        self.assertEqual(response.status_code, 302)

        # Check the SQLite record
        connection = database.get_connection()

        try:
            diagrams = connection.execute(
                """
                SELECT original_filename,
                       stored_filename,
                       file_path
                FROM architecture_diagrams
                WHERE project_id = ?
                """,
                (self.project_id,)
            ).fetchall()

            self.assertEqual(len(diagrams), 1)

            diagram = diagrams[0]

            self.assertEqual(
                diagram["original_filename"],
                "architecture.png"
            )

            # Check the physical file
            saved_file = (
                upload_folder / diagram["file_path"]
            )

            self.assertTrue(saved_file.is_file())

            with Image.open(saved_file) as saved_image:
                self.assertEqual(saved_image.format, "PNG")

        finally:
            connection.close()

    
    def test_diagram_upload_rollback_cleanup(self):
        upload_folder = Path(self.temp_dir.name) / "uploads"

        # Generate valid PNG
        image_buffer = BytesIO()
        image = Image.new("RGB", (10, 10), "white")
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        # Capture the original project state
        connection = database.get_connection()

        try:
            original = connection.execute(
                """
                SELECT problem, architecture, architecture_flow
                FROM projects
                WHERE id = ?
                """,
                (self.project_id,)
            ).fetchone()

            original_state = tuple(original)

        finally:
            connection.close()

        # Force a database failure after file save
        with (
            patch.object(
                app_module,
                "UPLOAD_FOLDER",
                upload_folder
            ),
            patch.object(
                app_module,
                "add_architecture_diagram",
                side_effect=RuntimeError("Simulated database failure")
            )
        ):
            response = self.client.post(
                f"/projects/{self.project_id}/design",
                data={
                    "problem": "Should be rolled back",
                    "architecture_system_overview": "Changed architecture",
                    "data_flow": "Changed flow",
                    "must_have_id": [str(self.requirement_id)],
                    "must_have": ["Test requirement"],
                    "component": ["Changed component"],
                    "architecture_diagram": (
                        image_buffer,
                        "architecture.png"
                    )
                },
                content_type="multipart/form-data",
                follow_redirects=False
            )

        # Flask handles unexpected failure
        self.assertEqual(response.status_code, 500)

        # Verify project changes were rolled back
        connection = database.get_connection()

        try:
            current = connection.execute(
                """
                SELECT problem, architecture, architecture_flow
                FROM projects
                WHERE id = ?
                """,
                (self.project_id,)
            ).fetchone()

            self.assertEqual(
                tuple(current),
                original_state
            )

            diagram_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM architecture_diagrams
                WHERE project_id = ?
                """,
                (self.project_id,)
            ).fetchone()[0]

            self.assertEqual(diagram_count, 0)

        finally:
            connection.close()

        # Verify uploaded file was removed
        project_folder = (
            upload_folder / f"project_{self.project_id}"
        )

        if project_folder.exists():
            self.assertEqual(
                list(project_folder.iterdir()),
                []
            )


    def create_test_project(self, title="Test Project"):
        connection = database.get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO projects (title)
                VALUES (?)
                """,
                (title,)
            )

            connection.commit()
            return cursor.lastrowid

        finally:
            connection.close()


    def test_execution_page(self):
        project_id = self.create_test_project()

        # Create a task for the project
        database.create_task(
            project_id=project_id,
            title="Implement execution page",
            priority="high"
        )

        # Request the execution page
        response = self.client.get(
            f"/projects/{project_id}/execution"
        )

        self.assertEqual(response.status_code, 200)

        # Verify project and task information appears
        self.assertIn(
            b"Implement execution page",
            response.data
        )

        self.assertIn(
            b"high",
            response.data
        )

        # Verify nonexistent projects return 404
        response = self.client.get(
            "/projects/999999/execution"
        )

        self.assertEqual(response.status_code, 404)


    def test_create_task_route(self):
        project_id = self.create_test_project()

        response = self.client.post(
            f"/projects/{project_id}/tasks/new",
            data={
                "title": "Configure monitoring",
                "description": "Monitor system resources",
                "priority": "high",
                "stage": "Implementation"
            },
            follow_redirects=False
        )

        # Successful creation redirects to Execution
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"/projects/{project_id}/execution",
            response.headers["Location"]
        )

        # Verify actual database persistence
        tasks = database.get_tasks(project_id)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Configure monitoring")
        self.assertEqual(tasks[0]["description"], "Monitor system resources")
        self.assertEqual(tasks[0]["priority"], "high")
        self.assertEqual(tasks[0]["status"], "todo")
        self.assertEqual(tasks[0]["stage"], "Implementation")

    def test_create_task_route_invalid_input(self):
        project_id = self.create_test_project()

        response = self.client.post(
            f"/projects/{project_id}/tasks/new",
            data={
                "title": "",
                "priority": "high",
                "stage": "Implementation"
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(database.get_tasks(project_id), [])

    def test_create_task_route_missing_project(self):
        response = self.client.post(
            "/projects/999999/tasks/new",
            data={
                "title": "Orphan task",
                "priority": "medium",
                "stage": "Implementation"
            }
        )

        # Current route converts database ValueError to HTTP 400
        self.assertEqual(response.status_code, 404)


    
    def test_update_task_status_route(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id=project_id,
            title="Test status updates"
        )

        url = f"/projects/{project_id}/tasks/{task_id}/status"

        response = self.client.post(
            url,
            data={"status": "done"}
        )

        self.assertEqual(response.status_code, 302)

        task = database.get_task(project_id, task_id)
        self.assertEqual(task["status"], "done")
        self.assertIsNotNone(task["completed_at"])

        # Reopen completed task
        response = self.client.post(
            url,
            data={"status": "in_progress"}
        )

        self.assertEqual(response.status_code, 302)

        task = database.get_task(project_id, task_id)
        self.assertEqual(task["status"], "in_progress")
        self.assertIsNone(task["completed_at"])

    def test_update_task_status_invalid(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id=project_id,
            title="Protected task"
        )

        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}/status",
            data={"status": "invalid"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            database.get_task(project_id, task_id)["status"],
            "todo"
        )

    def test_update_task_status_wrong_project(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        task_id = database.create_task(
            project_id=project_a,
            title="Project A task"
        )

        response = self.client.post(
            f"/projects/{project_b}/tasks/{task_id}/status",
            data={"status": "done"}
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            database.get_task(project_a, task_id)["status"],
            "todo"
        )



    def test_edit_task_get(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id=project_id,
            title="Original task",
            description="Original description",
            priority="high",
            stage="Testing"
        )

        response = self.client.get(
            f"/projects/{project_id}/tasks/{task_id}/edit"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Original task", response.data)
        self.assertIn(b"Original description", response.data)
        self.assertIn(b"Testing", response.data)

    def test_edit_task_post(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id=project_id,
            title="Original task"
        )

        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}/edit",
            data={
                "title": "Updated task",
                "description": "Updated description",
                "priority": "high",
                "stage": "Documentation"
            }
        )

        self.assertEqual(response.status_code, 302)

        task = database.get_task(project_id, task_id)

        self.assertEqual(task["title"], "Updated task")
        self.assertEqual(
            task["description"],
            "Updated description"
        )
        self.assertEqual(task["priority"], "high")
        self.assertEqual(task["stage"], "Documentation")
        self.assertEqual(task["status"], "todo")

        # Editing must not create duplicate tasks.
        self.assertEqual(
            len(database.get_tasks(project_id)),
            1
        )

    
    def test_edit_completed_task_preserves_completion(self):
        # 1. Create a test project
        project_id = self.create_test_project()

        # 2. Create a task
        task_id = database.create_task(
            project_id=project_id,
            title="Completed task"
        )

        # 3. Mark the task as completed
        database.update_task(
            project_id=project_id,
            task_id=task_id,
            title="Completed task",
            description="",
            status="done",
            priority="medium",
            stage="Implementation"
        )

        # 4. Record original completion timestamp
        original = database.get_task(project_id, task_id)
        original_completed_at = original["completed_at"]

        self.assertEqual(original["status"], "done")
        self.assertIsNotNone(original_completed_at)

        # 5. Edit the completed task through Flask
        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}/edit",
            data={
                "title": "Edited completed task",
                "description": "Updated documentation",
                "priority": "low",
                "stage": "Documentation"
            }
        )

        self.assertEqual(response.status_code, 302)

        # 6. Verify changes and completion history
        updated = database.get_task(project_id, task_id)

        self.assertEqual(
            updated["title"],
            "Edited completed task"
        )
        self.assertEqual(updated["status"], "done")
        self.assertEqual(
            updated["completed_at"],
            original_completed_at
        )


    def test_edit_task_invalid_input(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id=project_id,
            title="Valid task"
        )

        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}/edit",
            data={
                "title": "",
                "description": "Invalid submission",
                "priority": "high",
                "stage": "Testing"
            }
        )

        self.assertEqual(response.status_code, 400)

        task = database.get_task(project_id, task_id)

        # Invalid updates must not modify stored data.
        self.assertEqual(task["title"], "Valid task")
        self.assertEqual(task["description"], "")

    def test_edit_task_wrong_project(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        task_id = database.create_task(
            project_id=project_a,
            title="Project A task"
        )

        url = f"/projects/{project_b}/tasks/{task_id}/edit"

        get_response = self.client.get(url)

        self.assertEqual(get_response.status_code, 404)

        post_response = self.client.post(
            url,
            data={
                "title": "Unauthorized edit",
                "description": "",
                "priority": "high",
                "stage": "Implementation"
            }
        )

        self.assertEqual(post_response.status_code, 404)

        task = database.get_task(project_a, task_id)

        self.assertEqual(task["title"], "Project A task")


    def test_create_completed_task_sets_timestamp(self):
        task_id = database.create_task(
            project_id=self.project_id,
            title="Already completed",
            status="done"
        )

        task = database.get_task(self.project_id, task_id)

        self.assertEqual(task["status"], "done")
        self.assertIsNotNone(task["completed_at"])


    def test_delete_task_route(self):
        project_id = self.create_test_project()
        task_id = database.create_task(
            project_id=project_id,
            title="Task to delete"
        )

        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}/delete"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(database.get_task(project_id, task_id))

    def test_delete_task_nonexistent(self):
        project_id = self.create_test_project()

        response = self.client.post(
            f"/projects/{project_id}/tasks/999999/delete"
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_task_wrong_project(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        task_id = database.create_task(
            project_id=project_a,
            title="Protected task"
        )

        response = self.client.post(
            f"/projects/{project_b}/tasks/{task_id}/delete"
        )

        self.assertEqual(response.status_code, 404)
        self.assertIsNotNone(database.get_task(project_a, task_id))

    def test_delete_task_get_rejected(self):
        project_id = self.create_test_project()
        task_id = database.create_task(
            project_id=project_id,
            title="Protected from GET"
        )

        response = self.client.get(
            f"/projects/{project_id}/tasks/{task_id}/delete"
        )

        self.assertEqual(response.status_code, 405)
        self.assertIsNotNone(database.get_task(project_id, task_id))



    def test_link_task_requirement_route(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id,
            "Implement authentication"
        )

        connection = database.get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, completed, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    "Secure authentication",
                    "must_have",
                    0,
                    0
                )
            )
            requirement_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}/requirements",
            data={"requirement_id": str(requirement_id)}
        )

        self.assertEqual(response.status_code, 302)

        requirements = database.get_task_requirements(
            project_id,
            task_id
        )

        self.assertEqual(len(requirements), 1)
        self.assertEqual(
            requirements[0]["id"],
            requirement_id
        )



    def test_link_task_requirement_invalid_id(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id,
            "Test task"
        )

        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}/requirements",
            data={"requirement_id": "invalid"}
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            database.get_task_requirements(project_id, task_id),
            []
        )


    def test_link_task_requirement_duplicate_route(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id,
            "Test task"
        )

        connection = database.get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, completed, position)
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

        url = (
            f"/projects/{project_id}/tasks/"
            f"{task_id}/requirements"
        )

        first_response = self.client.post(
            url,
            data={"requirement_id": str(requirement_id)}
        )

        second_response = self.client.post(
            url,
            data={"requirement_id": str(requirement_id)}
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 409)

        self.assertEqual(
            len(database.get_task_requirements(project_id, task_id)),
            1
        )


    def test_link_task_requirement_cross_project_route(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        task_id = database.create_task(
            project_a,
            "Project A task"
        )

        connection = database.get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, completed, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_b,
                    "Project B requirement",
                    "must_have",
                    0,
                    0
                )
            )
            requirement_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        response = self.client.post(
            f"/projects/{project_a}/tasks/{task_id}/requirements",
            data={"requirement_id": str(requirement_id)}
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            database.get_task_requirements(project_a, task_id),
            []
        )


    def test_unlink_task_requirement_route(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id,
            "Test task"
        )

        # Create requirement.
        connection = database.get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, completed, position)
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

        # 1. Create the relationship.
        database.link_task_requirement(
            project_id,
            task_id,
            requirement_id
        )

        # 2. Verify the relationship exists.
        linked = database.get_task_requirements(
            project_id,
            task_id
        )

        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["id"], requirement_id)

        # 3. Unlink through the Flask route.
        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}"
            f"/requirements/{requirement_id}/delete"
        )

        self.assertEqual(response.status_code, 302)

        # 4. Verify the relationship was removed.
        linked = database.get_task_requirements(
            project_id,
            task_id
        )

        self.assertEqual(len(linked), 0)

        # 5. Verify the task still exists.
        self.assertIsNotNone(
            database.get_task(project_id, task_id)
        )

        # 6. Verify the requirement still exists.
        connection = database.get_connection()

        try:
            requirement = connection.execute(
                """
                SELECT id
                FROM requirements
                WHERE id = ?
                """,
                (requirement_id,)
            ).fetchone()

            self.assertIsNotNone(requirement)

        finally:
            connection.close()


    def test_unlink_task_requirement_missing_link(self):
        project_id = self.create_test_project()
        task_id = database.create_task(
            project_id, "Test task"
        )

        response = self.client.post(
            f"/projects/{project_id}/tasks/{task_id}"
            "/requirements/999999/delete"
        )

        self.assertEqual(response.status_code, 404)



    def test_unlink_task_requirement_cross_project_route(self):
        project_a = self.create_test_project("Project A")
        project_b = self.create_test_project("Project B")

        task_id = database.create_task(
            project_a, "Project A task"
        )

        connection = database.get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, completed, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_a,
                    "Project A requirement",
                    "must_have",
                    0,
                    0
                )
            )
            requirement_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        database.link_task_requirement(
            project_a, task_id, requirement_id
        )

        response = self.client.post(
            f"/projects/{project_b}/tasks/{task_id}"
            f"/requirements/{requirement_id}/delete"
        )

        self.assertEqual(response.status_code, 404)

        # Original relationship must remain intact.
        requirements = database.get_task_requirements(
            project_a, task_id
        )

        self.assertEqual(len(requirements), 1)
        self.assertEqual(
            requirements[0]["id"],
            requirement_id
        )



    def test_unlink_task_requirement_get_rejected(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id, "Test task"
        )

        response = self.client.get(
            f"/projects/{project_id}/tasks/{task_id}"
            "/requirements/999999/delete"
        )

        self.assertEqual(response.status_code, 405)


    
    def test_execution_displays_linked_requirements(self):
        project_id = self.create_test_project()

        # Create a task.
        task_id = database.create_task(
            project_id,
            "Implement authentication"
        )

        # Create a requirement for the project.
        connection = database.get_connection()

        try:
            cursor = connection.execute(
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
                    "Secure user authentication",
                    "must_have",
                    0
                )
            )

            requirement_id = cursor.lastrowid
            connection.commit()

        finally:
            connection.close()

        # Link the task and requirement.
        database.link_task_requirement(
            project_id,
            task_id,
            requirement_id
        )

        # Request the Execution page.
        response = self.client.get(
            f"/projects/{project_id}/execution"
        )

        # Verify successful rendering.
        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)

        # Task and requirement should both appear.
        self.assertIn(
            "Implement authentication",
            html
        )

        self.assertIn(
            "Secure user authentication",
            html
        )

        # Verify the Unlink form points to the correct endpoint.
        self.assertIn(
            f"/projects/{project_id}/tasks/{task_id}"
            f"/requirements/{requirement_id}/delete",
            html
        )

    
    def test_execution_filters_linked_requirements(self):
        project_id = self.create_test_project()

        task_id = database.create_task(
            project_id,
            "Implement authentication"
        )

        connection = database.get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, position)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, "Password hashing", "must_have", 0)
            )
            linked_id = cursor.lastrowid

            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, position)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, "Session management", "must_have", 1)
            )
            available_id = cursor.lastrowid

            connection.commit()

        finally:
            connection.close()

        database.link_task_requirement(
            project_id,
            task_id,
            linked_id
        )

        response = self.client.get(
            f"/projects/{project_id}/execution"
        )

        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)

        # The linked requirement should be displayed.
        self.assertIn("Password hashing", html)

        # The linked requirement must not be selectable again.
        self.assertNotIn(
            f'<option value="{linked_id}">',
            html
        )

        # The unlinked requirement must remain selectable.
        self.assertIn(
            f'<option value="{available_id}">',
            html
        )


    def test_execution_requirements_project_isolation(self):
        # Create two independent projects.
        project_a = self.create_test_project()
        project_b = self.create_test_project()

        # Create a task belonging to Project A.
        task_id = database.create_task(
            project_a,
            "Implement authentication"
        )

        connection = database.get_connection()

        try:
            # Requirement belonging to Project A.
            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, position)
                VALUES (?, ?, ?, ?)
                """,
                (
                    project_a,
                    "Project A authentication",
                    "must_have",
                    0
                )
            )
            requirement_a_id = cursor.lastrowid

            # Requirement belonging to Project B.
            cursor = connection.execute(
                """
                INSERT INTO requirements
                    (project_id, text, type, position)
                VALUES (?, ?, ?, ?)
                """,
                (
                    project_b,
                    "Project B authentication",
                    "must_have",
                    0
                )
            )
            requirement_b_id = cursor.lastrowid

            connection.commit()

        finally:
            connection.close()

        # Request Project A's Execution page.
        response = self.client.get(
            f"/projects/{project_a}/execution"
        )

        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)

        # Project A's requirement must be available.
        self.assertIn(
            f'<option value="{requirement_a_id}">',
            html
        )

        self.assertIn(
            "Project A authentication",
            html
        )

        # Project B's requirement must not appear.
        self.assertNotIn(
            f'<option value="{requirement_b_id}">',
            html
        )

        self.assertNotIn(
            "Project B authentication",
            html
        )

        # Confirm Project A's task appears.
        self.assertIn(
            "Implement authentication",
            html
        )




if __name__ == "__main__":
    unittest.main()
