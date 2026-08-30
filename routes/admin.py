from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    session
)

from werkzeug.security import check_password_hash

from database import get_db
from routes.decorators import admin_required


admin_bp = Blueprint(
    "admin",
    __name__
)


# =========================================================
# ADMIN LOGIN
# =========================================================

@admin_bp.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    # Already logged-in admin
    if session.get("role") == "admin":
        return redirect("/admin/dashboard")

    if request.method == "POST":

        admin_id = request.form.get(
            "admin_id",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not admin_id or not password:

            flash(
                "Please enter Admin ID and Password.",
                "danger"
            )

            return redirect("/admin/login")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM admin
            WHERE admin_id=?
        """, (
            admin_id,
        ))

        admin = cur.fetchone()

        conn.close()

        # Admin not found
        if not admin:

            flash(
                "Invalid Admin ID or Password.",
                "danger"
            )

            return redirect("/admin/login")

        # Password check
        try:

            password_valid = check_password_hash(
                admin["password"],
                password
            )

        except Exception:

            password_valid = False

        if not password_valid:

            flash(
                "Invalid Admin ID or Password.",
                "danger"
            )

            return redirect("/admin/login")

        # =====================================================
        # ADMIN LOGIN SUCCESS
        # =====================================================

        session.clear()

        session["admin_id"] = admin["admin_id"]
        session["admin_name"] = admin["fullname"]
        session["role"] = "admin"

        flash(
            "Admin Login Successful.",
            "success"
        )

        return redirect(
            "/admin/dashboard"
        )

    return render_template(
        "admin/login.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@admin_bp.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    conn = get_db()
    cur = conn.cursor()

    # -----------------------------------------------------
    # TOTAL WORKERS
    # -----------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM workers
        WHERE is_deleted=0
    """)

    total_workers = cur.fetchone()["total"]


    # -----------------------------------------------------
    # TOTAL PARTNERS
    # -----------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM partners
        WHERE is_deleted=0
    """)

    total_partners = cur.fetchone()["total"]


    # -----------------------------------------------------
    # TOTAL JOBS
    # -----------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM jobs
    """)

    total_jobs = cur.fetchone()["total"]


    # -----------------------------------------------------
    # TOTAL WITHDRAW REQUESTS
    # -----------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM withdraw_requests
    """)

    total_withdrawals = cur.fetchone()["total"]


    # -----------------------------------------------------
    # TOTAL JOB REQUESTS
    # -----------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM job_requests
    """)

    total_job_requests = cur.fetchone()["total"]


    # -----------------------------------------------------
    # TOTAL NOTIFICATIONS
    # -----------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM notifications
    """)

    total_notifications = cur.fetchone()["total"]


    # -----------------------------------------------------
    # DELETED WORKERS
    # -----------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM workers
        WHERE is_deleted=1
    """)

    deleted_workers = cur.fetchone()["total"]


    # -----------------------------------------------------
    # DELETED PARTNERS
    # -----------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM partners
        WHERE is_deleted=1
    """)

    deleted_partners = cur.fetchone()["total"]


    deleted_accounts = (
        deleted_workers +
        deleted_partners
    )

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_workers=total_workers,
        total_partners=total_partners,
        total_jobs=total_jobs,
        total_withdrawals=total_withdrawals,
        total_job_requests=total_job_requests,
        total_notifications=total_notifications,
        deleted_workers=deleted_workers,
        deleted_partners=deleted_partners,
        deleted_accounts=deleted_accounts
    )


# =========================================================
# ADMIN PARTNERS
# =========================================================

@admin_bp.route("/admin/partners")
@admin_required
def admin_partners():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM partners
        WHERE is_deleted=0
        ORDER BY id DESC
    """)

    partners = cur.fetchall()

    conn.close()

    return render_template(
        "admin/partners.html",
        partners=partners
    )


# =========================================================
# PARTNER DETAILS
# =========================================================

@admin_bp.route(
    "/admin/partner/<int:partner_id>"
)
@admin_required
def admin_partner_details(partner_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM partners
        WHERE id=?
    """, (
        partner_id,
    ))

    partner = cur.fetchone()

    conn.close()

    if not partner:

        flash(
            "Partner not found.",
            "danger"
        )

        return redirect(
            "/admin/partners"
        )

    return render_template(
        "admin/partner_details.html",
        partner=partner
    )


# =========================================================
# SUSPEND PARTNER
# =========================================================

@admin_bp.route(
    "/admin/partner/<int:id>/suspend",
    methods=["POST"]
)
@admin_required
def suspend_partner(id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE partners
        SET status='suspended'
        WHERE id=?
    """, (
        id,
    ))

    conn.commit()
    conn.close()

    flash(
        "Partner Suspended Successfully.",
        "success"
    )

    return redirect(
        f"/admin/partner/{id}"
    )


