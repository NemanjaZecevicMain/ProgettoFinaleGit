import os
import time
import threading
import secrets
import string

from flask import Blueprint, render_template, request, redirect, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user

from models.connection import db
from models.model import User, VMRequest
from proxmox_client import ProxmoxClient
from proxmox_specs import VM_TYPES
from datetime import timedelta

# Blueprint che contiene tutta la logica di autenticazione,
# richieste VM e pannello admin
auth_bp = Blueprint("auth", __name__)


# -------------------------
# UTIL
# -------------------------

# Genera una password casuale sicura
# Usata per assegnare automaticamente la password root alla VM
def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# Job asincrono che completa la creazione della VM
# Viene eseguito in un thread separato per non bloccare la web app
def finalize_vm_job(app, req_id, vmid, vm_type):
    # Serve per poter usare SQLAlchemy fuori da una request HTTP
    with app.app_context():
        # Attesa per evitare conflitti/lock su Proxmox
        time.sleep(60)

        px = ProxmoxClient()
        specs = VM_TYPES[vm_type]
        password = generate_password()

        # Configura CPU, RAM e disco e avvia il container
        px.configure_and_start(
            vmid,
            specs["cores"],
            specs["memory"],
            specs["disk_gb"]
        )

        # Imposta la password root nel container
        px.set_root_password(vmid, password)

        # Recupera l'indirizzo IP del container
        ip = px.get_container_ip(vmid)

        # Aggiorna lo stato della richiesta nel database
        req = VMRequest.query.get(req_id)
        if not req:
            return

        req.status = "READY"
        req.initial_user = "root"
        req.initial_password = password
        req.ip_address = ip
        req.notes = "VM pronta. Accedi via SSH."
        db.session.commit()


# -------------------------
# AUTH
# -------------------------

# Login utente
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.check_password(request.form["password"]):
            login_user(user)
            return redirect("/dashboard")
        flash("Credenziali errate")
    return render_template("auth/login.html")


# Registrazione nuovo utente
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if User.query.filter_by(username=request.form["username"]).first():
            flash("Utente già esistente")
            return redirect("/signup")

        user = User(username=request.form["username"])
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("auth/signup.html")


# Logout utente
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# -------------------------
# USER
# -------------------------

# Dashboard principale
@auth_bp.route("/dashboard")
@login_required
def dashboard():
    # se admin → pagina admin
    if current_user.role == "admin":
        return redirect("/admin/requests")

    # se utente normale → dashboard utente
    return render_template("dashboard.html")



# Creazione richiesta VM (bronze / silver / gold)
@auth_bp.route("/request", methods=["GET", "POST"])
@login_required
def request_vm():
    if request.method == "POST":
        req = VMRequest(
            user_id=current_user.id,
            vm_type=request.form["vm_type"],
            status="PENDING"
        )
        db.session.add(req)
        db.session.commit()
        return redirect("/dashboard")

    return render_template("vm/request.html")


# Visualizza le richieste dell'utente loggato
@auth_bp.route("/my-requests")
@login_required
def my_requests():
    reqs = (
        VMRequest.query
        .filter_by(user_id=current_user.id)
        .order_by(VMRequest.created_at.desc())
        .all()
    )

    return render_template("vm/my_requests.html", requests=reqs)


# -------------------------
# ADMIN
# -------------------------

# Lista di tutte le richieste (solo admin)
@auth_bp.route("/admin/requests")
@login_required
def admin_requests():
    if current_user.role != "admin":
        return "Forbidden", 403

    reqs = VMRequest.query.order_by(VMRequest.created_at.desc()).all()
    return render_template("vm/admin_list.html", requests=reqs)


# Azioni admin: approva o rifiuta richiesta
@auth_bp.route("/admin/requests/<int:req_id>/<action>")
@login_required
def admin_action(req_id, action):
    if current_user.role != "admin":
        return "Forbidden", 403

    req = VMRequest.query.get_or_404(req_id)

    if action == "approve":
        try:
            px = ProxmoxClient()
            vmid = px.get_next_vmid()
            hostname = f"ct-{req.vm_type}-{req.id}"

            # Clona il template LXC su Proxmox
            px.clone_container(
                int(os.getenv("PROXMOX_LXC_TEMPLATE_ID")),
                vmid,
                hostname
            )

            req.status = "CREATED"
            req.vmid = vmid
            req.hostname = hostname
            req.notes = "VM clonata. Configurazione in corso…"
            db.session.commit()

            # Avvia il job asincrono di configurazione
            threading.Thread(
                target=finalize_vm_job,
                args=(current_app._get_current_object(), req.id, vmid, req.vm_type),
                daemon=True
            ).start()

        except Exception as e:
            req.status = "ERROR"
            req.notes = str(e)
            db.session.commit()

    elif action == "reject":
        req.status = "REJECTED"
        db.session.commit()

    return redirect("/admin/requests")
