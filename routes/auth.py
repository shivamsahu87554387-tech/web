import random

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


# =====================================
# Splash
# =====================================

@auth_bp.route("/")
def splash():

    return render_template(
        "splash.html"
    )


# =====================================
# Choose Role
# =====================================

@auth_bp.route("/choose-role")
def choose_role():

    return render_template(
        "choose_role.html"
    )


# =====================================
# Login
# =====================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    role = request.args.get(
        "role",
        "worker"
    )

    if request.method == "POST":

        user_id = request.form["user_id"].strip()
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        # =====================================
        # WORKER LOGIN
        # =====================================

        if role == "worker":

            cur.execute("""
                SELECT *
                FROM workers
                WHERE worker_id=?
            """, (user_id,))

        # =====================================
        # PARTNER LOGIN
        # =====================================

        elif role == "partner":

            cur.execute("""
                SELECT *
                FROM partners
                WHERE partner_id=?
            """, (user_id,))

        else:

            conn.close()

            flash(
                "Invalid account type.",
                "danger"
            )

            return redirect(
                url_for("auth.login")
            )

        user = cur.fetchone()

        conn.close()

        # =====================================
        # USER NOT FOUND
        # =====================================

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

        # =====================================
        # CHECK ACCOUNT STATUS
        # =====================================

        status = user["status"] or "active"

        if status.lower() == "suspended":

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

        # =====================================
        # PASSWORD CHECK
        # =====================================

        if not check_password_hash(
            user["password"],
            password
        ):

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

        # =====================================
        # WORKER LOGIN SUCCESS
        # =====================================

        if role == "worker":

            session.clear()

            session["user_id"] = user["worker_id"]
            session["role"] = "worker"

            flash(
                "Login Successful.",
                "success"
            )

            return redirect(
                "/worker/home"
            )

        # =====================================
        # PARTNER LOGIN SUCCESS
        # =====================================

        else:

            session.clear()

            session["user_id"] = user["partner_id"]
            session["role"] = "partner"

            flash(
                "Login Successful.",
                "success"
            )

            return redirect(
                "/partner/home"
            )


    # =====================================
    # LOGIN PAGE
    # =====================================

    return render_template(
        "login.html",
        role=role
    )


# =====================================
# Signup
# =====================================

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():

    role = request.args.get(
        "role",
        "worker"
    )

    if request.method == "POST":

        fullname = request.form["fullname"].strip()
        email = request.form["email"].strip()
        mobile = request.form["mobile"].strip()

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # =====================================
        # PASSWORD CONFIRMATION
        # =====================================

        if password != confirm_password:

            flash(
                "Password and Confirm Password do not match.",
                "danger"
            )

            return redirect(request.url)

        password = generate_password_hash(password)

        conn = get_db()
        cur = conn.cursor()

        # =====================================
        # DUPLICATE EMAIL
        # =====================================

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

            return redirect(request.url)

        # =====================================
        # DUPLICATE MOBILE
        # =====================================

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

            return redirect(request.url)


        # =====================================
        # WORKER SIGNUP
        # =====================================

        if role == "worker":

            worker_id = generate_worker_id()

            referred_by = request.form.get(
                "referral_code",
                "WM00000"
            ).strip()

            if referred_by == "":

                referred_by = "WM00000"

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
                    password,
                    referred_by
                )
            )

            # =====================================
            # LINK WORKER WITH PARTNER
            # =====================================

            cur.execute(
                """
                SELECT partner_id
                FROM partners
                WHERE referral_code=?
                """,
                (referred_by,)
            )

            partner = cur.fetchone()

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
            conn.close()

            return render_template(
                "account_created.html",
                account_id=worker_id,
                role="worker"
            )


        # =====================================
        # PARTNER SIGNUP
        # =====================================

        partner_id = generate_partner_id()

        referral_code = generate_referral_code()

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
                password
            )
        )

        conn.commit()
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


# =====================================
# Logout
# =====================================

@auth_bp.route("/logout")
def logout():

    session.clear()

    flash(
        "Logged out successfully.",
        "success"
    )

    return redirect(
        url_for("auth.login")
    )


# =====================================
# Forgot Password
# =====================================

@auth_bp.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form["email"].strip()

        conn = get_db()
        cur = conn.cursor()

        # =====================================
        # WORKER CHECK
        # =====================================

        cur.execute(
            """
            SELECT worker_id
            FROM workers
            WHERE email=?
            """,
            (email,)
        )

        user = cur.fetchone()

        role = "worker"


        # =====================================
        # PARTNER CHECK
        # =====================================

        if not user:

            cur.execute(
                """
                SELECT partner_id
                FROM partners
                WHERE email=?
                """,
                (email,)
            )

            user = cur.fetchone()

            role = "partner"

        conn.close()


        # =====================================
        # EMAIL NOT FOUND
        # =====================================

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


        # =====================================
        # GENERATE OTP
        # =====================================

        otp = str(
            random.randint(
                100000,
                999999
            )
        )

        session["reset_email"] = email
        session["reset_role"] = role
        session["reset_otp"] = otp


        # =====================================
        # SEND OTP
        # =====================================

        try:

            send_otp(
                email,
                otp
            )

            flash(
                "OTP has been sent to your email.",
                "success"
            )

        except Exception as e:

            print(e)

            flash(
                "Failed to send OTP.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.forgot_password"
                )
            )


        return redirect(
            url_for(
                "auth.verify_otp"
            )
        )


    return render_template(
        "forgot_password.html"
    )


# =====================================
# Verify OTP
# =====================================

@auth_bp.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    if request.method == "POST":

        otp = request.form["otp"].strip()

        if otp == session.get("reset_otp"):

            flash(
                "OTP Verified Successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "auth.new_password"
                )
            )

        flash(
            "Invalid OTP.",
            "danger"
        )

        return redirect(
            url_for(
                "auth.verify_otp"
            )
        )


    return render_template(
        "verify_otp.html"
    )


# =====================================
# New Password
# =====================================

@auth_bp.route(
    "/new-password",
    methods=["GET", "POST"]
)
def new_password():

    if request.method == "POST":

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]


        # =====================================
        # PASSWORD MATCH
        # =====================================

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


        password = generate_password_hash(
            password
        )

        conn = get_db()
        cur = conn.cursor()


        # =====================================
        # WORKER PASSWORD UPDATE
        # =====================================

        if session["reset_role"] == "worker":

            cur.execute(
                """
                UPDATE workers
                SET password=?
                WHERE email=?
                """,
                (
                    password,
                    session["reset_email"]
                )
            )


        # =====================================
        # PARTNER PASSWORD UPDATE
        # =====================================

        else:

            cur.execute(
                """
                UPDATE partners
                SET password=?
                WHERE email=?
                """,
                (
                    password,
                    session["reset_email"]
                )
            )


        conn.commit()
        conn.close()


        # =====================================
        # CLEAR RESET SESSION
        # =====================================

        session.pop(
            "reset_email",
            None
        )

        session.pop(
            "reset_role",
            None
        )

        session.pop(
            "reset_otp",
            None
        )


        flash(
            "Password updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )


    return render_template(
        "new_password.html"
    )