# =========================================================
# ACTIVATE PARTNER
# =========================================================

@admin_bp.route(
    "/admin/partner/<int:id>/activate",
    methods=["POST"]
)
@admin_required
def activate_partner(id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE partners
        SET status='active'
        WHERE id=?
    """, (
        id,
    ))

    conn.commit()
    conn.close()

    flash(
        "Partner Activated Successfully.",
        "success"
    )

    return redirect(
        f"/admin/partner/{id}"
    )


# =========================================================
# ADMIN WORKERS
# =========================================================

@admin_bp.route("/admin/workers")
@admin_required
def admin_workers():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM workers
        WHERE is_deleted=0
        ORDER BY id DESC
    """)

    workers = cur.fetchall()

    conn.close()

    return render_template(
        "admin/workers.html",
        workers=workers
    )


# =========================================================
# WORKER DETAILS
# =========================================================

@admin_bp.route(
    "/admin/worker/<int:worker_id>"
)
@admin_required
def admin_worker_details(worker_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM workers
        WHERE id=?
    """, (
        worker_id,
    ))

    worker = cur.fetchone()

    conn.close()

    if not worker:

        flash(
            "Worker not found.",
            "danger"
        )

        return redirect(
            "/admin/workers"
        )

    return render_template(
        "admin/worker_details.html",
        worker=worker
    )


# =========================================================
# SUSPEND WORKER
# =========================================================

@admin_bp.route(
    "/admin/worker/<int:worker_id>/suspend",
    methods=["POST"]
)
@admin_required
def suspend_worker(worker_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE workers
        SET status=?
        WHERE id=?
    """, (
        "suspended",
        worker_id
    ))

    conn.commit()
    conn.close()

    flash(
        "Worker account suspended successfully.",
        "success"
    )

    return redirect(
        f"/admin/worker/{worker_id}"
    )


# =========================================================
# ACTIVATE WORKER
# =========================================================

@admin_bp.route(
    "/admin/worker/<int:worker_id>/activate",
    methods=["POST"]
)
@admin_required
def activate_worker(worker_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE workers
        SET status=?
        WHERE id=?
    """, (
        "active",
        worker_id
    ))

    conn.commit()
    conn.close()

    flash(
        "Worker account activated successfully.",
        "success"
    )

    return redirect(
        f"/admin/worker/{worker_id}"
    )


# =========================================================
# DELETE WORKER
# =========================================================

@admin_bp.route(
    "/admin/worker/delete/<worker_id>",
    methods=["POST"]
)
@admin_required
def delete_worker(worker_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE workers
        SET is_deleted=1
        WHERE worker_id=?
    """, (
        worker_id,
    ))

    conn.commit()
    conn.close()

    flash(
        "Worker moved to Deleted Accounts.",
        "success"
    )

    return redirect(
        "/admin/workers"
    )


# =========================================================
# DELETE PARTNER
# =========================================================

@admin_bp.route(
    "/admin/partner/delete/<partner_id>",
    methods=["POST"]
)
@admin_required
def delete_partner(partner_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE partners
        SET is_deleted=1
        WHERE partner_id=?
    """, (
        partner_id,
    ))

    conn.commit()
    conn.close()

    flash(
        "Partner moved to Deleted Accounts.",
        "success"
    )

    return redirect(
        "/admin/partners"
    )


# =========================================================
# DELETED ACCOUNTS
# =========================================================

@admin_bp.route("/admin/deleted-accounts")
@admin_required
def deleted_accounts():

    conn = get_db()
    cur = conn.cursor()

    # -----------------------------------------------------
    # DELETED WORKERS
    # -----------------------------------------------------

    cur.execute("""
        SELECT *
        FROM workers
        WHERE is_deleted=1
        ORDER BY id DESC
    """)

    deleted_workers = cur.fetchall()


    # -----------------------------------------------------
    # DELETED PARTNERS
    # -----------------------------------------------------

    cur.execute("""
        SELECT *
        FROM partners
        WHERE is_deleted=1
        ORDER BY id DESC
    """)

    deleted_partners = cur.fetchall()

    conn.close()

    return render_template(
        "admin/deleted_accounts.html",
        deleted_workers=deleted_workers,
        deleted_partners=deleted_partners
    )


# =========================================================
# RESTORE WORKER
# =========================================================

@admin_bp.route(
    "/admin/worker/<int:worker_id>/restore",
    methods=["POST"]
)
@admin_required
def restore_worker(worker_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE workers
        SET is_deleted=0
        WHERE id=?
    """, (
        worker_id,
    ))

    conn.commit()
    conn.close()

    flash(
        "Worker account restored successfully.",
        "success"
    )

    return redirect(
        "/admin/deleted-accounts"
    )


# =========================================================
# RESTORE PARTNER
# =========================================================

