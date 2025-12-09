from flask import Flask, render_template, request, redirect, session, flash, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os

import cloudinary
import cloudinary.uploader
import cloudinary.api

# =====================================
#            FLASK SETUP
# =====================================
app = Flask(__name__)
app.secret_key = "nsluvurhozqetrxz"

# ============ DATABASE (SQLite) =============
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///AI_IDE.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

### ==================== Cloudinary =================
# Replace these with your actual Cloudinary credentials
cloudinary.config(
    cloud_name="YOUR_CLOUD_NAME",
    api_key="YOUR_API_KEY",
    api_secret="YOUR_API_SECRET",
    secure=True
)

# =====================================
#              MODELS
# =====================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    Linkedin_url = db.Column(db.varchar(100),nullable=False)

    # Extra fields for file tracking
    storage_used = db.Column(db.Float, default=0.0)       # current usage in MB
    max_storage_mb = db.Column(db.Float, default=500.0)  # 500 MB per user
    
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Uid = db.Column(db.Integer , db.ForeignKey('Uid') ,nullable = False)
    name = db.Column(db.String(80), unique=True, nullable=False)
    discreption = db.Column(db.String(1000), nullable=True)
    repolink = db.Column(db.varchar(100),nullable=False)
    
# id, project_id, filename, content, language, last_updated
class File_Details(db.Model):
    id = db.Column(db.Integer , primary_key = True)
    Uid = db.Column(db.Integer , db.ForeignKey('Uid'), nullable = False)
    filename = db.Column(db.String(20) , nullable = False)
    discreption = db.Column(db.String(100) , nullable = True)
    language = db.Column(db.String(10),nullable = False)
    


# =====================================
#            AUTH HELPERS
# =====================================
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in to access that page.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


# =====================================
#            ROUTES
# =====================================
@app.route('/')
def index():
    return render_template('dashbord.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route('/home/<UID>', methods=['GET', 'POST'])
@login_required
def home(projectID):
    # example: you can fetch project info here
    return render_template('Home.html', projectID=projectID)


# =====================================
#            File & Cloud
# =====================================
MAX_STORAGE_MB = 500  # app-level cap (per user is also stored in DB)

@app.route('/file', methods=['GET', 'POST'])
@login_required
def file():
    return render_template('file_select.html', user=user)


@app.route('/file/load', methods=['GET', 'POST'])
@login_required
def file_load():
    # GET -> show upload page
    return render_template("file_load.html", user=user)


# =====================================
#            APP BOOT
# =====================================
if __name__ == "__main__":
    # create tables if they don't exist
    with app.app_context():
        db.create_all()

    app.run(debug=True)
