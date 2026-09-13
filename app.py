from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def dashboard():
    pass
    return render_template("projects.html")
    


@app.route("/overview", methods=["GET", "POST"])
def overview():
    if request.method == "POST":
        project_title = request.form["project_title"]
        project_description = request.form["project_description"]
        project_reason = request.form["project_reason"]
        success_criteria = request.form["success_criteria"]

        print(project_title)
        print(project_description)
        print(project_reason)
        print(success_criteria)

    return render_template("index.html")


@app.route("/design")
def design():
    return render_template("design.html")


@app.route("/build")
def build():
    return render_template("build.html")


@app.route("/testing")
def testing():
    return render_template("testing.html")


@app.route("/learning")
def learning():
    return render_template("learning.html")


@app.route("/log")
def log():
    return render_template("log.html")


@app.route("/interview-prep")
def interview_prep():
    return render_template("interview_prep.html")


@app.route("/write-up")
def write_up():
    return render_template("write_up.html")


@app.route("/retrospective")
def retrospective():
    return render_template("retrospective.html")


if __name__ == "__main__":
    app.run(debug=True)