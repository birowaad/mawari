from flask import Blueprint

content_bp = Blueprint('content', __name__, url_prefix='/content')

@content_bp.route('/')
def content_home():
    return "Content Home Page"

@content_bp.route('/articles')
def articles():
    return "Articles List"
