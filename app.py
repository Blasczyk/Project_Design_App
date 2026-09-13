from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/overview', methods=['GET', 'POST'])
def overview():
    if request.method == 'POST':
        # Handle form submission here
        project_name = request.form['Project Title']
        # You can add logic to save the project name or perform other actions
        return redirect(url_for('project'))  # Redirect to the same page after submission

    return render_template('index.html')
