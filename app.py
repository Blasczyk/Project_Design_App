from flask import Flask, render_template, request, redirect, url_for, abort
from database import init_db , create_project as db_create_project
from database import get_project , get_all_projects , design_project , get_project_design, get_connection
from database import delete_project, update_project, get_technologies , validate_design
from database import delete_architecture_diagram, get_architecture_diagrams, add_architecture_diagram
from pathlib import Path
from uuid import uuid4
from PIL import Image, UnidentifiedImageError 
from flask import send_from_directory, abort
from flask import redirect, url_for, flash
from werkzeug.exceptions import RequestEntityTooLarge
import warnings





app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

UPLOAD_FOLDER = Path(app.instance_path) /"uploads" / "architecture"

ALLOWED_EXTENSIONS = {".png", ".jpg",".jpeg", ".webp"}

MAX_DIAGRAM_SIZE = 10 * 1024 * 1024

init_db()


@app.route("/")
def project_repo():

    projects = get_all_projects()
    return render_template("projects.html", projects=projects)
    


@app.route("/projects/new", methods=["GET","POST"])
def create_project():

    if request.method == "POST":
        title = request.form.get("title")
        what = request.form.get("what")
        why =request.form.get("why")
        success = request.form.get("success")

        print(title)
        print(what)
        print(why)
        print(success)

        project_id = db_create_project(
            title,
            what,
            why,
            success
        )
       
        return redirect(url_for("project_dashboard", project_id=project_id))

    # Get ends here.
    return render_template("create_project.html")


@app.route("/projects/<int:project_id>")
def project_dashboard(project_id):
    project = get_project(project_id)

    if project is None:
        return "Project not found", 404

    design_data = get_project_design(project_id)
    technologies = get_technologies(project_id)
    diagrams = get_architecture_diagrams(project_id)

    return render_template(
        "project_dashboard.html",
        project=project,
        design_data=design_data,
        technologies=technologies,
        diagrams=diagrams
    )


@app.route(
    "/projects/<int:project_id>/design",
    methods=["GET", "POST"]
)
def design(project_id):

    project = get_project(project_id)

    if project is None:
        return "Project not found", 404

    if request.method == "POST":

        problem = request.form.get("problem")
        must_have_ids = request.form.getlist("must_have_id")
        must_have = request.form.getlist("must_have")

        nice_have_ids = request.form.getlist("nice_have_id")
        nice_to_have = request.form.getlist("nice_have")
        constraints = request.form.getlist("constraints")
        # 
        architecture_overview = request.form.get("architecture_system_overview")
        architecture_components = request.form.getlist("component")
        architecture_flow = request.form.get("data_flow")
        risks = request.form.getlist("risks")
       
        # Architecutural Technologies
        technology_names = request.form.getlist("technology_name")
        technology_reasons = request.form.getlist("technology_reason")
        technology_alternatives = request.form.getlist("technology_alternative")
        technology_tradeoffs = request.form.getlist("technology_tradeoff")

        technologies = []
        technology_counts = [
            len(technology_names),
            len(technology_reasons),
            len(technology_alternatives),
            len(technology_tradeoffs)
            ]

        if len(set(technology_counts)) != 1:
            raise ValueError("Technology fields do not match")

        for name, reason, alternative, tradeoff in zip(
            technology_names,
            technology_reasons,
            technology_alternatives,
            technology_tradeoffs
        ):
            if name.strip():
                technologies.append({
                    "name": name.strip(),
                    "reason": reason.strip(),
                    "alternative": alternative.strip(),
                    "tradeoff": tradeoff.strip()
                })

        print("COMPONENTS RECEIVED:", architecture_components)
        

        # Step 5.10.2 - Save design and diagram
        diagram = request.files.get("architecture_diagram")
        diagram_data = None
        connection = None

        try:
            # Validate the design before making database changes
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

            # Validate and save the uploaded file
            if diagram and diagram.filename:
                diagram_data = save_architecture_diagram(
                    diagram,
                    project_id
                )

            # Start one database transaction
            connection = get_connection()
            connection.execute("BEGIN")

            design_project(
                connection,
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
            )

            if diagram_data is not None:
                add_architecture_diagram(
                    connection,
                    project_id,
                    diagram_data
                )

            # Commit only after all SQL operations succeed
            connection.commit()

        except ValueError as error:
            if connection is not None:
                connection.rollback()

            if diagram_data is not None:
                uploaded_path = UPLOAD_FOLDER / diagram_data["file_path"]
                uploaded_path.unlink(missing_ok=True)

            restored_design, restored_technologies = restore_design_form(
                request.form
            )

            return render_template(
                "design.html",
                project=project,
                design_data=restored_design,
                technologies=restored_technologies,
                diagrams=get_architecture_diagrams(project_id),
                form_values=request.form,
                error=str(error)
            ), 400

        except Exception:
            if connection is not None:
                connection.rollback()

            if diagram_data is not None:
                uploaded_path = UPLOAD_FOLDER / diagram_data["file_path"]
                uploaded_path.unlink(missing_ok=True)

            app.logger.exception("Failed to save project design")

            return "Unable to save project design.", 500

        finally:
            if connection is not None:
                connection.close()


        return redirect(
            url_for(
                "project_dashboard",
                project_id=project_id
            )
        )

     #GET: retrieve existing design data
    design_data = get_project_design(project_id)
    technologies = get_technologies(project_id)
    diagrams = get_architecture_diagrams(project_id)

    


    
    return render_template(
    "design.html",
    project=project,
    design_data=design_data,
    technologies=technologies,
    diagrams=diagrams,
    form_values={},
    error=None
)


