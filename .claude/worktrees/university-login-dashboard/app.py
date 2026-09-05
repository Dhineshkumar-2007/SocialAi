from flask import Flask, jsonify, send_from_directory, render_template, session, redirect
from flask_cors import CORS
from config import Config
from database.db import init_db
from routes.problems import problems_bp
from routes.universities import universities_bp
from routes.projects import projects_bp
from routes.assignments import assignments_bp
from routes.dashboard import dashboard_bp
from routes.notifications import notifications_bp
from auth.routes import auth_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Ensure SECRET_KEY is set
    if not app.config.get('SECRET_KEY'):
        import os
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
    # Enable session cookies
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})
    init_db()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(problems_bp)
    app.register_blueprint(universities_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notifications_bp)

    # Health endpoint
    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        user = session.get('user')
        return jsonify({
            "status": "ok",
            "ai_enabled": Config.AI_ENABLED,
            "authenticated": bool(user),
            "user_role": user.get('role') if user else None
        })

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(Config.UPLOAD_DIR, filename)

    # Serve static files
    @app.get("/static/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory('static/css', filename)

    @app.get("/static/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory('static/js', filename)

    # Admin dashboard page — simplified single-view control panel
    @app.get("/admin")
    def admin_dashboard():
        return render_template("admin_dashboard_simple.html")

    # University login page — separate from the citizen login
    @app.get("/university/login")
    def university_login_page():
        return render_template("auth/university_login.html")

    # University dashboard page — auth guard: only logged-in universities
    @app.get("/university")
    def university_dashboard():
        user = session.get('user')
        if not user:
            return redirect('/university/login')
        if user.get('role') != 'university':
            return redirect('/university/login')
        return render_template("university/dashboard.html")

    # University registration page (separate from public dashboard / login)
    @app.get("/university/register")
    def university_register_page():
        return render_template("auth/university_register.html")

    # University workspace page
    @app.get("/workspace")
    def university_workspace():
        return render_template("university_workspace.html")

    # Industry dashboard page
    @app.get("/industry")
    def industry_dashboard():
        return render_template("industry/dashboard.html")

    # Public dashboard page
    @app.get("/dashboard")
    def public_dashboard():
        return render_template("public/dashboard.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
