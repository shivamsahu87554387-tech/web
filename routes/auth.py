import random

from datetime import datetime, timedelta

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import get_db

from utils.email_sender import send_otp

from utils.id_generator import (
    generate_worker_id,
    generate_partner_id,
    generate_referral_code
)


auth_bp = Blueprint(
    "auth",
    __name__
)


# ==========================================================
# HELPER: CLEAR PASSWORD RESET SESSION
# ==========================================================

def clear_reset_session():
    session.pop("reset_email", None)
    session.pop("reset_role", None)
    session.pop("reset_otp", None)
    session.pop("reset_otp_expiry", None)
    session.pop("reset_verified", None)


# ==========================================================
# SPLASH
# ==========================================================

@auth_bp.route("/")
def splash():

    return render_template(
        "splash.html"
    )


# ==========================================================
# CHOOSE ROLE
# ==========================================================

@auth_bp.route("/choose-role")
def choose_role():

    return render_template(
        "choose_role.html"
    )


# ==========================================================
# LOGIN
# ==========================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    role = request.args.get(
        "role",
        "worker"
    ).strip().lower()

    if role not in ("worker", "partner"):

        role = "worker"

    if request.method == "POST":

        user_id = request.form.get(
            "user_id",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # --------------------------------------------------
        # BASIC VALIDATION
        # --------------------------------------------------

        if not user_id or not password:

            flash(
                "Please enter your ID and Password.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.login",
                    role=role
                )
            )

        conn = get_db()
        cur = conn.cursor()

        # --------------------------------------------------
        # WORKER
        # --------------------------------------------------

        if role == "worker":

            cur.execute(
                """
                SELECT *
                FROM workers
                WHERE worker_id=?
                """,
                (user_id,)
            )

        # --------------------------------------------------
        # PARTNER
        # --------------------------------------------------

        else:

            cur.execute(
                """
                SELECT *
                FROM partners
                WHERE partner_id=?
                """,
                (user_id,)
            )

        user = cur.fetchone()

        conn.close()

        # --------------------------------------------------
        # USER NOT FOUND
        # --------------------------------------------------

        if not user:

            flash(
                "Invalid ID or Password.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.login",
                    role=role
                )
            )

        # --------------------------------------------------
        # DELETED ACCOUNT CHECK
        # --------------------------------------------------

        is_deleted = user["is_deleted"]

        if is_deleted:

            flash(
                "This account has been deleted. Please contact Workmitra Support.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.login",
                    role=role
                )
            )

        # --------------------------------------------------
        # ACCOUNT STATUS
        # --------------------------------------------------

        status = user["status"] or "active"

        if str(status).lower() == "suspended":

            if role == "worker":

                flash(
                    "Your worker account has been suspended. Please contact Workmitra Support.",
                    "danger"
                )

            else:

                flash(
                    "Your partner account has been suspended. Please contact Workmitra Support.",
                    "danger"
                )

            return redirect(
                url_for(
                    "auth.login",
                    role=role
                )
            )

        # --------------------------------------------------
        # PASSWORD CHECK
        # --------------------------------------------------

        stored_password = user["password"]

        if not stored_password:

            flash(
                "Your account password is not configured. Please contact support.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.login",
                    role=role
                )
            )

        try:

            password_valid = check_password_hash(
                stored_password,
                password
            )

        except (ValueError, TypeError):

            password_valid = False

        if not password_valid:

            flash(
                "Invalid ID or Password.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.login",
                    role=role
                )
            )

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        session.clear()

        if role == "worker":

            session["user_id"] = user["worker_id"]
            session["role"] = "worker"

            flash(
                "Login Successful.",
                "success"
            )

            return redirect(
                url_for(
                    "worker.worker_home"
                )
            )

        session["user_id"] = user["partner_id"]
        session["role"] = "partner"

        flash(
            "Login Successful.",
            "success"
        )

        return redirect(
            url_for(
                "partner.partner_home"
            )
        )

    # ------------------------------------------------------
    # LOGIN PAGE
    # ------------------------------------------------------

    return render_template(
        "login.html",
        role=role
    )


