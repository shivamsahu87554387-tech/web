from flask import (
    Blueprint,
    render_template,
    session,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)

from werkzeug.utils import secure_filename

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

import os
import threading
import random

from datetime import datetime, timedelta

from utils.email_sender import send_otp
from database import get_db
from routes.decorators import worker_required


# ============================================================
# BLUEPRINT
# ============================================================

worker_bp = Blueprint(
    "worker",
    __name__
)


# ============================================================
# CONFIG
# ============================================================

UPLOAD_FOLDER = "static/uploads"


# ============================================================
# COMMON HELPERS
# ============================================================

def get_current_worker():

    worker_id = session.get("user_id")

    if not worker_id:
        return None

    conn = get_db()

    try:

        worker = conn.execute(
            """
            SELECT *
            FROM workers
            WHERE worker_id = ?
            LIMIT 1
            """,
            (worker_id,)
        ).fetchone()

        return worker

    except Exception as error:

        print(
            "GET CURRENT WORKER ERROR:",
            error
        )

        return None

    finally:

        conn.close()


def get_current_worker_db_id():

    worker = get_current_worker()

    if not worker:
        return None

    return worker["id"]


def get_booking_for_worker(booking_value):

    worker_db_id = get_current_worker_db_id()

    if not worker_db_id:
        return None

    if not booking_value:
        return None

    conn = get_db()

    try:

        if str(booking_value).isdigit():

            booking = conn.execute(
                """
                SELECT
                    b.*,

                    c.fullname AS customer_name,
                    c.mobile AS customer_mobile,
                    c.email AS customer_email,

                    w.fullname AS worker_name,
                    w.mobile AS worker_mobile

                FROM bookings b

                LEFT JOIN customers c
                    ON c.id = b.customer_id

                LEFT JOIN workers w
                    ON w.id = b.worker_id

                WHERE b.id = ?
                AND b.worker_id = ?

                LIMIT 1
                """,
                (
                    int(booking_value),
                    worker_db_id
                )
            ).fetchone()

            if booking:
                return booking

        booking = conn.execute(
            """
            SELECT
                b.*,

                c.fullname AS customer_name,
                c.mobile AS customer_mobile,
                c.email AS customer_email,

                w.fullname AS worker_name,
                w.mobile AS worker_mobile

            FROM bookings b

            LEFT JOIN customers c
                ON c.id = b.customer_id

            LEFT JOIN workers w
                ON w.id = b.worker_id

            WHERE b.booking_id = ?
            AND b.worker_id = ?

            LIMIT 1
            """,
            (
                booking_value,
                worker_db_id
            )
        ).fetchone()

        return booking

    except Exception as error:

        print(
            "GET WORKER BOOKING ERROR:",
            error
        )

        return None

    finally:

        conn.close()


def create_notification(
    user_type,
    user_id,
    title,
    message
):

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO notifications
            (
                user_type,
                user_id,
                title,
                message
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_type,
                str(user_id),
                title,
                message
            )
        )

        conn.commit()

    except Exception as error:

        conn.rollback()

        print(
            "NOTIFICATION ERROR:",
            error
        )

    finally:

        conn.close()


def update_booking_status(
    booking_id,
    new_status,
    allowed_statuses=None
):

    worker_db_id = get_current_worker_db_id()

    if not worker_db_id:
        return False, "Worker session expired."

    conn = get_db()

    try:

        if allowed_statuses:

            placeholders = ",".join(
                ["?"] * len(allowed_statuses)
            )

            query = f"""
                UPDATE bookings
                SET
                    booking_status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                AND worker_id = ?
                AND LOWER(booking_status)
                    IN ({placeholders})
            """

            params = [
                new_status,
                booking_id,
                worker_db_id
            ]

            params.extend(
                allowed_statuses
            )

            cursor = conn.execute(
                query,
                params
            )

        else:

            cursor = conn.execute(
                """
                UPDATE bookings
                SET
                    booking_status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                AND worker_id = ?
                """,
                (
                    new_status,
                    booking_id,
                    worker_db_id
                )
            )

        if cursor.rowcount == 0:

            conn.rollback()

            return (
                False,
                "Booking cannot be updated."
            )

        conn.commit()

        return (
            True,
            "Booking status updated."
        )

    except Exception as error:

        conn.rollback()

        print(
            "UPDATE BOOKING STATUS ERROR:",
            error
        )

        return (
            False,
            "Booking could not be updated."
        )

    finally:

        conn.close()


