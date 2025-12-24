import os
from flask import Flask
from dotenv import load_dotenv

from models.connection import db, login_manager
from models.model import User, VMRequest
from blueprints.auth import auth_bp
from sqlalchemy import select
from datetime import timedelta


load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

# Directory instance usata per il database SQLite
os.makedirs(INSTANCE_DIR, exist_ok=True)
DB_PATH = os.path.join(INSTANCE_DIR, "vmportal.sqlite")


app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db.init_app(app)
login_manager.init_app(app)

app.register_blueprint(auth_bp)


# Funzione richiesta da Flask-Login
# Serve a ricaricare l’utente dalla sessione
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Contesto applicativo iniziale
# - crea le tabelle
# - crea l’utente admin se non esiste
with app.app_context():
    db.create_all()

    # Creazione automatica account admin
    # (necessario per approvare le richieste VM)
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()


# Avvio applicazione in modalità debug
if __name__ == "__main__":
    app.run(debug=True)
