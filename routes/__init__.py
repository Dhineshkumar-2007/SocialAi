from flask import Blueprint

# Import all route blueprints to register them
from routes.problems import problems_bp
from routes.universities import universities_bp
from routes.projects import projects_bp
from routes.assignments import assignments_bp
from routes.dashboard import dashboard_bp
from routes.notifications import notifications_bp
