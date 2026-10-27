
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app as app_module

from io import BytesIO
from PIL import Image
from werkzeug.datastructures import FileStorage

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




if __name__ == "__main__":
    unittest.main()