# ==========================================================
# SIGNUP
# ==========================================================

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():

    role = request.args.get(
        "role",
        "worker"
    ).strip().lower()

    if role not in ("worker", "partner"):

        role = "worker"

    if request.method == "POST":

        fullname = request.form.get(
            "fullname",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # --------------------------------------------------
        # VALIDATION
        # --------------------------------------------------

        if not fullname or not email or not mobile or not password:

            flash(
                "Please fill all required fields.",
                "danger"
            )

            return redirect(
                request.url
            )

        if password != confirm_password:

            flash(
                "Password and Confirm Password do not match.",
                "danger"
            )

            return redirect(
                request.url
            )

        conn = get_db()
        cur = conn.cursor()

        # --------------------------------------------------
        # DUPLICATE EMAIL
        # --------------------------------------------------

        if role == "worker":

            cur.execute(
                """
                SELECT id
                FROM workers
                WHERE email=?
                """,
                (email,)
            )

        else:

            cur.execute(
                """
                SELECT id
                FROM partners
                WHERE email=?
                """,
                (email,)
            )

        if cur.fetchone():

            conn.close()

            flash(
                "Email already registered.",
                "danger"
            )

            return redirect(
                request.url
            )

        # --------------------------------------------------
        # DUPLICATE MOBILE
        # --------------------------------------------------

        if role == "worker":

            cur.execute(
                """
                SELECT id
                FROM workers
                WHERE mobile=?
                """,
                (mobile,)
            )

        else:

            cur.execute(
                """
                SELECT id
                FROM partners
                WHERE mobile=?
                """,
                (mobile,)
            )

        if cur.fetchone():

            conn.close()

            flash(
                "Mobile already registered.",
                "danger"
            )

            return redirect(
                request.url
            )

        # --------------------------------------------------
        # HASH PASSWORD
        # --------------------------------------------------

        password_hash = generate_password_hash(
            password
        )

        # ==================================================
        # WORKER SIGNUP
        # ==================================================

        if role == "worker":

            worker_id = generate_worker_id()

            referred_by = request.form.get(
                "referral_code",
                "WM00000"
            ).strip()

            if not referred_by:

                referred_by = "WM00000"

            try:

                cur.execute(
                    """
                    INSERT INTO workers
                    (
                        worker_id,
                        fullname,
                        email,
                        mobile,
                        password,
                        referred_by
                    )
                    VALUES(?,?,?,?,?,?)
                    """,
                    (
                        worker_id,
                        fullname,
                        email,
                        mobile,
                        password_hash,
                        referred_by
                    )
                )

                # ------------------------------------------
                # FIND PARTNER
                # ------------------------------------------

                cur.execute(
                    """
                    SELECT partner_id
                    FROM partners
                    WHERE referral_code=?
                    AND is_deleted=0
                    """,
                    (referred_by,)
                )

                partner = cur.fetchone()

                # ------------------------------------------
                # LINK WORKER
                # ------------------------------------------

                if partner:

                    cur.execute(
                        """
                        INSERT INTO partner_workers
                        (
                            partner_id,
                            worker_id
                        )
                        VALUES(?,?)
                        """,
                        (
                            partner["partner_id"],
                            worker_id
                        )
                    )

                conn.commit()

            except Exception as e:

                conn.rollback()
                conn.close()

                print(
                    "WORKER SIGNUP ERROR:",
                    e
                )

                flash(
                    "Unable to create account. Please try again.",
                    "danger"
                )

                return redirect(
                    request.url
                )

            conn.close()

            return render_template(
                "account_created.html",
                account_id=worker_id,
                role="worker"
            )

        # ==================================================
        # PARTNER SIGNUP
        # ==================================================

        partner_id = generate_partner_id()
        referral_code = generate_referral_code()

        try:

            cur.execute(
                """
                INSERT INTO partners
                (
                    partner_id,
                    referral_code,
                    fullname,
                    email,
                    mobile,
                    password
                )
                VALUES(?,?,?,?,?,?)
                """,
                (
                    partner_id,
                    referral_code,
                    fullname,
                    email,
                    mobile,
                    password_hash
                )
            )

            conn.commit()

        except Exception as e:

            conn.rollback()
            conn.close()

            print(
                "PARTNER SIGNUP ERROR:",
                e
            )

            flash(
                "Unable to create account. Please try again.",
                "danger"
            )

            return redirect(
                request.url
            )

        conn.close()

        return render_template(
            "account_created.html",
            account_id=partner_id,
            referral_code=referral_code,
            role="partner"
        )

    return render_template(
        "signup.html",
        role=role
    )


# ==========================================================
# LOGOUT
# ==========================================================

@auth_bp.route("/logout")
def logout():

    session.clear()

    flash(
        "Logged out successfully.",
        "success"
    )

    return redirect(
        url_for(
            "auth.login"
        )
    )


# ==========================================================
# FORGOT PASSWORD
# ==========================================================

@auth_bp.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        if not email:

            flash(
                "Please enter your email address.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.forgot_password"
                )
            )

        conn = get_db()
        cur = conn.cursor()

        # --------------------------------------------------
        # WORKER CHECK
        # --------------------------------------------------

        cur.execute(
            """
            SELECT worker_id, status, is_deleted
            FROM workers
            WHERE email=?
            """,
            (email,)
        )

        user = cur.fetchone()

        role = "worker"

        # --------------------------------------------------
        # PARTNER CHECK
        # --------------------------------------------------

        if not user:

            cur.execute(
                """
                SELECT partner_id, status, is_deleted
                FROM partners
                WHERE email=?
                """,
                (email,)
            )

            user = cur.fetchone()

            role = "partner"

        conn.close()

        # --------------------------------------------------
        # EMAIL NOT FOUND
        # --------------------------------------------------

        if not user:

            flash(
                "Email not registered.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.forgot_password"
                )
            )

        # --------------------------------------------------
        # DELETED ACCOUNT
        # --------------------------------------------------

        if user["is_deleted"]:

            flash(
                "This account has been deleted. Please contact Workmitra Support.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.forgot_password"
                )
            )

        # --------------------------------------------------
        # SUSPENDED ACCOUNT
        # --------------------------------------------------

        if str(user["status"] or "active").lower() == "suspended":

            flash(
                "This account is suspended. Please contact Workmitra Support.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.forgot_password"
                )
            )

        # --------------------------------------------------
        # CLEAR OLD RESET DATA
        # --------------------------------------------------

        clear_reset_session()

        # --------------------------------------------------
        # GENERATE OTP
        # --------------------------------------------------

        otp = str(
            random.randint(
                100000,
                999999
            )
        )

        expiry = (
            datetime.now()
            + timedelta(minutes=5)
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        session["reset_email"] = email
        session["reset_role"] = role
        session["reset_otp"] = otp
        session["reset_otp_expiry"] = expiry
        session["reset_verified"] = False

        # --------------------------------------------------
        # SEND OTP
        # --------------------------------------------------

        try:

            send_otp(
                email,
                otp
            )

        except Exception as e:

            print(
                "FORGOT PASSWORD OTP ERROR:",
                e
            )

            clear_reset_session()

            flash(
                "Failed to send OTP. Please try again.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.forgot_password"
                )
            )

        flash(
            "OTP has been sent to your email.",
            "success"
        )

        return redirect(
            url_for(
                "auth.verify_otp"
            )
        )

    return render_template(
        "forgot_password.html"
    )