# ============================================================
# WORKER DASHBOARD
# ============================================================

@worker_bp.route("/worker/home")
@worker_required
def worker_home():

    worker = get_current_worker()

    if not worker:

        session.clear()

        return redirect("/worker/login")

    worker_db_id = worker["id"]

    conn = get_db()

    try:

        total_jobs = conn.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE worker_id = ?
            """,
            (worker_db_id,)
        ).fetchone()[0]

        pending_jobs = conn.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE worker_id = ?
            AND LOWER(booking_status)
            IN ('assigned', 'pending')
            """,
            (worker_db_id,)
        ).fetchone()[0]

        active_jobs = conn.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE worker_id = ?
            AND LOWER(booking_status)
            IN ('accepted', 'started', 'in_progress')
            """,
            (worker_db_id,)
        ).fetchone()[0]

        completed_jobs = conn.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE worker_id = ?
            AND LOWER(booking_status)
            = 'completed'
            """,
            (worker_db_id,)
        ).fetchone()[0]

        recent_jobs = conn.execute(
            """
            SELECT
                b.*,
                c.fullname AS customer_name,
                c.mobile AS customer_mobile
            FROM bookings b
            LEFT JOIN customers c
                ON c.id = b.customer_id
            WHERE b.worker_id = ?
            ORDER BY b.id DESC
            LIMIT 5
            """,
            (worker_db_id,)
        ).fetchall()

    except Exception as error:

        print(
            "WORKER DASHBOARD ERROR:",
            error
        )

        total_jobs = 0
        pending_jobs = 0
        active_jobs = 0
        completed_jobs = 0
        recent_jobs = []

    finally:

        conn.close()

    return render_template(
        "worker/home.html",
        worker=worker,
        total_jobs=total_jobs,
        pending_jobs=pending_jobs,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        recent_jobs=recent_jobs
    )


# ============================================================
# MY JOBS
# ============================================================

@worker_bp.route("/worker/jobs")
@worker_required
def worker_jobs():

    worker = get_current_worker()

    if not worker:

        session.clear()

        return redirect("/worker/login")

    conn = get_db()

    try:

        jobs = conn.execute(
            """
            SELECT
                b.*,

                c.fullname AS customer_name,
                c.mobile AS customer_mobile,
                c.email AS customer_email,

                c.address AS customer_saved_address,
                c.city AS customer_city,
                c.state AS customer_state,
                c.pincode AS customer_pincode

            FROM bookings b

            LEFT JOIN customers c
                ON c.id = b.customer_id

            WHERE b.worker_id = ?

            ORDER BY
                CASE
                    WHEN LOWER(b.booking_status)
                        IN ('assigned', 'pending')
                    THEN 1

                    WHEN LOWER(b.booking_status)
                        IN ('accepted', 'started', 'in_progress')
                    THEN 2

                    WHEN LOWER(b.booking_status)
                        = 'completed'
                    THEN 3

                    ELSE 4
                END,

                b.id DESC
            """,
            (worker["id"],)
        ).fetchall()

    except Exception as error:

        print(
            "WORKER JOBS ERROR:",
            error
        )

        jobs = []

    finally:

        conn.close()

    return render_template(
        "worker/jobs.html",
        worker=worker,
        jobs=jobs
    )


# ============================================================
# JOB DETAILS
# ============================================================