@app.route("/projects/<int:project_id>/build", methods =["GET","POST"])
def build(project_id):

    project = get_project(project_id)
    
    
    if project is None:
        return "Project not found", 404

    if request.method == "POST":
        print("helloworld")

    return render_template("build.html", project= project)


@app.route("/projects/<int:project_id>/testing" , methods = ["GET","POST"])
def testing(project_id):

    project = get_project(project_id)

    if project is None:
        return "Project not Found.", 404

    if request.method == "POST":
        print("helloworld")
    return render_template("testing.html",project = project)


@app.route(
    "/projects/<int:project_id>/edit", methods = ["GET","POST"])
def edit_project(project_id):

    project = get_project(project_id)

    if project is None:
        return "Project not found", 404

    if request.method == "POST":
        title = request.form.get("title")
        what = request.form.get("what")
        why = request.form.get("why")
        success = request.form.get("success")

        update_project(
            project_id, title, what, why, success
        )
        # updated_project = get_project(project_id)
        # print("DATABASE AFTER UPDATE:", dict(updated_project))

        return redirect(
            url_for("project_dashboard", project_id=project_id)
        )

    return render_template("edit_project.html", project=project)


@app.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project_route(project_id):
    deleted = delete_project(project_id)

    if deleted == 0:
        abort(404)

    return redirect(url_for("project_repo"))



