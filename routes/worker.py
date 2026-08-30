from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
import threading
import random
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
from utils.email_sender import send_otp
from database import get_db


worker_bp = Blueprint(
    "worker",
    __name__
)


UPLOAD_FOLDER = "static/uploads"


# ======================================
# Worker Dashboard
# ======================================

@worker_bp.route("/worker/home")
def worker_home():

    return render_template(
        "worker/home.html"
    )


# ======================================
# My Jobs
# ======================================

@worker_bp.route("/worker/jobs")
def worker_jobs():

    return render_template(
        "worker/jobs.html"
    )


# ======================================
# Job Details
# ======================================

@worker_bp.route("/worker/job/<job_id>")
def job_details(job_id):

    return render_template(
        "worker/job_details.html",
        job_id=job_id
    )


# ======================================
# Wallet
# ======================================

@worker_bp.route("/worker/wallet")
def wallet():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        worker_id,
        fullname
    FROM workers
    WHERE worker_id=?
    """, (session["user_id"],))

    worker = cur.fetchone()

    conn.close()

    return render_template(
        "worker/wallet.html",
        worker=worker,
        total_earned=0,
        pending_payment=0,
        paid_amount=0,
        transactions=[]
    )


# ======================================
# Notifications
# ======================================

@worker_bp.route("/worker/notifications", methods=["GET", "POST"])
def notifications():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        app_notification = (
            1 if request.form.get("app_notification") else 0
        )

        email_notification = (
            1 if request.form.get("email_notification") else 0
        )

        job_notification = (
            1 if request.form.get("job_notification") else 0
        )

        payment_notification = (
            1 if request.form.get("payment_notification") else 0
        )

        promo_notification = (
            1 if request.form.get("promo_notification") else 0
        )

        cur.execute("""
        UPDATE workers
        SET
            app_notification=?,
            email_notification=?,
            job_notification=?,
            payment_notification=?,
            promo_notification=?
        WHERE worker_id=?
        """, (
            app_notification,
            email_notification,
            job_notification,
            payment_notification,
            promo_notification,
            session["user_id"]
        ))

        conn.commit()

        flash(
            "Notification Settings Updated Successfully.",
            "success"
        )

    cur.execute("""
    SELECT *
    FROM workers
    WHERE worker_id=?
    """, (
        session["user_id"],
    ))

    worker = cur.fetchone()

    conn.close()

    return render_template(
        "worker/notifications.html",
        worker=worker
    )


# ======================================
# Profile
# ======================================

@worker_bp.route("/worker/profile")
def profile():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM workers
    WHERE worker_id=?
    """, (
        session["user_id"],
    ))

    worker = cur.fetchone()

    conn.close()

    return render_template(
        "worker/profile.html",
        worker=worker
    )


# ======================================
# Edit Profile
# ======================================

