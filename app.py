from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os
import subprocess
import tempfile
import cloudinary
import cloudinary.uploader
import cloudinary.api
from sqlalchemy import text

# =====================================
#            FLASK SETUP
# =====================================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nsluvurhozqetrxz")

# ============ DATABASE (SQLite) =============
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///AI_IDE.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
db = SQLAlchemy(app)

# ==================== Cloudinary Configuration =================
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "YOUR_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY", "YOUR_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", "YOUR_API_SECRET"),
    secure=True
)

# =====================================
#              DATABASE MODELS
# =====================================
class User(db.Model):
    """User account information and storage tracking"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    linkedin_url = db.Column(db.String(200), nullable=True)
    
    # Storage tracking
    storage_used = db.Column(db.Float, default=0.0)  # Current usage in MB
    max_storage_mb = db.Column(db.Float, default=500.0)  # 500 MB limit per user
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='owner', lazy=True, cascade='all, delete-orphan')
    files = db.relationship('FileDetails', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'


class Project(db.Model):
    """User projects with metadata"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(1000), nullable=True)
    repo_link = db.Column(db.String(200), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    files = db.relationship('FileDetails', backref='project', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Project {self.name}>'


class FileDetails(db.Model):
    """File metadata and content storage"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    language = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Store file content
    cloudinary_url = db.Column(db.String(500), nullable=True)  # Cloud storage URL
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<File {self.filename}>'

import google.generativeai as genai

# ... (Existing imports)

# =====================================
#         GEMINI AI SETUP
# =====================================
# =====================================
#         GEMINI AI SETUP
# =====================================
# 1. Get your key from https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", 'AIzaSyCe-j3YXcDECkupfUDxqPhHjsWYjWBrQ9Y')
genai.configure(api_key=GEMINI_API_KEY)

# 2. Initialize with a VALID model name (Case sensitive: must be 'gemini')
# Recommended models: 'gemini-1.5-flash' (fast) or 'gemini-1.5-pro' (complex)
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro", 
    system_instruction="You are an expert AI Coding Assistant. Keep answers technical and brief."
)

# =====================================
#            AUTHENTICATION HELPERS
# =====================================
def login_required(fn):
    """Decorator to protect routes that require authentication"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def get_current_user():
    """Get the currently logged-in user object"""
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None


# =====================================
#            MAIN ROUTES
# =====================================
@app.route('/')
def index():
    """Homepage - redirect to dashboard if logged in"""
    if "user_id" in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login')) # done


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing projects and stats"""
    user = get_current_user()
    projects = Project.query.filter_by(user_id=user.id).order_by(Project.updated_at.desc()).all()
    
    # Calculate statistics
    total_files = FileDetails.query.filter_by(user_id=user.id).count()
    storage_percent = (user.storage_used / user.max_storage_mb) * 100 if user.max_storage_mb > 0 else 0
    
    return render_template('dashboard.html', 
                         user=user, 
                         projects=projects,
                         total_files=total_files,
                         storage_percent=storage_percent) # done



@app.route("/login", methods=["GET", "POST"])
def login():
    """User login page"""
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash("Please provide both username and password.", "error")
            return redirect(url_for("login"))

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password. Please try again.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration page"""
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        linkedin_url = request.form.get('linkedin_url', '').strip()

        # Validation
        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("register"))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("register"))
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("This username is already taken. Please choose another.", "error")
            return redirect(url_for("register"))

        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, linkedin_url=linkedin_url)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "error")
            app.logger.error(f"Registration error: {str(e)}")
            return redirect(url_for("register"))

    return render_template("register.html") # done


@app.route("/logout")
def logout():
    """Log out the current user"""
    username = session.get("username", "User")
    session.clear()
    flash(f"Goodbye, {username}! You've been logged out successfully.", "info")
    return redirect(url_for("login")) # done


# =====================================
#            PROJECT ROUTES
# =====================================
@app.route('/projects')
@login_required
def projects():
    """List all user projects"""
    user = get_current_user()
    user_projects = Project.query.filter_by(user_id=user.id).order_by(Project.updated_at.desc()).all()
    return render_template('projects.html', projects=user_projects) # done