@app.route(
    "/projects/<int:project_id>/requirements/<int:requirement_id>/completion",
    methods=["POST"]
)
def update_requirement(project_id, requirement_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or type(data.get("completed")) is not bool:
        return {"error": "Invalid completion value"}, 400

    updated = update_requirement_completion(
        project_id,
        requirement_id,
        data["completed"]
    )

    if not updated:
        return {"error": "Requirement not found"}, 404

    return {"success": True}, 200


def save_architecture_diagram(file, project_id):

    if not file or not file.filename:
        return None

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported diagram format")

    # Read at most 10 MB + 1 byte
    content = file.stream.read(MAX_DIAGRAM_SIZE + 1)

    if len(content) > MAX_DIAGRAM_SIZE:
        raise ValueError("Diagram exceeds 10 MB")

    # Validate that the content is a real image
    from io import BytesIO

    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning
            )

            with Image.open(BytesIO(content)) as image:
                image.verify()

            with Image.open(BytesIO(content)) as image:
                actual_format = image.format

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError
    ) as error:
        raise ValueError("Invalid or unsafe image file") from error

    formats = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".webp": "WEBP"
    }

    if actual_format != formats[extension]:
        raise ValueError("File extension does not match image format")

    project_folder = UPLOAD_FOLDER / f"project_{project_id}"
    project_folder.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4().hex}{extension}"
    destination = project_folder / stored_filename

    destination.write_bytes(content)

    return {
        "original_filename": Path(file.filename).name,
        "stored_filename": stored_filename,
        "file_path": str(
            Path(f"project_{project_id}") / stored_filename
        )
    }


@app.route(
    "/projects/<int:project_id>/diagrams/<int:diagram_id>"
)
def serve_architecture_diagram(project_id, diagram_id):

    connection = get_connection()

    try:
        diagram = connection.execute(
            """
            SELECT stored_filename
            FROM architecture_diagrams
            WHERE id = ? AND project_id = ?
            """,
            (diagram_id, project_id)
        ).fetchone()

    finally:
        connection.close()

    if diagram is None:
        abort(404)

    project_folder = (
        UPLOAD_FOLDER / f"project_{project_id}"
    )

    return send_from_directory(
        project_folder,
        diagram["stored_filename"]
    )



@app.route(
    "/projects/<int:project_id>/diagrams/<int:diagram_id>/delete",
    methods=["POST"]
)
def remove_architecture_diagram(project_id, diagram_id):

    diagram = delete_architecture_diagram(
        project_id,
        diagram_id
    )

    if diagram is None:
        abort(404)

    project_folder = UPLOAD_FOLDER / f"project_{project_id}"

    file_path = project_folder / diagram["stored_filename"]

    # Remove the physical file if it exists
    file_path.unlink(missing_ok=True)

    return redirect(
        url_for("design", project_id=project_id)
    )




@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(error):
    return (
        "Upload rejected: request exceeds the 12 MB limit.",
        413
    )


def restore_design_form(form):
    def text_items(name):
        return [
            {"text": text}
            for text in form.getlist(name)
        ]

    def requirements(id_name, text_name):
        ids = form.getlist(id_name)
        texts = form.getlist(text_name)

        return [
            {
                "id": ids[i] if i < len(ids) else "",
                "text": text
            }
            for i, text in enumerate(texts)
        ]

    technology_fields = (
        "technology_name",
        "technology_reason",
        "technology_alternative",
        "technology_tradeoff"
    )

    values = [
        form.getlist(field)
        for field in technology_fields
    ]

    technology_count = max(
        (len(items) for items in values),
        default=0
    )

    technologies = []

    for i in range(technology_count):
        def field_value(items):
            return items[i] if i < len(items) else ""

        technologies.append({
            "name": field_value(values[0]),
            "reason": field_value(values[1]),
            "alternative": field_value(values[2]),
            "tradeoff": field_value(values[3])
        })

    design_data = {
        "must_have": requirements("must_have_id", "must_have"),
        "nice_to_have": requirements("nice_have_id", "nice_have"),
        "constraints": text_items("constraints"),
        "components": text_items("component"),
        "risks": text_items("risks")
    }

    return design_data, technologies

# @app.route("/learning")
# def learning():
#     return render_template("learning.html")


# @app.route("/log")
# def log():
#     return render_template("log.html")


# @app.route("/interview-prep")
# def interview_prep():
#     return render_template("interview_prep.html")


# @app.route("/write-up")
# def write_up():
#     return render_template("write_up.html")


# @app.route("/retrospective")
# def retrospective():
#     return render_template("retrospective.html")


if __name__ == "__main__":
    app.run(debug=True)