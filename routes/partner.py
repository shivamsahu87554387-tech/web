from flask import (
    Blueprint,
    render_template,
    session,
    request,
    redirect,
    flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from werkzeug.utils import secure_filename
from utils.email_sender import send_otp
from routes.decorators import partner_required

import os
import random

from datetime import (
    datetime,
    timedelta
)

partner_bp = Blueprint(
    "partner",
    __name__
)

UPLOAD_FOLDER = "static/uploads"


# ======================================
# Partner Home
# ======================================

@partner_bp.route("/partner/home")
@partner_required
def partner_home():

    conn = get_db()
    cur = conn.cursor()

    # Total Workers of this Partner
    cur.execute("""
    SELECT COUNT(*)
    FROM partner_workers
    WHERE partner_id=?
    """, (session["user_id"],))

    total_workers = cur.fetchone()[0]

    # Total Jobs of this Partner
    cur.execute("""
    SELECT COUNT(*)
    FROM jobs
    WHERE partner_id=?
    """, (session["user_id"],))

    total_jobs = cur.fetchone()[0]

    # Pending Jobs of this Partner
    cur.execute("""
    SELECT COUNT(*)
    FROM jobs
    WHERE partner_id=?
    AND job_status='Pending'
    """, (session["user_id"],))

    pending_jobs = cur.fetchone()[0]

    # Notifications of this Partner
    cur.execute("""
    SELECT COUNT(*)
    FROM notifications
    WHERE user_type='partner'
    AND user_id=?
    AND is_read=0
    """, (session["user_id"],))

    total_notifications = cur.fetchone()[0]

    # Wallet
    cur.execute("""
    SELECT wallet
    FROM partners
    WHERE partner_id=?
    """, (session["user_id"],))

    partner = cur.fetchone()

    wallet = partner["wallet"] if partner else 0

    conn.close()

    return render_template(
        "partner/home.html",
        total_workers=total_workers,
        total_jobs=total_jobs,
        pending_jobs=pending_jobs,
        total_notifications=total_notifications,
        wallet=wallet
    )

# ======================================
# Workers
# ======================================

@partner_bp.route("/partner/workers")
@partner_required
def workers():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            w.worker_id,
            w.fullname,
            w.mobile,
            w.status
        FROM partner_workers pw
        JOIN workers w
        ON pw.worker_id=w.worker_id
        WHERE pw.partner_id=?
        ORDER BY pw.id DESC
    """,(session["user_id"],))

    workers=cur.fetchall()

    conn.close()

    return render_template(
        "partner/workers.html",
        workers=workers
    )


# ======================================
# Worker Profile
# ======================================

@partner_bp.route("/partner/worker/<worker_id>")
@partner_required
def worker_profile(worker_id):

    conn=get_db()
    cur=conn.cursor()

    cur.execute("""
        SELECT w.*
        FROM workers w
        JOIN partner_workers pw
        ON w.worker_id=pw.worker_id
        WHERE
        pw.partner_id=?
        AND
        w.worker_id=?
    """,(
        session["user_id"],
        worker_id
    ))

    worker=cur.fetchone()

    conn.close()

    if not worker:

        flash(
            "Worker not found.",
            "danger"
        )

        return redirect(
            "/partner/workers"
        )

    return render_template(
        "partner/worker_profile.html",
        worker=worker
    )


# ======================================
# Jobs
# ======================================

@partner_bp.route("/partner/jobs")
@partner_required
def jobs():

    conn=get_db()
    cur=conn.cursor()

    cur.execute("""
        SELECT *
        FROM jobs
        ORDER BY id DESC
    """)

    jobs=cur.fetchall()

    conn.close()

    return render_template(
        "partner/jobs.html",
        jobs=jobs
    )


@partner_bp.route("/partner/notifications", methods=["GET", "POST"])
@partner_required
def notifications():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        app_notification = 1 if request.form.get("app_notification") else 0
        email_notification = 1 if request.form.get("email_notification") else 0
        job_notification = 1 if request.form.get("job_notification") else 0
        withdraw_notification = 1 if request.form.get("withdraw_notification") else 0
        promo_notification = 1 if request.form.get("promo_notification") else 0

        cur.execute("""
        UPDATE partners
        SET
            app_notification=?,
            email_notification=?,
            job_notification=?,
            withdraw_notification=?,
            promo_notification=?
        WHERE partner_id=?
        """,(
            app_notification,
            email_notification,
            job_notification,
            withdraw_notification,
            promo_notification,
            session["user_id"]
        ))

        conn.commit()

        flash("Notification settings updated.","success")

        return redirect("/partner/notifications")

    cur.execute("""
    SELECT *
    FROM partners
    WHERE partner_id=?
    """,(session["user_id"],))

    partner = cur.fetchone()

    conn.close()

    return render_template(
        "partner/notifications.html",
        partner=partner
    )

# ======================================
# Profile
# ======================================

@partner_bp.route("/partner/profile")
@partner_required
def profile():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM partners
        WHERE partner_id=?
    """,(session["user_id"],))

    partner = cur.fetchone()

    conn.close()

    return render_template(
        "partner/profile.html",
        partner=partner
    )


