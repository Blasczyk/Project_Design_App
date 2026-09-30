from flask import Flask, render_template, request, redirect, url_for
from database import init_db , create_project as db_create_project
from database import get_project , get_all_projects

app = Flask(__name__)

init_db()


@app.route("/")
def Project_Repo():

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
        return "Project n0t found", 404
    
    return render_template("project_dashboard.html",
                            project = project)


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
        must_have = request.form.getlist("must_have")
        nice_to_have = request.form.getlist("nice_have")
        constraints = request.form.getlist("constraints")
        architecture = request.form.get("architecture")
        risks = request.form.getlist("risks")

        design_project(
            project_id,
            problem,
            architecture,
            must_have,
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

    return render_template(
        "design.html",
        project=project
    )


@app.route("/projects/<int:project_id>/build", methods =["GET","POST"])
def build(project_id):

    project = next(
            (project for project in projects if project["id"] == project_id),
            None
        )
    
    if project is None:
        return "Project not found", 404

    if request.method == "POST":
        print("helloworld")

    return render_template("build.html", project= project)


@app.route("/projects/<int:project_id>/testing" , methods = ["GET","POST"])
def testing(project_id):

    project = next(
        (project for project in projects if project["id"] == project_id),
         None
    )

    if project is None:
        return "Project not Found.", 404

    if request.method == "POST":
        print("helloworld")
    return render_template("testing.html",project = project)


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