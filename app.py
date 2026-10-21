from flask import Flask, render_template, request, redirect, url_for, abort
from database import init_db , create_project as db_create_project
from database import get_project , get_all_projects , design_project , get_project_design
from database import delete_project, update_project, get_technologies

app = Flask(__name__)

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
    
    return render_template("project_dashboard.html",
                            project = project,
                            design_data = design_data,
                            technologies = technologies)


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

        diagram = request.files.get("architecture_diagram")

        if diagram and diagram.filename:
            print("Uploaded diagram:", diagram.filename)

        technologies = []

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
        

        design_project(
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

   

        return redirect(
            url_for(
                "project_dashboard",
                project_id=project_id
            )
        )

     #GET: retrieve existing design data
    design_data = get_project_design(project_id)
    technologies = get_technologies(project_id)
    print("TECHNOLOGIES:", technologies)
    return render_template(
        "design.html",
        project=project,
        design_data = design_data,
        technologies= technologies
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