# ======================================
# Withdraw
# ======================================

@partner_bp.route("/partner/withdraw", methods=["GET","POST"])
@partner_required
def withdraw():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM partners
        WHERE partner_id=?
    """,(session["user_id"],))

    partner = cur.fetchone()

    if (
        not partner["bank_name"] or
        not partner["account_holder"] or
        not partner["account_number"] or
        not partner["ifsc"]
    ):

        flash(
            "Please add your bank details first.",
            "danger"
        )

        conn.close()

        return redirect("/partner/bank")

    if request.method == "POST":

        amount = float(request.form["amount"])
        wallet = float(partner["wallet"] or 0)

        if amount <= 0:

            flash(
                "Enter valid amount.",
                "danger"
            )

            conn.close()

            return redirect("/partner/withdraw")

        if amount > wallet:

            flash(
                "Insufficient wallet balance.",
                "danger"
            )

            conn.close()

            return redirect("/partner/withdraw")

        cur.execute("""
            INSERT INTO withdraw_requests
            (
                partner_id,
                amount,
                bank_name,
                account_number,
                ifsc,
                status
            )
            VALUES(?,?,?,?,?,?)
        """,(
            session["user_id"],
            amount,
            partner["bank_name"],
            partner["account_number"],
            partner["ifsc"],
            "Pending"
        ))

        new_wallet = wallet - amount

        cur.execute("""
            UPDATE partners
            SET wallet=?
            WHERE partner_id=?
        """,(
            new_wallet,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        flash(
            "Withdraw request submitted successfully.",
            "success"
        )

        return redirect("/partner/wallet")

    conn.close()

    return render_template(
        "partner/withdraw.html",
        partner=partner
    )


# ======================================
# Wallet
# ======================================

@partner_bp.route("/partner/wallet")
@partner_required
def wallet():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM partners
        WHERE partner_id=?
    """,(session["user_id"],))

    partner = cur.fetchone()

    cur.execute("""
        SELECT *
        FROM withdraw_requests
        WHERE partner_id=?
        ORDER BY id DESC
    """,(session["user_id"],))

    withdraws = cur.fetchall()

    conn.close()

    return render_template(
        "partner/wallet.html",
        partner=partner,
        withdraws=withdraws
    )

# ======================================
# Edit Profile
# ======================================