@admin_bp.route(
    "/admin/partner/<int:partner_id>/restore",
    methods=["POST"]
)
@admin_required
def restore_partner(partner_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE partners
        SET is_deleted=0
        WHERE id=?
    """, (
        partner_id,
    ))

    conn.commit()
    conn.close()

    flash(
        "Partner account restored successfully.",
        "success"
    )

    return redirect(
        "/admin/deleted-accounts"
    )


# =========================================================
# PERMANENT DELETE WORKER
# =========================================================

@admin_bp.route(
    "/admin/worker/<int:worker_id>/permanent-delete",
    methods=["POST"]
)
@admin_required
def permanent_delete_worker(worker_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM workers
        WHERE id=?
        AND is_deleted=1
    """, (
        worker_id,
    ))

    conn.commit()
    conn.close()

    flash(
        "Worker permanently deleted.",
        "success"
    )

    return redirect(
        "/admin/deleted-accounts"
    )


# =========================================================
# PERMANENT DELETE PARTNER
# =========================================================

@admin_bp.route(
    "/admin/partner/<int:partner_id>/permanent-delete",
    methods=["POST"]
)
@admin_required
def permanent_delete_partner(partner_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM partners
        WHERE id=?
        AND is_deleted=1
    """, (
        partner_id,
    ))

    conn.commit()
    conn.close()

    flash(
        "Partner permanently deleted.",
        "success"
    )

    return redirect(
        "/admin/deleted-accounts"
    )


# =========================================================
# ADMIN JOBS
# =========================================================

@admin_bp.route("/admin/jobs")
@admin_required
def admin_jobs():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            j.*,

            p.fullname AS partner_name,
            p.partner_id AS partner_id,

            w.fullname AS worker_name,
            w.worker_id AS worker_id

        FROM jobs j

        LEFT JOIN partners p
            ON j.partner_id = p.id

        LEFT JOIN workers w
            ON j.worker_id = w.id

        ORDER BY j.id DESC
    """)

    jobs = cur.fetchall()

    conn.close()

    return render_template(
        "admin/jobs.html",
        jobs=jobs
    )


# =========================================================
# JOB DETAILS
# =========================================================

@admin_bp.route(
    "/admin/job/<int:job_id>"
)
@admin_required
def admin_job_details(job_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM jobs
        WHERE id=?
    """, (
        job_id,
    ))

    job = cur.fetchone()

    conn.close()

    if not job:

        flash(
            "Job not found.",
            "danger"
        )

        return redirect(
            "/admin/jobs"
        )

    return render_template(
        "admin/job_details.html",
        job=job
    )


# =========================================================
# ADMIN WALLET
# =========================================================

@admin_bp.route("/admin/wallet")
@admin_required
def admin_wallet():

    conn = get_db()
    cur = conn.cursor()

    # -----------------------------------------------------
    # WORKER WALLET
    # -----------------------------------------------------

    cur.execute("""
        SELECT COALESCE(
            SUM(wallet),
            0
        ) AS total
        FROM workers
        WHERE is_deleted=0
    """)

    worker_wallet = (
        cur.fetchone()["total"] or 0
    )


    # -----------------------------------------------------
    # PARTNER WALLET
    # -----------------------------------------------------

    cur.execute("""
        SELECT COALESCE(
            SUM(wallet),
            0
        ) AS total
        FROM partners
        WHERE is_deleted=0
    """)

    partner_wallet = (
        cur.fetchone()["total"] or 0
    )


    # -----------------------------------------------------
    # TOTAL WALLET
    # -----------------------------------------------------

    total_wallet = (
        worker_wallet +
        partner_wallet
    )


    # -----------------------------------------------------
    # TOTAL WITHDRAWN
    # -----------------------------------------------------

    cur.execute("""
        SELECT COALESCE(
            SUM(amount),
            0
        ) AS total
        FROM withdraw_requests
        WHERE status='completed'
    """)

    total_withdrawn = (
        cur.fetchone()["total"] or 0
    )


    # -----------------------------------------------------
    # WALLET TRANSACTIONS
    # -----------------------------------------------------

    transactions = []

    try:

        cur.execute("""
            SELECT
                id,
                fullname,
                user_id,
                user_type,
                transaction_type,
                amount,
                balance,
                status,
                created_at
            FROM wallet_transactions
            ORDER BY id DESC
        """)

        transactions = cur.fetchall()

    except Exception as e:

        print(
            "Wallet transaction table error:",
            e
        )

        transactions = []


    conn.close()

    return render_template(
        "admin/wallet.html",
        total_wallet=total_wallet,
        worker_wallet=worker_wallet,
        partner_wallet=partner_wallet,
        total_withdrawn=total_withdrawn,
        transactions=transactions
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@admin_bp.route("/admin/logout")
def admin_logout():

    session.clear()

    flash(
        "Admin logged out successfully.",
        "success"
    )

    return redirect(
        "/admin/login"
    )