@worker_bp.route("/worker/edit-profile", methods=["GET", "POST"])
def edit_profile():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM workers
        WHERE worker_id=?
    """, (
        session["user_id"],
    ))

    worker = cur.fetchone()

    if request.method == "POST":

        # =========================
        # BASIC DETAILS
        # =========================

        fullname = request.form["fullname"]

        address = request.form["address"]

        city = request.form["city"]

        state = request.form["state"]

        pincode = request.form["pincode"]

        skills = ", ".join(request.form.getlist("skills"))

        experience = request.form.get("experience", "").strip()


        # =========================
        # LIVE LOCATION
        # =========================

        latitude = request.form.get("latitude")

        longitude = request.form.get("longitude")


        # =========================
        # VALIDATE LOCATION
        # =========================

        if latitude:

            try:

                latitude = float(latitude)

                if latitude < -90 or latitude > 90:

                    latitude = None

            except (ValueError, TypeError):

                latitude = None


        if longitude:

            try:

                longitude = float(longitude)

                if longitude < -180 or longitude > 180:

                    longitude = None

            except (ValueError, TypeError):

                longitude = None


        # =========================
        # PROFILE PHOTO
        # =========================

        photo = request.files.get(
            "profile_photo"
        )

        photo_name = worker["profile_photo"]


        if photo and photo.filename != "":

            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True
            )

            filename = secure_filename(
                photo.filename
            )

            photo.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )
            )

            photo_name = filename


        # =========================
        # UPDATE WORKER
        # =========================

        cur.execute("""
            UPDATE workers
            SET
                fullname=?,
                address=?,
                city=?,
                state=?,
                pincode=?,
                skills=?,
                experience=?,
                profile_photo=?,
                latitude=?,
                longitude=?
            WHERE worker_id=?
        """, (
            fullname,
            address,
            city,
            state,
            pincode,
            skills,
            experience,
            photo_name,
            latitude,
            longitude,
            session["user_id"]
        ))


        conn.commit()

        conn.close()


        flash(
            "Profile Updated Successfully.",
            "success"
        )

        return redirect(
            "/worker/edit-profile"
        )


    conn.close()


    return render_template(
        "worker/edit_profile.html",
        worker=worker
    )


# ======================================
# UPDATE WORKER LIVE LOCATION
# ======================================

@worker_bp.route(
    "/worker/update-location",
    methods=["POST"]
)
def update_worker_location():

    try:

        data = request.get_json()

        latitude = data.get("latitude")

        longitude = data.get("longitude")


        if latitude is None or longitude is None:

            return jsonify({
                "success": False,
                "message": "Location not received."
            }), 400


        latitude = float(latitude)

        longitude = float(longitude)


        # =========================
        # VALIDATE LATITUDE
        # =========================

        if latitude < -90 or latitude > 90:

            return jsonify({
                "success": False,
                "message": "Invalid latitude."
            }), 400


        # =========================
        # VALIDATE LONGITUDE
        # =========================

        if longitude < -180 or longitude > 180:

            return jsonify({
                "success": False,
                "message": "Invalid longitude."
            }), 400


        # =========================
        # UPDATE DATABASE
        # =========================

        conn = get_db()

        cur = conn.cursor()

        cur.execute("""
            UPDATE workers
            SET
                latitude=?,
                longitude=?
            WHERE worker_id=?
        """, (
            latitude,
            longitude,
            session["user_id"]
        ))


        conn.commit()

        conn.close()


        return jsonify({
            "success": True,
            "message": "Live location updated successfully."
        })


    except Exception as e:

        print(
            "LOCATION ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Unable to update location."
        }), 500


# ======================================
# Change Bank
# ======================================

@worker_bp.route(
    "/worker/change-bank",
    methods=["POST"]
)
def change_bank():

    conn = get_db()

    cur = conn.cursor()

    cur.execute("""
    SELECT email
    FROM workers
    WHERE worker_id=?
    """, (
        session["user_id"],
    ))

    worker = cur.fetchone()


    otp = str(
        random.randint(
            100000,
            999999
        )
    )


    session["bank_otp"] = otp


    session["bank_expiry"] = (
        datetime.now()
        + timedelta(minutes=5)
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    session["new_bank"] = {

        "bank_name":
            request.form["bank_name"],

        "account_holder":
            request.form["account_holder"],

        "account_number":
            request.form["account_number"],

        "ifsc":
            request.form["ifsc"]

    }


    threading.Thread(
        target=send_otp,
        args=(
            worker["email"],
            otp
        )
    ).start()


    conn.close()


    flash(
        "OTP sent to your email.",
        "success"
    )


    return redirect(
        "/worker/verify-bank-otp"
    )


# ======================================
# Resend Bank OTP
# ======================================

@worker_bp.route(
    "/worker/resend-bank-otp"
)
def resend_bank_otp():

    conn = get_db()

    cur = conn.cursor()


    cur.execute("""
    SELECT email
    FROM workers
    WHERE worker_id=?
    """, (
        session["user_id"],
    ))


    worker = cur.fetchone()

    conn.close()


    otp = str(
        random.randint(
            100000,
            999999
        )
    )


    session["bank_otp"] = otp


    session["bank_expiry"] = (
        datetime.now()
        + timedelta(minutes=5)
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    threading.Thread(
        target=send_otp,
        args=(
            worker["email"],
            otp
        )
    ).start()


    flash(
        "New OTP Sent Successfully.",
        "success"
    )


    return redirect(
        "/worker/verify-bank-otp"
    )


# ======================================
# Worker Bank Details
# ======================================

@worker_bp.route(
    "/worker/bank",
    methods=["GET", "POST"]
)
def worker_bank():

    conn = get_db()

    cur = conn.cursor()


    cur.execute("""
    SELECT *
    FROM workers
    WHERE worker_id=?
    """, (
        session["user_id"],
    ))


    worker = cur.fetchone()

    conn.close()


    return render_template(
        "worker/bank.html",
        worker=worker
    )


# ======================================
# Verify Bank OTP
# ======================================

@worker_bp.route(
    "/worker/verify-bank-otp",
    methods=["GET", "POST"]
)
def verify_bank_otp():

    if "new_bank" not in session:

        return redirect(
            "/worker/bank"
        )


    if request.method == "POST":

        otp = request.form["otp"]


        if otp != session.get(
            "bank_otp"
        ):

            flash(
                "Invalid OTP",
                "danger"
            )

            return redirect(
                "/worker/verify-bank-otp"
            )


        expiry = datetime.strptime(
            session["bank_expiry"],
            "%Y-%m-%d %H:%M:%S"
        )


        if datetime.now() > expiry:

            flash(
                "OTP Expired",
                "danger"
            )

            return redirect(
                "/worker/verify-bank-otp"
            )


        bank = session["new_bank"]


        conn = get_db()

        cur = conn.cursor()


        cur.execute("""

        UPDATE workers

        SET

            bank_name=?,
            account_holder=?,
            account_number=?,
            ifsc=?

        WHERE worker_id=?

        """, (

            bank["bank_name"],

            bank["account_holder"],

            bank["account_number"],

            bank["ifsc"],

            session["user_id"]

        ))


        conn.commit()

        conn.close()


        session.pop(
            "bank_otp",
            None
        )

        session.pop(
            "bank_expiry",
            None
        )

        session.pop(
            "new_bank",
            None
        )


        flash(
            "Bank Details Updated Successfully.",
            "success"
        )


        return redirect(
            "/worker/bank"
        )


    return render_template(
        "worker/verify_bank_otp.html"
    )


# ======================================
# Settings
# ======================================

@worker_bp.route(
    "/worker/settings"
)
def worker_settings():

    conn = get_db()

    cur = conn.cursor()


    cur.execute("""
    SELECT *
    FROM workers
    WHERE worker_id=?
    """, (
        session["user_id"],
    ))


    worker = cur.fetchone()

    conn.close()


    return render_template(
        "worker/settings.html",
        worker=worker
    )


# ======================================
# Change Password
# ======================================

@worker_bp.route(
    "/worker/change-password",
    methods=["GET", "POST"]
)
def change_password():

    if request.method == "POST":

        current_password = request.form[
            "current_password"
        ]

        new_password = request.form[
            "new_password"
        ]

        confirm_password = request.form[
            "confirm_password"
        ]


        conn = get_db()

        cur = conn.cursor()


        cur.execute("""
        SELECT email,password
        FROM workers
        WHERE worker_id=?
        """, (
            session["user_id"],
        ))


        worker = cur.fetchone()

        conn.close()


        if not check_password_hash(
            worker["password"],
            current_password
        ):

            flash(
                "Current Password is Incorrect.",
                "danger"
            )

            return redirect(
                "/worker/change-password"
            )


        if new_password != confirm_password:

            flash(
                "New Password and Confirm Password do not match.",
                "danger"
            )

            return redirect(
                "/worker/change-password"
            )


        otp = str(
            random.randint(
                100000,
                999999
            )
        )


        session["password_otp"] = otp


        session["new_password"] = (
            generate_password_hash(
                new_password
            )
        )


        threading.Thread(
            target=send_otp,
            args=(
                worker["email"],
                otp
            )
        ).start()


        flash(
            "OTP sent to your email.",
            "success"
        )


        return redirect(
            "/worker/verify-password-otp"
        )


    return render_template(
        "worker/change_password.html"
    )


# ======================================
# Verify Password OTP
# ======================================

@worker_bp.route(
    "/worker/verify-password-otp",
    methods=["GET", "POST"]
)
def verify_password_otp():

    if "new_password" not in session:

        return redirect(
            "/worker/change-password"
        )


    if request.method == "POST":

        otp = request.form[
            "otp"
        ].strip()


        if otp != session.get(
            "password_otp"
        ):

            flash(
                "Invalid OTP.",
                "danger"
            )

            return redirect(
                "/worker/verify-password-otp"
            )


        conn = get_db()

        cur = conn.cursor()


        cur.execute("""
        UPDATE workers
        SET password=?
        WHERE worker_id=?
        """, (
            session["new_password"],
            session["user_id"]
        ))


        conn.commit()

        conn.close()


        flash(
            "Password Changed Successfully.",
            "success"
        )


        session.pop(
            "password_otp",
            None
        )

        session.pop(
            "new_password",
            None
        )


        return render_template(
            "worker/verify_password_otp.html"
        )


    return render_template(
        "worker/verify_password_otp.html"
    )


# ======================================
# Resend Password OTP
# ======================================

@worker_bp.route(
    "/worker/resend-password-otp"
)
def resend_password_otp():

    if "new_password" not in session:

        return redirect(
            "/worker/change-password"
        )


    conn = get_db()

    cur = conn.cursor()


    cur.execute("""
    SELECT email
    FROM workers
    WHERE worker_id=?
    """, (
        session["user_id"],
    ))


    worker = cur.fetchone()

    conn.close()


    otp = str(
        random.randint(
            100000,
            999999
        )
    )


    session["password_otp"] = otp


    threading.Thread(
        target=send_otp,
        args=(
            worker["email"],
            otp
        )
    ).start()


    flash(
        "New OTP Sent Successfully.",
        "success"
    )


    return redirect(
        "/worker/verify-password-otp"
    )


# ======================================
# About
# ======================================

@worker_bp.route(
    "/worker/about"
)
def about():

    return render_template(
        "worker/about.html"
    )


# ======================================
# Privacy Policy
# ======================================

@worker_bp.route(
    "/worker/privacy_policy"
)
def privacy_policy():

    return render_template(
        "worker/privacy_policy.html"
    )


# ======================================
# Terms
# ======================================

@worker_bp.route(
    "/worker/terms"
)
def terms():

    return render_template(
        "worker/terms.html"
    )


# ======================================
# Help
# ======================================

@worker_bp.route(
    "/worker/help"
)
def help():

    return render_template(
        "worker/help.html"
    )


# ======================================
# Rate Workmitra
# ======================================

@worker_bp.route(
    "/worker/rate-app",
    methods=["GET", "POST"]
)
def rate_app():

    if request.method == "POST":

        rating = request.form.get(
            "rating"
        )

        feedback = request.form.get(
            "feedback",
            ""
        ).strip()


        if not rating:

            flash(
                "Please select a rating.",
                "danger"
            )

            return redirect(
                "/worker/rate-app"
            )


        try:

            rating = int(rating)

        except ValueError:

            flash(
                "Invalid rating.",
                "danger"
            )

            return redirect(
                "/worker/rate-app"
            )


        if rating < 1 or rating > 5:

            flash(
                "Rating must be between 1 and 5.",
                "danger"
            )

            return redirect(
                "/worker/rate-app"
            )


        conn = get_db()

        cur = conn.cursor()


        cur.execute("""
        INSERT INTO worker_ratings
        (
            worker_id,
            rating,
            feedback
        )
        VALUES (?, ?, ?)
        """, (
            session["user_id"],
            rating,
            feedback
        ))


        conn.commit()

        conn.close()


        flash(
            "Thank you! Your review has been submitted successfully.",
            "success"
        )


        return redirect(
            "/worker/rate-app"
        )


    return render_template(
        "worker/rate_app.html"
    )


# ======================================
# Check for Update
# ======================================

@worker_bp.route(
    "/worker/check-update"
)
def check_update():

    current_version = "1.0.0"

    latest_version = "1.0.0"


    if current_version == latest_version:

        update_available = False

    else:

        update_available = True


    return render_template(
        "worker/check_update.html",
        current_version=current_version,
        latest_version=latest_version,
        update_available=update_available
    )


# ======================================
# App Version
# ======================================

@worker_bp.route(
    "/worker/app-version"
)
def app_version():

    version = "1.0.0"


    return render_template(
        "worker/app_version.html",
        version=version
    )


# ======================================
# FAQ
# ======================================

@worker_bp.route(
    "/worker/faq"
)
def faq():

    return render_template(
        "worker/faq.html"
    )
