from flask import Flask, render_template, request

app = Flask(__name__)


projects = [
    {
        "id": 1,
        "title": "Raspberry Pi Homelab",
        "category": "Cybersecurity / Infrastructure",
        "status": "In Progress",
        "current_stage": "Testing",
        "progress": 80,
        "next_action": "Add system monitoring",
        "last_updated": "2026-09-12"
    },

    {
        "id": 2,
        "title": "Portfolio Website",
        "category": "Full Stack",
        "status": "In Progress",
        "current_stage": "Implementation",
        "progress": 60,
        "next_action": "Finish projects section",
        "last_updated": "2026-09-11"
    }
]

@app.route("/", methods = ['Get', 'Post'] )
def dashboard():
    return render_template("projects.html", projects=projects)
    


@app.route("/projects/<int:project_id>")
def project_overview(project_id):
    project = next(
        (project for project in projects if project["id"] == project_id),
        None
    )

    if project is None:
        return "Project n0t found", 404
    return render_template("project_overview.html", project = project)

@app.route("/projects/new", methods=["GET","POST"]):
def create_project():

    if request.method == "POST":
         # Later:
        # 1. Read form
        # 2. Validate
        # 3. Generate ID
        # 4. Create project
        # 5. Add to projects
        # 6. Redirect to new project
        pass

    # Get ends here.
    return render_template("create_project.html")

# @app.route("/design")
# def design():
#     return render_template("design.html")


# @app.route("/build")
# def build():
#     return render_template("build.html")


# @app.route("/testing")
# def testing():
#     return render_template("testing.html")


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