# ==========================================================
# VERIFY OTP
# ==========================================================

@auth_bp.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    # ------------------------------------------------------
    # RESET SESSION CHECK
    # ------------------------------------------------------

    if not session.get("reset_email"):

        flash(
            "Please request a password reset first.",
            "warning"
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    if not session.get("reset_role"):

        clear_reset_session()

        flash(
            "Password reset session expired. Please start again.",
            "warning"
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    # ------------------------------------------------------
    # OTP CHECK
    # ------------------------------------------------------

    stored_otp = session.get(
        "reset_otp"
    )

    if not stored_otp:

        flash(
            "OTP session expired. Please request a new OTP.",
            "warning"
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    # ------------------------------------------------------
    # EXPIRY CHECK
    # ------------------------------------------------------

    expiry_string = session.get(
        "reset_otp_expiry"
    )

    if not expiry_string:

        clear_reset_session()

        flash(
            "OTP session expired. Please request a new OTP.",
            "warning"
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    try:

        expiry = datetime.strptime(
            expiry_string,
            "%Y-%m-%d %H:%M:%S"
        )

    except (ValueError, TypeError):

        clear_reset_session()

        flash(
            "OTP session expired. Please request a new OTP.",
            "warning"
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    if datetime.now() > expiry:

        clear_reset_session()

        flash(
            "OTP has expired. Please request a new OTP.",
            "danger"
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    # ------------------------------------------------------
    # POST OTP
    # ------------------------------------------------------

    if request.method == "POST":

        otp = request.form.get(
            "otp",
            ""
        ).strip()

        if not otp:

            flash(
                "Please enter the OTP.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.verify_otp"
                )
            )

        if otp != stored_otp:

            flash(
                "Invalid OTP.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.verify_otp"
                )
            )

        # --------------------------------------------------
        # OTP VERIFIED
        # --------------------------------------------------

        session["reset_verified"] = True

        # OTP cannot be reused
        session.pop(
            "reset_otp",
            None
        )

        session.pop(
            "reset_otp_expiry",
            None
        )

        flash(
            "OTP Verified Successfully.",
            "success"
        )

        return redirect(
            url_for(
                "auth.new_password"
            )
        )

    return render_template(
        "verify_otp.html"
    )


# ==========================================================
# NEW PASSWORD
# ==========================================================

@auth_bp.route(
    "/new-password",
    methods=["GET", "POST"]
)
def new_password():

    reset_email = session.get(
        "reset_email"
    )

    reset_role = session.get(
        "reset_role"
    )

    reset_verified = session.get(
        "reset_verified",
        False
    )

    # ------------------------------------------------------
    # RESET SESSION CHECK
    # ------------------------------------------------------

    if not reset_email or reset_role not in (
        "worker",
        "partner"
    ):

        clear_reset_session()

        flash(
            "Password reset session expired. Please start again.",
            "warning"
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    # ------------------------------------------------------
    # OTP VERIFICATION CHECK
    # ------------------------------------------------------

    if reset_verified is not True:

        flash(
            "Please verify the OTP first.",
            "warning"
        )

        return redirect(
            url_for(
                "auth.verify_otp"
            )
        )

    # ------------------------------------------------------
    # CHANGE PASSWORD
    # ------------------------------------------------------

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not password or not confirm_password:

            flash(
                "Please enter the new password.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.new_password"
                )
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.new_password"
                )
            )

        # --------------------------------------------------
        # PASSWORD HASH
        # --------------------------------------------------

        password_hash = generate_password_hash(
            password
        )

        conn = get_db()
        cur = conn.cursor()

        try:

            # ----------------------------------------------
            # WORKER
            # ----------------------------------------------

            if reset_role == "worker":

                cur.execute(
                    """
                    UPDATE workers
                    SET password=?
                    WHERE email=?
                    AND is_deleted=0
                    """,
                    (
                        password_hash,
                        reset_email
                    )
                )

            # ----------------------------------------------
            # PARTNER
            # ----------------------------------------------

            else:

                cur.execute(
                    """
                    UPDATE partners
                    SET password=?
                    WHERE email=?
                    AND is_deleted=0
                    """,
                    (
                        password_hash,
                        reset_email
                    )
                )

            # ----------------------------------------------
            # CHECK UPDATE
            # ----------------------------------------------

            if cur.rowcount == 0:

                conn.rollback()
                conn.close()

                clear_reset_session()

                flash(
                    "Unable to update password. Account not found.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "auth.forgot_password"
                    )
                )

            conn.commit()

        except Exception as e:

            conn.rollback()
            conn.close()

            print(
                "PASSWORD RESET ERROR:",
                e
            )

            flash(
                "Unable to update password. Please try again.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.new_password"
                )
            )

        conn.close()

        # --------------------------------------------------
        # CLEAR RESET SESSION
        # --------------------------------------------------

        clear_reset_session()

        flash(
            "Password updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "auth.login",
                role=reset_role
            )
        )

    return render_template(
        "new_password.html"
    )