@worker_bp.route(
    "/worker/job/<job_id>"
)
@worker_required
def job_details(job_id):

    worker = get_current_worker()

    if not worker:

        session.clear()

        return redirect("/worker/login")

    job = get_booking_for_worker(
        job_id
    )

    if not job:

        flash(
            "Job not found.",
            "danger"
        )

        return redirect(
            url_for("worker.worker_jobs")
        )

    return render_template(
        "worker/job_details.html",
        worker=worker,
        job=job,
        booking=job,
        job_id=job_id
    )


# ============================================================
# ACCEPT JOB
# ============================================================

@worker_bp.route(
    "/worker/job/<job_id>/accept",
    methods=["POST"]
)
@worker_required
def accept_job(job_id):

    booking = get_booking_for_worker(
        job_id
    )

    if not booking:

        return jsonify({
            "success": False,
            "message": "Job not found."
        }), 404

    status = (
        booking["booking_status"]
        or "pending"
    ).lower()

    if status not in (
        "assigned",
        "pending"
    ):

        return jsonify({
            "success": False,
            "message":
                "This job cannot be accepted."
        }), 400

    success, message = update_booking_status(
        booking["id"],
        "accepted",
        [
            "assigned",
            "pending"
        ]
    )

    if not success:

        return jsonify({
            "success": False,
            "message": message
        }), 400

    create_notification(
        "customer",
        booking["customer_id"],
        "Worker Accepted Your Booking",
        "Your worker has accepted booking "
        + str(booking["booking_id"])
    )

    return jsonify({
        "success": True,
        "message":
            "Job accepted successfully.",
        "status": "accepted"
    })


# ============================================================
# REJECT JOB
# ============================================================

@worker_bp.route(
    "/worker/job/<job_id>/reject",
    methods=["POST"]
)
@worker_required
def reject_job(job_id):

    booking = get_booking_for_worker(
        job_id
    )

    if not booking:

        return jsonify({
            "success": False,
            "message": "Job not found."
        }), 404

    status = (
        booking["booking_status"]
        or "pending"
    ).lower()

    if status not in (
        "assigned",
        "pending"
    ):

        return jsonify({
            "success": False,
            "message":
                "This job cannot be rejected."
        }), 400

    data = request.get_json(
        silent=True
    )

    if data is None:

        data = request.form.to_dict()

    reason = str(
        data.get(
            "reason",
            "Worker rejected the job."
        )
    ).strip()

    conn = get_db()

    try:

        cursor = conn.execute(
            """
            UPDATE bookings
            SET
                booking_status = 'pending',
                worker_id = NULL,
                cancellation_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            AND worker_id = ?
            AND LOWER(booking_status)
                IN ('assigned', 'pending')
            """,
            (
                reason,
                booking["id"],
                get_current_worker_db_id()
            )
        )

        if cursor.rowcount == 0:

            conn.rollback()

            return jsonify({
                "success": False,
                "message":
                    "Job could not be rejected."
            }), 400

        conn.commit()

    except Exception as error:

        conn.rollback()

        print(
            "REJECT JOB ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message":
                "Job could not be rejected."
        }), 500

    finally:

        conn.close()

    create_notification(
        "customer",
        booking["customer_id"],
        "Worker Unavailable",
        "The assigned worker was unavailable. "
        "Your booking will be reassigned."
    )

    return jsonify({
        "success": True,
        "message":
            "Job rejected. It can now be reassigned."
    })


# ============================================================
# START JOB
# ============================================================

@worker_bp.route(
    "/worker/job/<job_id>/start",
    methods=["POST"]
)
@worker_required
def start_job(job_id):

    booking = get_booking_for_worker(
        job_id
    )

    if not booking:

        return jsonify({
            "success": False,
            "message": "Job not found."
        }), 404

    success, message = update_booking_status(
        booking["id"],
        "in_progress",
        [
            "accepted"
        ]
    )

    if not success:

        return jsonify({
            "success": False,
            "message":
                "Job must be accepted before starting."
        }), 400

    create_notification(
        "customer",
        booking["customer_id"],
        "Service Started",
        "Your worker has started booking "
        + str(booking["booking_id"])
    )

    return jsonify({
        "success": True,
        "message":
            "Job started successfully.",
        "status": "in_progress"
    })


