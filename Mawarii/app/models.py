from . import db

# ------------------------------
# User Model
# ------------------------------
class User(db.Model):
    __tablename__ = 'users'  # optional, makes table name explicit

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"