@partner_bp.route("/partner/edit-profile", methods=["GET", "POST"])
@partner_required
def edit_profile():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM partners
        WHERE partner_id=?
    """,(session["user_id"],))

    partner = cur.fetchone()

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        address = request.form["address"]
        city = request.form["city"]
        state = request.form["state"]
        pincode = request.form["pincode"]

        photo = request.files.get("profile_photo")
        photo_name = partner["profile_photo"]

        if photo and photo.filename != "":

            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            filename = secure_filename(photo.filename)

            photo.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )
            )

            photo_name = filename

        cur.execute("""
            UPDATE partners
            SET
                fullname=?,
                email=?,
                mobile=?,
                address=?,
                city=?,
                state=?,
                pincode=?,
                profile_photo=?
            WHERE partner_id=?
        """,(
            fullname,
            email,
            mobile,
            address,
            city,
            state,
            pincode,
            photo_name,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        flash(
            "Profile Updated Successfully.",
            "success"
        )

        return redirect("/partner/profile")

    conn.close()

    return render_template(
        "partner/edit_profile.html",
        partner=partner
    )


# ======================================
# Settings
# ======================================

@partner_bp.route("/partner/settings")
@partner_required
def settings():

    return render_template(
        "partner/settings.html"
    )


# ======================================
# Bank
# ======================================

@partner_bp.route("/partner/bank", methods=["GET","POST"])
@partner_required
def bank():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM partners
        WHERE partner_id=?
    """,(session["user_id"],))

    partner = cur.fetchone()

    if request.method=="POST" and not partner["bank_name"]:

        cur.execute("""
            UPDATE partners
            SET
                bank_name=?,
                account_holder=?,
                account_number=?,
                ifsc=?
            WHERE partner_id=?
        """,(
            request.form["bank_name"],
            request.form["account_holder"],
            request.form["account_number"],
            request.form["ifsc"],
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        flash(
            "Bank Details Saved",
            "success"
        )

        return redirect("/partner/bank")

    conn.close()

    return render_template(
        "partner/bank.html",
        partner=partner
    )


# ======================================
# Change Bank
# ======================================

@partner_bp.route("/partner/change-bank", methods=["POST"])
@partner_required
def change_bank():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT email
        FROM partners
        WHERE partner_id=?
    """,(session["user_id"],))

    partner = cur.fetchone()

    otp = str(random.randint(100000,999999))

    session["bank_otp"] = otp

    session["bank_expiry"] = (
        datetime.now() + timedelta(minutes=5)
    ).strftime("%Y-%m-%d %H:%M:%S")

    session["new_bank"] = {

        "bank_name":request.form["bank_name"],
        "account_holder":request.form["account_holder"],
        "account_number":request.form["account_number"],
        "ifsc":request.form["ifsc"]

    }

    send_otp(
        partner["email"],
        otp
    )

    conn.close()

    flash(
        "OTP sent to your email.",
        "success"
    )

    return redirect("/partner/verify-bank-otp")

# ======================================
# Verify Bank OTP
# ======================================

@partner_bp.route("/partner/verify-bank-otp", methods=["GET","POST"])
@partner_required
def verify_bank_otp():

    if request.method == "POST":

        user_otp = request.form["otp"]

        if "bank_otp" not in session:

            flash("OTP Expired","danger")
            return redirect("/partner/bank")

        expiry = datetime.strptime(
            session["bank_expiry"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() > expiry:

            session.pop("bank_otp", None)
            session.pop("bank_expiry", None)
            session.pop("new_bank", None)

            flash("OTP Expired","danger")
            return redirect("/partner/bank")

        if user_otp != session["bank_otp"]:

            flash("Invalid OTP","danger")
            return redirect("/partner/verify-bank-otp")

        bank = session["new_bank"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            UPDATE partners
            SET
                bank_name=?,
                account_holder=?,
                account_number=?,
                ifsc=?
            WHERE partner_id=?
        """,(
            bank["bank_name"],
            bank["account_holder"],
            bank["account_number"],
            bank["ifsc"],
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        session.pop("bank_otp", None)
        session.pop("bank_expiry", None)
        session.pop("new_bank", None)

        flash(
            "Bank Details Updated Successfully",
            "success"
        )

        return redirect("/partner/bank")

    return render_template(
        "partner/verify_bank_otp.html"
    )


# ======================================
# Resend Bank OTP
# ======================================

@partner_bp.route("/partner/resend-bank-otp")
@partner_required
def resend_bank_otp():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT email
        FROM partners
        WHERE partner_id=?
    """,(session["user_id"],))

    partner = cur.fetchone()

    conn.close()

    otp = str(random.randint(100000,999999))

    session["bank_otp"] = otp

    session["bank_expiry"] = (
        datetime.now() + timedelta(minutes=5)
    ).strftime("%Y-%m-%d %H:%M:%S")

    send_otp(
        partner["email"],
        otp
    )

    flash(
        "New OTP Sent Successfully.",
        "success"
    )

    return redirect("/partner/verify-bank-otp")


# ======================================
# Help
# ======================================

@partner_bp.route("/partner/help")
@partner_required
def help():

    return render_template("partner/help.html")


# ======================================
# FAQ
# ======================================

@partner_bp.route("/partner/faq")
@partner_required
def faq():

    return render_template("partner/faq.html")


# ======================================
# Privacy
# ======================================

@partner_bp.route("/partner/privacy")
@partner_required
def privacy():

    return render_template("partner/privacy.html")


# ======================================
# Terms
# ======================================

@partner_bp.route("/partner/terms")
@partner_required
def terms():

    return render_template("partner/terms.html")


# ======================================
# About Workmitra
# ======================================

@partner_bp.route("/partner/about")
@partner_required
def about():

    return render_template("partner/about.html")



# ======================================
# Language
# ======================================

@partner_bp.route(
    "/partner/language",
    methods=["GET", "POST"]
)
@partner_required
def language():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        language = request.form["language"]

        cur.execute("""
        UPDATE partners
        SET language=?
        WHERE partner_id=?
        """, (
            language,
            session["user_id"]
        ))

        conn.commit()

        flash(
            "Language Updated Successfully.",
            "success"
        )

        conn.close()

        return redirect("/partner/language")

    cur.execute("""
    SELECT language
    FROM partners
    WHERE partner_id=?
    """, (session["user_id"],))

    partner = cur.fetchone()

    conn.close()

    return render_template(
        "partner/language.html",
        partner=partner
    )


# ======================================
# Change Password
# ======================================

@partner_bp.route("/partner/change-password", methods=["GET", "POST"])
@partner_required
def change_password():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM partners
    WHERE partner_id=?
    """, (session["user_id"],))

    partner = cur.fetchone()

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        # Current Password Check
        if not check_password_hash(
            partner["password"],
            current_password
        ):
            flash("Current password is incorrect.", "danger")
            conn.close()
            return redirect("/partner/change-password")

        # Confirm Password Check
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            conn.close()
            return redirect("/partner/change-password")

        # OTP Generate
        otp = str(random.randint(100000, 999999))

        session["password_otp"] = otp

        session["password_expiry"] = (
            datetime.now() + timedelta(minutes=5)
        ).strftime("%Y-%m-%d %H:%M:%S")

        session["new_password"] = generate_password_hash(new_password)

        send_otp(
            partner["email"],
            otp
        )

        conn.close()

        flash("OTP sent to your email.", "success")

        return redirect("/partner/verify-password-otp")

    conn.close()

    return render_template(
        "partner/change_password.html"
    )
# ======================================
# Verify Change Password OTP
# ======================================

@partner_bp.route("/partner/verify-password-otp", methods=["GET", "POST"])
@partner_required
def verify_password_otp():

    if request.method == "POST":

        user_otp = request.form["otp"]

        if "password_otp" not in session:
            flash("OTP Expired", "danger")
            return redirect("/partner/change-password")

        expiry = datetime.strptime(
            session["password_expiry"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() > expiry:

            session.pop("password_otp", None)
            session.pop("password_expiry", None)
            session.pop("new_password", None)

            flash("OTP Expired", "danger")
            return redirect("/partner/change-password")

        if user_otp != session["password_otp"]:

            flash("Invalid OTP", "danger")
            return redirect("/partner/verify-password-otp")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        UPDATE partners
        SET password=?
        WHERE partner_id=?
        """, (
            session["new_password"],
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        session.pop("password_otp", None)
        session.pop("password_expiry", None)
        session.pop("new_password", None)

        flash(
            "Password Changed Successfully.",
            "success"
        )

        return redirect("/partner/verify-password-otp")

    return render_template(
        "partner/verify_password_otp.html"
    )

# ======================================
# Resend Change Password OTP
# ======================================

@partner_bp.route("/partner/resend-password-otp")
@partner_required
def resend_password_otp():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT email
    FROM partners
    WHERE partner_id=?
    """, (session["user_id"],))

    partner = cur.fetchone()

    conn.close()

    otp = str(random.randint(100000, 999999))

    session["password_otp"] = otp

    session["password_expiry"] = (
        datetime.now() + timedelta(minutes=5)
    ).strftime("%Y-%m-%d %H:%M:%S")

    send_otp(
        partner["email"],
        otp
    )

    flash(
        "New OTP Sent Successfully.",
        "success"
    )

    return redirect("/partner/verify-password-otp")

# ======================================
# Rate App
# ======================================

@partner_bp.route(
    "/partner/rate-app",
    methods=["GET", "POST"]
)
@partner_required
def rate_app():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        rating = request.form["rating"]
        feedback = request.form.get("feedback", "").strip()

        cur.execute("""
        INSERT INTO app_ratings(
            partner_id,
            rating,
            feedback
        )
        VALUES(?,?,?)
        """, (
            session["user_id"],
            rating,
            feedback
        ))

        conn.commit()
        conn.close()

        flash(
            "Thank you for your feedback ❤️",
            "success"
        )

        return redirect("/partner/rate-app")

    conn.close()

    return render_template(
        "partner/rate_app.html"
    )

# ======================================
# Check for Update
# ======================================

@partner_bp.route("/partner/check-update")
@partner_required
def check_update():

    current_version = "1.0.0"
    latest_version = "1.0.0"

    if current_version == latest_version:
        update_available = False
    else:
        update_available = True

    return render_template(
        "partner/check_update.html",
        current_version=current_version,
        latest_version=latest_version,
        update_available=update_available
    )


# ======================================
# App Version
# ======================================

@partner_bp.route("/partner/app-version")
@partner_required
def app_version():

    version = "1.0.0"

    return render_template(
        "partner/app_version.html",
        version=version
    )