# ============================================================
# COMPLETE JOB
# ============================================================

@worker_bp.route(
    "/worker/job/<job_id>/complete",
    methods=["POST"]
)
@worker_required
def complete_job(job_id):

    booking = get_booking_for_worker(
        job_id
    )

    if not booking:

        return jsonify({
            "success": False,
            "message": "Job not found."
        }), 404

    success, message = update_booking_status(
        booking["id"],
        "completed",
        [
            "in_progress",
            "started"
        ]
    )

    if not success:

        return jsonify({
            "success": False,
            "message":
                "Job must be in progress before completion."
        }), 400

    create_notification(
        "customer",
        booking["customer_id"],
        "Service Completed",
        "Your service booking "
        + str(booking["booking_id"])
        + " has been completed."
    )

    return jsonify({
        "success": True,
        "message":
            "Job completed successfully.",
        "status": "completed"
    })


# ============================================================
# WALLET
# ============================================================

@worker_bp.route("/worker/wallet")
@worker_required
def wallet():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

    worker_id = worker["worker_id"]

    conn = get_db()

    try:

        total_earned_row = conn.execute(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            )
            FROM wallet_transactions
            WHERE user_type = 'worker'
            AND user_id = ?
            AND transaction_type
                IN ('earning', 'credit')
            """,
            (worker_id,)
        ).fetchone()

        paid_row = conn.execute(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            )
            FROM wallet_transactions
            WHERE user_type = 'worker'
            AND user_id = ?
            AND transaction_type
                IN ('withdraw', 'debit')
            """,
            (worker_id,)
        ).fetchone()

        transactions = conn.execute(
            """
            SELECT *
            FROM wallet_transactions
            WHERE user_type = 'worker'
            AND user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (worker_id,)
        ).fetchall()

        total_earned = (
            total_earned_row[0]
            if total_earned_row
            else 0
        )

        paid_amount = (
            paid_row[0]
            if paid_row
            else 0
        )

        pending_payment = max(
            float(total_earned or 0)
            - float(paid_amount or 0),
            0
        )

    except Exception as error:

        print(
            "WORKER WALLET ERROR:",
            error
        )

        total_earned = 0
        paid_amount = 0
        pending_payment = 0
        transactions = []

    finally:

        conn.close()

    return render_template(
        "worker/wallet.html",
        worker=worker,
        total_earned=total_earned,
        pending_payment=pending_payment,
        paid_amount=paid_amount,
        transactions=transactions
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

@worker_bp.route(
    "/worker/notifications",
    methods=["GET", "POST"]
)
@worker_required
def notifications():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

    conn = get_db()

    try:

        if request.method == "POST":

            app_notification = (
                1
                if request.form.get(
                    "app_notification"
                )
                else 0
            )

            email_notification = (
                1
                if request.form.get(
                    "email_notification"
                )
                else 0
            )

            job_notification = (
                1
                if request.form.get(
                    "job_notification"
                )
                else 0
            )

            payment_notification = (
                1
                if request.form.get(
                    "payment_notification"
                )
                else 0
            )

            promo_notification = (
                1
                if request.form.get(
                    "promo_notification"
                )
                else 0
            )

            conn.execute(
                """
                UPDATE workers
                SET
                    app_notification = ?,
                    email_notification = ?,
                    job_notification = ?,
                    payment_notification = ?,
                    promo_notification = ?
                WHERE worker_id = ?
                """,
                (
                    app_notification,
                    email_notification,
                    job_notification,
                    payment_notification,
                    promo_notification,
                    session["user_id"]
                )
            )

            conn.commit()

            flash(
                "Notification Settings Updated Successfully.",
                "success"
            )

        worker = conn.execute(
            """
            SELECT *
            FROM workers
            WHERE worker_id = ?
            """,
            (
                session["user_id"],
            )
        ).fetchone()

    except Exception as error:

        conn.rollback()

        print(
            "NOTIFICATION SETTINGS ERROR:",
            error
        )

    finally:

        conn.close()

    return render_template(
        "worker/notifications.html",
        worker=worker
    )


# ============================================================
# PROFILE
# ============================================================

@worker_bp.route("/worker/profile")
@worker_required
def profile():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

    return render_template(
        "worker/profile.html",
        worker=worker
    )


# ============================================================
# EDIT PROFILE
# ============================================================

@worker_bp.route(
    "/worker/edit-profile",
    methods=["GET", "POST"]
)
@worker_required
def edit_profile():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

    if request.method == "POST":

        fullname = request.form.get(
            "fullname",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        city = request.form.get(
            "city",
            ""
        ).strip()

        state = request.form.get(
            "state",
            ""
        ).strip()

        pincode = request.form.get(
            "pincode",
            ""
        ).strip()

        skills = ", ".join(
            request.form.getlist(
                "skills"
            )
        )

        if not skills:

            skills = request.form.get(
                "skills",
                ""
            ).strip()

        experience = request.form.get(
            "experience",
            ""
        ).strip()

        latitude = request.form.get(
            "latitude"
        )

        longitude = request.form.get(
            "longitude"
        )

        # ----------------------------------------------------
        # LOCATION VALIDATION
        # ----------------------------------------------------

        try:

            latitude = (
                float(latitude)
                if latitude
                else None
            )

            if (
                latitude is not None
                and (
                    latitude < -90
                    or latitude > 90
                )
            ):
                latitude = None

        except (
            ValueError,
            TypeError
        ):

            latitude = None

        try:

            longitude = (
                float(longitude)
                if longitude
                else None
            )

            if (
                longitude is not None
                and (
                    longitude < -180
                    or longitude > 180
                )
            ):
                longitude = None

        except (
            ValueError,
            TypeError
        ):

            longitude = None

        # ----------------------------------------------------
        # PHOTO
        # ----------------------------------------------------

        photo = request.files.get(
            "profile_photo"
        )

        photo_name = worker[
            "profile_photo"
        ]

        if (
            photo
            and photo.filename
        ):

            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True
            )

            filename = secure_filename(
                photo.filename
            )

            if filename:

                photo.save(
                    os.path.join(
                        UPLOAD_FOLDER,
                        filename
                    )
                )

                photo_name = filename

        conn = get_db()

        try:

            conn.execute(
                """
                UPDATE workers
                SET
                    fullname = ?,
                    address = ?,
                    city = ?,
                    state = ?,
                    pincode = ?,
                    skills = ?,
                    experience = ?,
                    profile_photo = ?,
                    latitude = ?,
                    longitude = ?
                WHERE worker_id = ?
                """,
                (
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
                )
            )

            conn.commit()

        except Exception as error:

            conn.rollback()

            print(
                "EDIT PROFILE ERROR:",
                error
            )

            flash(
                "Profile could not be updated.",
                "danger"
            )

            conn.close()

            return redirect(
                "/worker/edit-profile"
            )

        finally:

            conn.close()

        flash(
            "Profile Updated Successfully.",
            "success"
        )

        return redirect(
            "/worker/edit-profile"
        )

    return render_template(
        "worker/edit_profile.html",
        worker=worker
    )


# ============================================================
# UPDATE LIVE LOCATION
# ============================================================

@worker_bp.route(
    "/worker/update-location",
    methods=["POST"]
)
@worker_required
def update_worker_location():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        latitude = data.get(
            "latitude"
        )

        longitude = data.get(
            "longitude"
        )

        if (
            latitude is None
            or longitude is None
        ):

            return jsonify({
                "success": False,
                "message":
                    "Location not received."
            }), 400

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

        if (
            latitude < -90
            or latitude > 90
        ):

            return jsonify({
                "success": False,
                "message":
                    "Invalid latitude."
            }), 400

        if (
            longitude < -180
            or longitude > 180
        ):

            return jsonify({
                "success": False,
                "message":
                    "Invalid longitude."
            }), 400

        conn = get_db()

        try:

            conn.execute(
                """
                UPDATE workers
                SET
                    latitude = ?,
                    longitude = ?
                WHERE worker_id = ?
                """,
                (
                    latitude,
                    longitude,
                    session["user_id"]
                )
            )

            conn.commit()

        finally:

            conn.close()

        return jsonify({
            "success": True,
            "message":
                "Live location updated successfully."
        })

    except Exception as error:

        print(
            "LOCATION ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message":
                "Unable to update location."
        }), 500


# ============================================================
# BANK
# ============================================================

@worker_bp.route(
    "/worker/bank",
    methods=["GET", "POST"]
)
@worker_required
def worker_bank():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

    return render_template(
        "worker/bank.html",
        worker=worker
    )


# ============================================================
# CHANGE BANK
# ============================================================

@worker_bp.route(
    "/worker/change-bank",
    methods=["POST"]
)
@worker_required
def change_bank():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

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
            request.form.get(
                "bank_name",
                ""
            ).strip(),

        "account_holder":
            request.form.get(
                "account_holder",
                ""
            ).strip(),

        "account_number":
            request.form.get(
                "account_number",
                ""
            ).strip(),

        "ifsc":
            request.form.get(
                "ifsc",
                ""
            ).strip().upper()
    }

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
        "/worker/verify-bank-otp"
    )


# ============================================================
# RESEND BANK OTP
# ============================================================

@worker_bp.route(
    "/worker/resend-bank-otp"
)
@worker_required
def resend_bank_otp():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

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


# ============================================================
# VERIFY BANK OTP
# ============================================================

@worker_bp.route(
    "/worker/verify-bank-otp",
    methods=["GET", "POST"]
)
@worker_required
def verify_bank_otp():

    if "new_bank" not in session:

        return redirect(
            "/worker/bank"
        )

    if request.method == "POST":

        otp = request.form.get(
            "otp",
            ""
        ).strip()

        if otp != session.get(
            "bank_otp"
        ):

            flash(
                "Invalid OTP.",
                "danger"
            )

            return redirect(
                "/worker/verify-bank-otp"
            )

        try:

            expiry = datetime.strptime(
                session["bank_expiry"],
                "%Y-%m-%d %H:%M:%S"
            )

        except Exception:

            flash(
                "OTP expired.",
                "danger"
            )

            return redirect(
                "/worker/bank"
            )

        if datetime.now() > expiry:

            flash(
                "OTP Expired.",
                "danger"
            )

            return redirect(
                "/worker/bank"
            )

        bank = session[
            "new_bank"
        ]

        conn = get_db()

        try:

            conn.execute(
                """
                UPDATE workers
                SET
                    bank_name = ?,
                    account_holder = ?,
                    account_number = ?,
                    ifsc = ?
                WHERE worker_id = ?
                """,
                (
                    bank["bank_name"],
                    bank["account_holder"],
                    bank["account_number"],
                    bank["ifsc"],
                    session["user_id"]
                )
            )

            conn.commit()

        except Exception as error:

            conn.rollback()

            print(
                "BANK UPDATE ERROR:",
                error
            )

            flash(
                "Bank details could not be updated.",
                "danger"
            )

            conn.close()

            return redirect(
                "/worker/bank"
            )

        finally:

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


# ============================================================
# SETTINGS
# ============================================================

@worker_bp.route(
    "/worker/settings"
)
@worker_required
def worker_settings():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

    return render_template(
        "worker/settings.html",
        worker=worker
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================

@worker_bp.route(
    "/worker/change-password",
    methods=["GET", "POST"]
)
@worker_required
def change_password():

    worker = get_current_worker()

    if not worker:

        return redirect("/worker/login")

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

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

        if len(new_password) < 6:

            flash(
                "Password must contain at least 6 characters.",
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


# ============================================================
# VERIFY PASSWORD OTP
# ============================================================

@worker_bp.route(
    "/worker/verify-password-otp",
    methods=["GET", "POST"]
)
@worker_required
def verify_password_otp():

    if "new_password" not in session:

        return redirect(
            "/worker/change-password"
        )

    if request.method == "POST":

        otp = request.form.get(
            "otp",
            ""
        ).strip()

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

        try:

            conn.execute(
                """
                UPDATE workers
                SET password = ?
                WHERE worker_id = ?
                """,
                (
                    session["new_password"],
                    session["user_id"]
                )
            )

            conn.commit()

        except Exception as error:

            conn.rollback()

            print(
                "PASSWORD UPDATE ERROR:",
                error
            )

            flash(
                "Password could not be changed.",
                "danger"
            )

            conn.close()

            return redirect(
                "/worker/change-password"
            )

        finally:

            conn.close()

        session.pop(
            "password_otp",
            None
        )

        session.pop(
            "new_password",
            None
        )

        flash(
            "Password Changed Successfully.",
            "success"
        )

        return redirect(
            "/worker/settings"
        )

    return render_template(
        "worker/verify_password_otp.html"
    )


# ============================================================
# RESEND PASSWORD OTP
# ============================================================

@worker_bp.route(
    "/worker/resend-password-otp"
)
@worker_required
def resend_password_otp():

    if "new_password" not in session:

        return redirect(
            "/worker/change-password"
        )

    worker = get_current_worker()

    if not worker:

        return redirect(
            "/worker/login"
        )

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


# ============================================================
# ABOUT
# ============================================================

@worker_bp.route(
    "/worker/about"
)
@worker_required
def about():

    return render_template(
        "worker/about.html"
    )


# ============================================================
# PRIVACY POLICY
# ============================================================

@worker_bp.route(
    "/worker/privacy_policy"
)
@worker_required
def privacy_policy():

    return render_template(
        "worker/privacy_policy.html"
    )


# ============================================================
# TERMS
# ============================================================

@worker_bp.route(
    "/worker/terms"
)
@worker_required
def terms():

    return render_template(
        "worker/terms.html"
    )


# ============================================================
# HELP
# ============================================================

@worker_bp.route(
    "/worker/help"
)
@worker_required
def help():

    return render_template(
        "worker/help.html"
    )


# ============================================================
# RATE APP
# ============================================================

@worker_bp.route(
    "/worker/rate-app",
    methods=["GET", "POST"]
)
@worker_required
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

            rating = int(
                rating
            )

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

        try:

            conn.execute(
                """
                INSERT INTO worker_ratings
                (
                    worker_id,
                    rating,
                    feedback
                )
                VALUES (?, ?, ?)
                """,
                (
                    session["user_id"],
                    rating,
                    feedback
                )
            )

            conn.commit()

        except Exception as error:

            conn.rollback()

            print(
                "WORKER RATING ERROR:",
                error
            )

            flash(
                "Rating could not be submitted.",
                "danger"
            )

            conn.close()

            return redirect(
                "/worker/rate-app"
            )

        finally:

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


# ============================================================
# CHECK UPDATE
# ============================================================

@worker_bp.route(
    "/worker/check-update"
)
@worker_required
def check_update():

    current_version = "1.0.0"

    latest_version = "1.0.0"

    update_available = (
        current_version != latest_version
    )

    return render_template(
        "worker/check_update.html",
        current_version=current_version,
        latest_version=latest_version,
        update_available=update_available
    )


# ============================================================
# APP VERSION
# ============================================================

@worker_bp.route(
    "/worker/app-version"
)
@worker_required
def app_version():

    version = "1.0.0"

    return render_template(
        "worker/app_version.html",
        version=version
    )


# ============================================================
# FAQ
# ============================================================

@worker_bp.route(
    "/worker/faq"
)
@worker_required
def faq():

    return render_template(
        "worker/faq.html"
    )