@app.route('/project/create', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create a new project"""
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        repo_link = request.form.get('repo_link', '').strip()
        
        if not name:
            flash("Project name is required.", "error")
            return redirect(url_for("create_project")) # done
        
        user = get_current_user()
        new_project = Project(
            user_id=user.id,
            name=name,
            description=description,
            repo_link=repo_link
        )
        
        try:
            db.session.add(new_project)
            db.session.commit()
            flash(f"Project '{name}' created successfully!", "success")
            return redirect(url_for('project_detail', project_id=new_project.id)) # done
        except Exception as e:
            db.session.rollback()
            flash("Error creating project. Please try again.", "error")
            app.logger.error(f"Project creation error: {str(e)}")
            return redirect(url_for("create_project"))
    
    return render_template('create_project.html')


@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    """View project details and files"""
    user = get_current_user()
    project = Project.query.filter_by(id=project_id, user_id=user.id).first()
    
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for('projects'))
    
    files = FileDetails.query.filter_by(project_id=project_id).order_by(FileDetails.last_updated.desc()).all()
    return render_template('project_detail.html', project=project, files=files)


@app.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Delete a project"""
    user = get_current_user()
    project = Project.query.filter_by(id=project_id, user_id=user.id).first()
    
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for('projects'))
    
    try:
        db.session.delete(project)
        db.session.commit()
        flash(f"Project '{project.name}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting project.", "error")
        app.logger.error(f"Project deletion error: {str(e)}")
    
    return redirect(url_for('projects'))


# =====================================
#            FILE UPLOAD & MANAGEMENT
# =====================================
@app.route('/files')
@login_required
def file_manager():
    """File manager page"""
    user = get_current_user()
    files = FileDetails.query.filter_by(user_id=user.id).order_by(FileDetails.last_updated.desc()).all()
    return render_template('file_manager.html', user=user, files=files) # done


@app.route('/file/upload', methods=['GET', 'POST'])
@login_required
def file_upload():
    """Upload a file to cloud storage"""
    user = get_current_user()

    if request.method == "POST":
        # Check if file is in request
        if "file" not in request.files:
            flash("No file selected for upload.", "error")
            return redirect(request.url)

        file = request.files["file"]
        
        if not file or file.filename == "":
            flash("Please select a file to upload.", "error")
            return redirect(request.url)

        # Get file size
        file.seek(0, os.SEEK_END)
        size_bytes = file.tell()
        file.seek(0)
        file_size_mb = size_bytes / (1024 * 1024)

        # Check storage limits
        remaining_mb = user.max_storage_mb - (user.storage_used or 0.0)
        if file_size_mb > remaining_mb:
            flash(f"Upload would exceed your storage limit. You have {remaining_mb:.2f} MB remaining, but the file is {file_size_mb:.2f} MB.", "error")
            return redirect(url_for("file_manager"))

        try:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                folder=f"user_uploads/{user.id}/",
                resource_type="auto"
            )

            # Get metadata from form
            filename = request.form.get('filename', file.filename)
            description = request.form.get('description', '')
            language = request.form.get('language', 'text')
            project_id = request.form.get('project_id')

            # Create file record
            new_file = FileDetails(
                user_id=user.id,
                project_id=project_id if project_id else None,
                filename=filename,
                description=description,
                language=language,
                cloudinary_url=upload_result.get('secure_url')
            )

            # Update user storage
            uploaded_mb = upload_result.get("bytes", size_bytes) / (1024 * 1024)
            user.storage_used = (user.storage_used or 0.0) + uploaded_mb

            db.session.add(new_file)
            db.session.commit()

            flash(f"File '{filename}' uploaded successfully!", "success")
            return redirect(url_for("file_manager"))

        except Exception as e:
            db.session.rollback()
            flash(f"Upload failed: {str(e)}", "error")
            app.logger.error(f"File upload error: {str(e)}")
            return redirect(url_for("file_manager"))

    # GET request - show upload form
    projects = Project.query.filter_by(user_id=user.id).all()
    return render_template("file_upload.html", user=user, projects=projects) # done




