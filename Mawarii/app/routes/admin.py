from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin_home():
    return "Admin Home Page"

@admin_bp.route('/dashboard')
def admin_dashboard():
    return "Admin Dashboard"
