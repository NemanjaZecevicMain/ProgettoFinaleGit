from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models.connection import db


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)

    def set_password(self, password: str):
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)


class VMRequest(db.Model):
    __tablename__ = "vm_request"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    vm_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="PENDING", nullable=False)

    vmid = db.Column(db.Integer, nullable=True)
    hostname = db.Column(db.String(120), nullable=True)

    initial_user = db.Column(db.String(80), nullable=True)
    initial_password = db.Column(db.String(100), nullable=True)

    ip_address = db.Column(db.String(50), nullable=True)

    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("requests", lazy=True))
