from flask import Flask, jsonify, send_from_directory, render_template, session, redirect
from flask_cors import CORS
from config import Config
from database.db import init_db
from routes.problems import problems_bp
from routes.universities import universities_bp
from routes.projects import projects_bp
from routes.assignments import assignments_bp
from routes.dashboard import dashboard_bp, public_bp
from routes.notifications import notifications_bp
from routes.admin import admin_bp
from auth.routes import auth_bp
from auth.decorators import login_user, logout_user, require_role
import os


def _warm_ai_models():
    """Preload the heavy AI models in the background so the first analysis
    request doesn't pay the multi-second model-load cost."""
    if not Config.AI_ENABLED:
        return
    try:
        from ai.embeddings import generate_embedding
        generate_embedding("warm-up")
    except Exception:
        pass
    try:
        from ai.vision import get_vision
        get_vision()
    except Exception:
        pass


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Ensure SECRET_KEY is set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
    # Enable session cookies
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})
    init_db()

    if Config.AI_ENABLED and not os.getenv("SOCIALAI_SKIP_WARMUP"):
        import threading
        threading.Thread(target=_warm_ai_models, daemon=True).start()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(problems_bp)
    app.register_blueprint(universities_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)

    # Inject user into all templates for navbar (login state / role / page locks)
    @app.context_processor
    def inject_user():
        user = session.get('user') or {}
        return dict(
            user_role=user.get('role'),
            user_email=user.get('email'),
            user_name=user.get('name'),
        )

    # Health endpoint
    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/report")
    def report_page():
        """Landing page for the report flow.

        The old 4-step wizard (templates/report.html) was never wired to a
        route, so navbar/template links to /report 404'd. Route citizens to
        the real, login-gated submission page instead."""
        return redirect("/citizen/submit")

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

    # Admin dashboard page — simplified single-view control panel
    @app.get("/admin")
    def admin_dashboard():
        user = session.get('user')
        if not user:
            return redirect('/login')
        if user.get('role') not in ('admin', 'superadmin'):
            return redirect('/login')
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
    @app.get("/register")
    def common_register_page():
        return render_template("auth/register.html")

    @app.get("/login")
    def common_login_page():
        return render_template("auth/login.html")

    @app.get("/university/register")
    def university_register_page():
        return redirect("/register?type=institution")

    @app.get("/university/challenges")
    def university_challenges_list():
        user = session.get('user')
        if not user:
            return redirect('/university/login')
        if user.get('role') != 'university':
            return redirect('/university/login')
        return render_template("university/challenges.html")

    @app.get("/university/challenges/<int:assignment_id>")
    def university_challenge_detail(assignment_id):
        user = session.get('user')
        if not user:
            return redirect('/university/login')
        return render_template("university/challenge_detail.html",
                               assignment_id=assignment_id)

    @app.get("/university/projects")
    def university_projects_list():
        user = session.get('user')
        if not user:
            return redirect('/university/login')
        if user.get('role') != 'university':
            return redirect('/university/login')
        return render_template("university/dashboard.html")

    @app.get("/university/profile")
    def university_profile():
        user = session.get('user')
        if not user:
            return redirect('/university/login')
        if user.get('role') != 'university':
            return redirect('/university/login')
        return render_template("hei_profile.html")

    @app.get("/university/projects/<int:project_id>/workspace")
    def university_project_workspace(project_id):
        user = session.get('user')
        if not user:
            return redirect('/university/login')
        if user.get('role') != 'university':
            return redirect('/university/login')
        return render_template("university/project_workspace.html",
                               project_id=project_id)

    # University workspace page
    @app.get("/workspace")
    def university_workspace():
        user = session.get('user')
        if not user:
            return redirect('/university/login')
        if user.get('role') != 'university':
            return redirect('/university/login')
        return render_template("university_workspace.html")

    # Industry dashboard page
    @app.get("/industry")
    def industry_dashboard():
        user = session.get('user')
        if not user:
            return redirect('/login')
        if user.get('role') not in ('industry', 'admin'):
            return redirect('/login')
        return render_template("industry/dashboard.html")

    # Public dashboard page
    @app.get("/dashboard")
    def public_dashboard():
        return render_template("public/dashboard.html")

    # Citizen product pages
    @app.get("/citizen")
    def citizen_dashboard():
        if not session.get('user'):
            return redirect('/login')
        return render_template("citizen/dashboard.html")

    @app.get("/citizen/submit")
    def citizen_submit():
        if not session.get('user'):
            return redirect('/login?next=/citizen/submit')
        return render_template("citizen/submit.html")

    @app.get("/citizen/problems")
    def citizen_problems():
        if not session.get('user'):
            return redirect('/login')
        return render_template("citizen/problems.html")

    @app.get("/citizen/problems/<int:problem_id>")
    def citizen_problem_detail(problem_id):
        if not session.get('user'):
            return redirect('/login')
        return render_template("citizen/problem_detail.html", problem_id=problem_id)

    @app.get("/citizen/problems/<int:problem_id>/verify")
    def citizen_verify_problem(problem_id):
        if not session.get('user'):
            return redirect('/login')
        return render_template("citizen/verify.html", problem_id=problem_id)

    @app.get("/citizen/notifications")
    def citizen_notifications():
        if not session.get('user'):
            return redirect('/login')
        return render_template("citizen/notifications.html")

    @app.get("/citizen/profile")
    def citizen_profile():
        if not session.get('user'):
            return redirect('/login')
        return render_template("citizen/profile.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
