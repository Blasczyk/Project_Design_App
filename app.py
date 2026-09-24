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

@app.route("/", methods = ['Get'] )
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

@app.route("/projects/new", methods=["GET","POST"])
def create_project():

    if request.method == "POST":
        project_title = request.form.get("title")
        what_building = request.form.get("what")
        why_building =request.form.get("why")
        success = request.form.get("success")

        print(project_title)
        print(what_building)
        print(why_building)
        print(success)


        new_project= {
            "id": new_id,
            "title": project_title,
            "what": what_building,
            "why": why_building,
            "success": success,
            "status": "Not Started",
            "current_stage": "Overview",
            "progress": 0,
            "next_action": "Complete project design",
        }
         # Later:
        # 1. Read form
        # 2. Validate
        # 3. Generate ID
        # 4. Create project
        # 5. Add to projects
        # 6. Redirect to new project
        

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