@app.route('/file/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file(file_id):
    """Delete a file"""
    user = get_current_user()
    file = FileDetails.query.filter_by(id=file_id, user_id=user.id).first()
    
    if not file:
        return jsonify({"status": "error", "message": "File not found"}), 404
    
    try:
        db.session.delete(file)
        db.session.commit()
        return jsonify({"status": "success", "message": "File deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# =====================================
#            CODE IDE
# =====================================
@app.route('/ide', methods=['GET'])
@login_required
def ide():
    """Code IDE interface"""
    user = get_current_user()
    projects = Project.query.filter_by(user_id=user.id).all()
    return render_template('ide.html', user=user, projects=projects) # done


@app.route('/ide/save', methods=['POST'])
@login_required
def save_code():
    """Save code from IDE"""
    user = get_current_user()
    data = request.get_json()
    
    project_id = data.get('project_id')
    filename = data.get('filename')
    content = data.get('content')
    language = data.get('language')

    if not all([filename, content, language]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # Check if project exists (if provided)
    if project_id:
        project = Project.query.filter_by(id=project_id, user_id=user.id).first()
        if not project:
            return jsonify({"status": "error", "message": "Project not found"}), 404

    # Check if file exists
    file_detail = FileDetails.query.filter_by(
        user_id=user.id, 
        project_id=project_id, 
        filename=filename
    ).first()

    try:
        if file_detail:
            # Update existing file
            file_detail.content = content
            file_detail.language = language
            file_detail.last_updated = datetime.utcnow()
            message = "File updated successfully"
        else:
            # Create new file
            file_detail = FileDetails(
                user_id=user.id,
                project_id=project_id,
                filename=filename,
                content=content,
                language=language
            )
            db.session.add(file_detail)
            message = "File created successfully"

        db.session.commit()
        return jsonify({"status": "success", "message": message, "file_id": file_detail.id})
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving file: {str(e)}")
        return jsonify({"status": "error", "message": f"Error saving file: {str(e)}"}), 500


@app.route('/ide/execute', methods=['POST'])
@login_required
def execute_code():
    """Execute code and return output"""
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')

    if not code:
        return jsonify({"status": "error", "message": "No code provided"}), 400

    # This is a simplified example for educational purposes
    
    try:
        if language == 'python':
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Execute with timeout
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Clean up
            os.unlink(temp_file)

            output = result.stdout if result.returncode == 0 else result.stderr
            status = "success" if result.returncode == 0 else "error"

            return jsonify({
                "status": status,
                "output": output,
                "return_code": result.returncode
            })
        
        else:
            return jsonify({"status": "error", "message": f"Language '{language}' not supported"}), 400

    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Code execution timeout (5 seconds)"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/ide/sql/execute', methods=['POST'])
@login_required
def execute_sql():
    """Execute SQL query"""
    user = get_current_user()
    data = request.get_json()
    sql_code = data.get('sql_code', '').strip()

    if not sql_code:
        return jsonify({"status": "error", "message": "No SQL code provided"}), 400

    try:
        with db.engine.connect() as connection:
            trans = connection.begin()
            try:
                result = connection.execute(text(sql_code))
                
                if result.returns_rows:
                    # SELECT query
                    rows = [dict(row._mapping) for row in result.fetchall()]
                    output = {
                        "status": "success",
                        "message": f"Query executed successfully. {len(rows)} rows returned.",
                        "results": rows
                    }
                else:
                    # INSERT, UPDATE, DELETE, etc.
                    output = {
                        "status": "success",
                        "message": f"Query executed successfully. {result.rowcount} rows affected."
                    }
                
                trans.commit()
                
            except Exception as e:
                trans.rollback()
                output = {"status": "error", "message": f"SQL execution failed: {str(e)}"}

    except Exception as e:
        output = {"status": "error", "message": f"Database error: {str(e)}"}

    return jsonify(output)


# =====================================
#            AI ASSISTANT (Gemini)
# =====================================
@app.route('/ai-assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    """AI coding assistant interface"""
    return render_template('ai_assistant.html')

@app.route('/ai-assistant/chat', methods=['POST'])
@login_required
def ai_chat():
    """Handle chat requests from the AI Assistant interface"""
    data = request.get_json()
    user_message = data.get('message', '')
    context_code = data.get('code', '')  # Optional: Pass code from the IDE for context

    if not user_message:
        return jsonify({"status": "error", "message": "No message provided"}), 400

    try:
        # Construct the prompt with context if available
        full_prompt = user_message
        if context_code:
            full_prompt = f"Context Code:\n```{context_code}```\n\nUser Question: {user_message}"

        response = model.generate_content(full_prompt)
        
        return jsonify({
            "status": "success",
            "reply": response.text
        })

    except Exception as e:
        app.logger.error(f"AI Assistant Error: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to get AI response"}), 500


# =====================================
#            ERROR HANDLERS
# =====================================
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('500.html'), 500


# =====================================
#            UTILITY ROUTES
# =====================================
@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    user = get_current_user()
    return render_template('profile.html', user=user)


@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    user = get_current_user()
    
    linkedin_url = request.form.get('linkedin_url', '').strip()
    user.linkedin_url = linkedin_url
    
    try:
        db.session.commit()
        flash("Profile updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error updating profile.", "error")
        app.logger.error(f"Profile update error: {str(e)}")
    
    return redirect(url_for('profile'))


# =====================================
#            APPLICATION STARTUP
# =====================================
if __name__ == "__main__":
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        print("✓ Database tables created successfully")
        print("✓ Starting Flask AI IDE application...")
        print("✓ Access the application at http://127.0.0.1:5000")

    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
