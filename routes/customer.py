from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import sqlite3
import secrets
from datetime import datetime, timedelta

from config import Config


# ============================================================
# CUSTOMER BLUEPRINT
# ============================================================

customer_bp = Blueprint(
    "customer",
    __name__,
    url_prefix="/customer"
)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ============================================================
# CUSTOMER AUTH HELPERS
# ============================================================

def is_customer_logged_in():
    return session.get("customer_id") is not None


def current_customer():

    customer_id = session.get("customer_id")

    if not customer_id:
        return None

    conn = get_db()

    try:

        customer = conn.execute(
            """
            SELECT *
            FROM customers
            WHERE id = ?
            LIMIT 1
            """,
            (customer_id,)
        ).fetchone()

    except sqlite3.Error as error:

        print("CURRENT CUSTOMER ERROR:", error)

        customer = None

    finally:
        conn.close()

    return customer


def customer_login_required():

    if not is_customer_logged_in():
        return redirect(
            url_for("customer.login")
        )

    return None


# ============================================================
# CUSTOMER INDEX
# ============================================================

@customer_bp.route("/")
def index():

    if is_customer_logged_in():

        return redirect(
            url_for("customer.home")
        )

    return redirect(
        url_for("customer.login")
    )


# ============================================================
# CUSTOMER SIGNUP
# ============================================================

@customer_bp.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if is_customer_logged_in():

        return redirect(
            url_for("customer.home")
        )

    if request.method == "GET":

        return render_template(
            "customer/signup.html"
        )

    fullname = request.form.get(
        "fullname",
        ""
    ).strip()

    mobile = request.form.get(
        "mobile",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not fullname:

        flash(
            "Please enter your full name.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    if not mobile:

        flash(
            "Please enter your mobile number.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    if not mobile.isdigit() or len(mobile) != 10:

        flash(
            "Please enter a valid 10-digit mobile number.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    if not email:

        flash(
            "Please enter your email address.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    if "@" not in email or "." not in email:

        flash(
            "Please enter a valid email address.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    if len(password) < 6:

        flash(
            "Password must contain at least 6 characters.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    if password != confirm_password:

        flash(
            "Passwords do not match.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    conn = get_db()

    try:

        # ----------------------------------------------------
        # CHECK EMAIL
        # ----------------------------------------------------

        existing_email = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE LOWER(email) = ?
            LIMIT 1
            """,
            (email,)
        ).fetchone()

        if existing_email:

            flash(
                "This email is already registered.",
                "error"
            )

            return render_template(
                "customer/signup.html"
            )

        # ----------------------------------------------------
        # CHECK MOBILE
        # ----------------------------------------------------

        existing_mobile = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE mobile = ?
            LIMIT 1
            """,
            (mobile,)
        ).fetchone()

        if existing_mobile:

            flash(
                "This mobile number is already registered.",
                "error"
            )

            return render_template(
                "customer/signup.html"
            )

        # ----------------------------------------------------
        # CUSTOMER ID
        #
        # Example:
        # CUS-7F29A4D1
        # ----------------------------------------------------

        customer_code = (
            "CUS-"
            + secrets.token_hex(4).upper()
        )

        # ----------------------------------------------------
        # PASSWORD HASH
        # ----------------------------------------------------

        password_hash = generate_password_hash(
            password
        )

        # ----------------------------------------------------
        # INSERT
        # ----------------------------------------------------

        cursor = conn.execute(
            """
            INSERT INTO customers
            (
                customer_id,
                fullname,
                email,
                mobile,
                password
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                customer_code,
                fullname,
                email,
                mobile,
                password_hash
            )
        )

        customer_id = cursor.lastrowid

        conn.commit()

    except sqlite3.IntegrityError as error:

        conn.rollback()

        print(
            "CUSTOMER SIGNUP INTEGRITY ERROR:",
            error
        )

        flash(
            "Account could not be created. "
            "The email, mobile number or customer ID may already exist.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "CUSTOMER SIGNUP DATABASE ERROR:",
            error
        )

        flash(
            "Account could not be created.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    finally:

        conn.close()

    # --------------------------------------------------------
    # LOGIN CUSTOMER
    # --------------------------------------------------------

    session.clear()

    session["customer_id"] = customer_id
    session["customer_code"] = customer_code
    session["customer_name"] = fullname
    session["customer_email"] = email
    session["customer_mobile"] = mobile

    flash(
        "Account created successfully.",
        "success"
    )

    return redirect(
        url_for("customer.home")
    )


# ============================================================
# CUSTOMER LOGIN
# ============================================================

@customer_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if is_customer_logged_in():

        return redirect(
            url_for("customer.home")
        )

    if request.method == "GET":

        return render_template(
            "customer/login.html"
        )

    login_value = request.form.get(
        "login",
        ""
    ).strip()

    if not login_value:

        # Some login forms use email instead
        login_value = request.form.get(
            "email",
            ""
        ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if not login_value:

        flash(
            "Enter your email or mobile number.",
            "error"
        )

        return render_template(
            "customer/login.html"
        )

    if not password:

        flash(
            "Enter your password.",
            "error"
        )

        return render_template(
            "customer/login.html"
        )

    conn = get_db()

    try:

        customer = conn.execute(
            """
            SELECT *
            FROM customers
            WHERE LOWER(email) = ?
               OR mobile = ?
               OR customer_id = ?
            LIMIT 1
            """,
            (
                login_value.lower(),
                login_value,
                login_value
            )
        ).fetchone()

    except sqlite3.Error as error:

        print(
            "CUSTOMER LOGIN ERROR:",
            error
        )

        customer = None

    finally:

        conn.close()

    if not customer:

        flash(
            "Invalid email, mobile number or password.",
            "error"
        )

        return render_template(
            "customer/login.html"
        )

    try:

        valid_password = check_password_hash(
            customer["password"],
            password
        )

    except Exception as error:

        print(
            "PASSWORD CHECK ERROR:",
            error
        )

        valid_password = False

    if not valid_password:

        flash(
            "Invalid email, mobile number or password.",
            "error"
        )

        return render_template(
            "customer/login.html"
        )

    # --------------------------------------------------------
    # CUSTOMER SESSION
    # --------------------------------------------------------

    session.clear()

    session["customer_id"] = customer["id"]

    if "customer_id" in customer.keys():
        session["customer_code"] = customer["customer_id"]

    session["customer_name"] = (
        customer["fullname"]
    )

    session["customer_email"] = (
        customer["email"]
    )

    session["customer_mobile"] = (
        customer["mobile"]
    )

    flash(
        "Login successful.",
        "success"
    )

    return redirect(
        url_for("customer.home")
    )


# ============================================================
# CUSTOMER LOGOUT
# ============================================================

@customer_bp.route("/logout")
def logout():

    # Completely remove customer session
    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    # IMPORTANT:
    # Customer logout NEVER goes to worker login.
    return redirect(
        url_for("customer.login")
    )


# ============================================================
# CUSTOMER HOME
# ============================================================

@customer_bp.route("/home")
def home():

    required = customer_login_required()

    if required:
        return required

    customer = current_customer()

    if not customer:

        session.clear()

        return redirect(
            url_for("customer.login")
        )

    return render_template(
        "customer/home.html",
        customer=customer
    )


# ============================================================
# SERVICE DETAILS
# ============================================================

@customer_bp.route("/service-details")
def service_details():

    required = customer_login_required()

    if required:
        return required

    category = request.args.get(
        "category",
        ""
    ).strip()

    if not category:

        return redirect(
            url_for("customer.home")
        )

    return render_template(
        "customer/service_details.html",
        category=category
    )


# ============================================================
# BOOKING
#
# Both URLs work:
#
# /customer/booking
# /customer/bookings
# ============================================================

@customer_bp.route("/booking")
def booking():

    required = customer_login_required()

    if required:
        return required

    customer_id = session.get(
        "customer_id"
    )

    conn = get_db()

    try:

        bookings = conn.execute(
            """
            SELECT *
            FROM bookings
            WHERE customer_id = ?
            ORDER BY id DESC
            """,
            (customer_id,)
        ).fetchall()

    except sqlite3.Error as error:

        print(
            "CUSTOMER BOOKING ERROR:",
            error
        )

        bookings = []

    finally:

        conn.close()

    return render_template(
        "customer/bookings.html",
        bookings=bookings
    )


@customer_bp.route("/bookings")
def bookings():

    return redirect(
        url_for("customer.booking")
    )


# ============================================================
# BOOKING DETAILS
#
# Supports:
#
# /customer/booking-details?id=1
# /customer/booking-details?id=WM-240921
# /customer/booking-details?booking_id=1
# ============================================================

@customer_bp.route("/booking-details")
def booking_details_query():

    required = customer_login_required()

    if required:
        return required

    booking_value = request.args.get(
        "id",
        ""
    ).strip()

    if not booking_value:

        booking_value = request.args.get(
            "booking_id",
            ""
        ).strip()

    if not booking_value:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("customer.booking")
        )

    customer_id = session.get(
        "customer_id"
    )

    conn = get_db()

    booking = None

    try:

        # ----------------------------------------------------
        # First: numeric database ID
        # ----------------------------------------------------

        if booking_value.isdigit():

            booking = conn.execute(
                """
                SELECT *
                FROM bookings
                WHERE id = ?
                  AND customer_id = ?
                LIMIT 1
                """,
                (
                    int(booking_value),
                    customer_id
                )
            ).fetchone()

        # ----------------------------------------------------
        # Second: booking code
        #
        # This is attempted only if your database has
        # booking_id or booking_code.
        # ----------------------------------------------------

        if booking is None:

            try:

                booking = conn.execute(
                    """
                    SELECT *
                    FROM bookings
                    WHERE customer_id = ?
                      AND (
                            booking_id = ?
                            OR booking_code = ?
                          )
                    LIMIT 1
                    """,
                    (
                        customer_id,
                        booking_value,
                        booking_value
                    )
                ).fetchone()

            except sqlite3.Error:

                # Older database may not have these columns.
                booking = None

    finally:

        conn.close()

    if not booking:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("customer.booking")
        )

    return render_template(
        "customer/booking_details.html",
        booking=booking
    )


# ============================================================
# BOOKING DETAILS BY NUMERIC ID
#
# /customer/booking/1
# ============================================================

@customer_bp.route(
    "/booking/<int:booking_id>"
)
def booking_details_numeric(
    booking_id
):

    required = customer_login_required()

    if required:
        return required

    customer_id = session.get(
        "customer_id"
    )

    conn = get_db()

    try:

        booking = conn.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = ?
              AND customer_id = ?
            LIMIT 1
            """,
            (
                booking_id,
                customer_id
            )
        ).fetchone()

    except sqlite3.Error as error:

        print(
            "BOOKING DETAILS ERROR:",
            error
        )

        booking = None

    finally:

        conn.close()

    if not booking:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("customer.booking")
        )

    return render_template(
        "customer/booking_details.html",
        booking=booking
    )


# ============================================================
# BOOKING SUCCESS
#
# Supports:
#
# /customer/booking-success
# /customer/booking-success?id=1
# /customer/booking-success/1
# ============================================================

@customer_bp.route("/booking-success")
def booking_success_query():

    required = customer_login_required()

    if required:
        return required

    booking_value = request.args.get(
        "id",
        ""
    ).strip()

    if not booking_value:

        booking_value = request.args.get(
            "booking_id",
            ""
        ).strip()

    # --------------------------------------------------------
    # No ID
    # --------------------------------------------------------

    if not booking_value:

        return render_template(
            "customer/booking_success.html",
            booking=None
        )

    customer_id = session.get(
        "customer_id"
    )

    conn = get_db()

    booking = None

    try:

        if booking_value.isdigit():

            booking = conn.execute(
                """
                SELECT *
                FROM bookings
                WHERE id = ?
                  AND customer_id = ?
                LIMIT 1
                """,
                (
                    int(booking_value),
                    customer_id
                )
            ).fetchone()

        else:

            try:

                booking = conn.execute(
                    """
                    SELECT *
                    FROM bookings
                    WHERE customer_id = ?
                      AND (
                            booking_id = ?
                            OR booking_code = ?
                          )
                    LIMIT 1
                    """,
                    (
                        customer_id,
                        booking_value,
                        booking_value
                    )
                ).fetchone()

            except sqlite3.Error:

                booking = None

    finally:

        conn.close()

    return render_template(
        "customer/booking_success.html",
        booking=booking
    )


@customer_bp.route(
    "/booking-success/<int:booking_id>"
)
def booking_success_numeric(
    booking_id
):

    required = customer_login_required()

    if required:
        return required

    customer_id = session.get(
        "customer_id"
    )

    conn = get_db()

    try:

        booking = conn.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = ?
              AND customer_id = ?
            LIMIT 1
            """,
            (
                booking_id,
                customer_id
            )
        ).fetchone()

    except sqlite3.Error as error:

        print(
            "BOOKING SUCCESS ERROR:",
            error
        )

        booking = None

    finally:

        conn.close()

    if not booking:

        return redirect(
            url_for("customer.booking")
        )

    return render_template(
        "customer/booking_success.html",
        booking=booking
    )


# ============================================================
# PROFILE
# ============================================================

@customer_bp.route("/profile")
def profile():

    required = customer_login_required()

    if required:
        return required

    customer = current_customer()

    if not customer:

        session.clear()

        return redirect(
            url_for("customer.login")
        )

    return render_template(
        "customer/profile.html",
        customer=customer
    )


# ============================================================
# EDIT PROFILE
#
# Supports both:
#
# /customer/profile/edit
# /customer/edit-profile
# ============================================================

@customer_bp.route(
    "/profile/edit",
    methods=["GET", "POST"]
)
def edit_profile():

    required = customer_login_required()

    if required:
        return required

    customer = current_customer()

    if not customer:

        session.clear()

        return redirect(
            url_for("customer.login")
        )

    if request.method == "GET":

        return render_template(
            "customer/profile.html",
            customer=customer,
            edit_mode=True
        )

    fullname = request.form.get(
        "fullname",
        ""
    ).strip()

    mobile = request.form.get(
        "mobile",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    if not fullname:

        flash(
            "Name cannot be empty.",
            "error"
        )

        return redirect(
            url_for("customer.profile")
        )

    if not mobile.isdigit() or len(mobile) != 10:

        flash(
            "Please enter a valid mobile number.",
            "error"
        )

        return redirect(
            url_for("customer.profile")
        )

    if "@" not in email or "." not in email:

        flash(
            "Please enter a valid email.",
            "error"
        )

        return redirect(
            url_for("customer.profile")
        )

    customer_id = session.get(
        "customer_id"
    )

    conn = get_db()

    try:

        duplicate_email = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE LOWER(email) = ?
              AND id != ?
            LIMIT 1
            """,
            (
                email,
                customer_id
            )
        ).fetchone()

        if duplicate_email:

            flash(
                "This email is already in use.",
                "error"
            )

            return redirect(
                url_for("customer.profile")
            )

        duplicate_mobile = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE mobile = ?
              AND id != ?
            LIMIT 1
            """,
            (
                mobile,
                customer_id
            )
        ).fetchone()

        if duplicate_mobile:

            flash(
                "This mobile number is already in use.",
                "error"
            )

            return redirect(
                url_for("customer.profile")
            )

        conn.execute(
            """
            UPDATE customers
            SET
                fullname = ?,
                email = ?,
                mobile = ?
            WHERE id = ?
            """,
            (
                fullname,
                email,
                mobile,
                customer_id
            )
        )

        conn.commit()

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "PROFILE UPDATE ERROR:",
            error
        )

        flash(
            "Profile could not be updated.",
            "error"
        )

        return redirect(
            url_for("customer.profile")
        )

    finally:

        conn.close()

    session["customer_name"] = fullname
    session["customer_email"] = email
    session["customer_mobile"] = mobile

    flash(
        "Profile updated successfully.",
        "success"
    )

    return redirect(
        url_for("customer.profile")
    )


@customer_bp.route(
    "/edit-profile",
    methods=["GET", "POST"]
)
def edit_profile_alias():

    if request.method == "GET":

        return redirect(
            url_for("customer.edit_profile")
        )

    # POST ko bhi same profile edit route par bhejna
    return redirect(
        url_for("customer.edit_profile")
    )


# ============================================================
# LOCATION
# ============================================================

@customer_bp.route(
    "/location",
    methods=["GET", "POST"]
)
def location():

    required = customer_login_required()

    if required:
        return required

    if request.method == "POST":

        location_value = request.form.get(
            "location",
            ""
        ).strip()

        if location_value:

            session["customer_location"] = (
                location_value
            )

            flash(
                "Location saved successfully.",
                "success"
            )

        return redirect(
            url_for("customer.location")
        )

    saved_location = session.get(
        "customer_location",
        ""
    )

    return render_template(
        "customer/location.html",
        location=saved_location
    )


# ============================================================
# ADDRESS
# ============================================================

@customer_bp.route(
    "/address",
    methods=["GET", "POST"]
)
def address():

    required = customer_login_required()

    if required:
        return required

    if request.method == "POST":

        address_value = request.form.get(
            "address",
            ""
        ).strip()

        if address_value:

            session["customer_address"] = (
                address_value
            )

            flash(
                "Address saved successfully.",
                "success"
            )

        return redirect(
            url_for("customer.address")
        )

    saved_address = session.get(
        "customer_address",
        ""
    )

    return render_template(
        "customer/address.html",
        address=saved_address
    )


# ============================================================
# PAYMENT
#
# Both:
#
# /customer/payment
# /customer/payments
# ============================================================

@customer_bp.route("/payment")
def payment():

    required = customer_login_required()

    if required:
        return required

    return render_template(
        "customer/payment.html"
    )


@customer_bp.route("/payments")
def payments():

    return redirect(
        url_for("customer.payment")
    )


# ============================================================
# FORGOT PASSWORD
# ============================================================

@customer_bp.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if is_customer_logged_in():

        return redirect(
            url_for("customer.home")
        )

    if request.method == "GET":

        return render_template(
            "customer/forgot_password.html"
        )

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    if not email:

        flash(
            "Enter your email address.",
            "error"
        )

        return render_template(
            "customer/forgot_password.html"
        )

    conn = get_db()

    try:

        customer = conn.execute(
            """
            SELECT id, fullname, email
            FROM customers
            WHERE LOWER(email) = ?
            LIMIT 1
            """,
            (email,)
        ).fetchone()

    except sqlite3.Error as error:

        print(
            "FORGOT PASSWORD ERROR:",
            error
        )

        customer = None

    finally:

        conn.close()

    if not customer:

        flash(
            "If the email is registered, an OTP will be generated.",
            "success"
        )

        return render_template(
            "customer/forgot_password.html"
        )

    # --------------------------------------------------------
    # GENERATE OTP
    # --------------------------------------------------------

    otp = str(
        secrets.randbelow(900000) + 100000
    )

    expires_at = (
        datetime.now()
        + timedelta(minutes=10)
    )

    session["customer_reset_email"] = email

    session["customer_reset_otp"] = otp

    session["customer_reset_expires"] = (
        expires_at.timestamp()
    )

    # Development mode
    print()
    print("=" * 60)
    print("CUSTOMER PASSWORD RESET")
    print("EMAIL:", email)
    print("OTP:", otp)
    print("VALID FOR: 10 MINUTES")
    print("=" * 60)
    print()

    flash(
        "OTP generated. Check the terminal.",
        "success"
    )

    return redirect(
        url_for("customer.verify")
    )


# ============================================================
# VERIFY OTP
# ============================================================

@customer_bp.route(
    "/verify",
    methods=["GET", "POST"]
)
def verify():

    if is_customer_logged_in():

        return redirect(
            url_for("customer.home")
        )

    if not session.get(
        "customer_reset_email"
    ):

        return redirect(
            url_for("customer.forgot_password")
        )

    if request.method == "GET":

        return render_template(
            "customer/verify.html"
        )

    entered_otp = request.form.get(
        "otp",
        ""
    ).strip()

    saved_otp = session.get(
        "customer_reset_otp"
    )

    expires = session.get(
        "customer_reset_expires"
    )

    if not saved_otp or not expires:

        flash(
            "OTP expired. Request a new OTP.",
            "error"
        )

        return redirect(
            url_for("customer.forgot_password")
        )

    if datetime.now().timestamp() > float(expires):

        session.pop(
            "customer_reset_otp",
            None
        )

        session.pop(
            "customer_reset_expires",
            None
        )

        flash(
            "OTP expired. Request a new OTP.",
            "error"
        )

        return redirect(
            url_for("customer.forgot_password")
        )

    if entered_otp != saved_otp:

        flash(
            "Invalid OTP.",
            "error"
        )

        return render_template(
            "customer/verify.html"
        )

    session["customer_reset_verified"] = True

    session.pop(
        "customer_reset_otp",
        None
    )

    session.pop(
        "customer_reset_expires",
        None
    )

    return redirect(
        url_for("customer.reset_password")
    )


# ============================================================
# RESET PASSWORD
# ============================================================

@customer_bp.route(
    "/reset-password",
    methods=["GET", "POST"]
)
def reset_password():

    if is_customer_logged_in():

        return redirect(
            url_for("customer.home")
        )

    if not session.get(
        "customer_reset_verified"
    ):

        return redirect(
            url_for("customer.forgot_password")
        )

    email = session.get(
        "customer_reset_email"
    )

    if not email:

        return redirect(
            url_for("customer.forgot_password")
        )

    if request.method == "GET":

        return render_template(
            "customer/reset_password.html"
        )

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    if len(password) < 6:

        flash(
            "Password must contain at least 6 characters.",
            "error"
        )

        return render_template(
            "customer/reset_password.html"
        )

    if password != confirm_password:

        flash(
            "Passwords do not match.",
            "error"
        )

        return render_template(
            "customer/reset_password.html"
        )

    password_hash = generate_password_hash(
        password
    )

    conn = get_db()

    try:

        cursor = conn.execute(
            """
            UPDATE customers
            SET password = ?
            WHERE LOWER(email) = ?
            """,
            (
                password_hash,
                email
            )
        )

        if cursor.rowcount == 0:

            conn.rollback()

            flash(
                "Password could not be reset.",
                "error"
            )

            return redirect(
                url_for("customer.forgot_password")
            )

        conn.commit()

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "RESET PASSWORD ERROR:",
            error
        )

        flash(
            "Password could not be reset.",
            "error"
        )

        return redirect(
            url_for("customer.forgot_password")
        )

    finally:

        conn.close()

    # --------------------------------------------------------
    # CLEAR RESET SESSION
    # --------------------------------------------------------

    session.pop(
        "customer_reset_email",
        None
    )

    session.pop(
        "customer_reset_verified",
        None
    )

    session.pop(
        "customer_reset_otp",
        None
    )

    session.pop(
        "customer_reset_expires",
        None
    )

    flash(
        "Password reset successfully.",
        "success"
    )

    return redirect(
        url_for("customer.login")
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================

@customer_bp.route(
    "/change-password",
    methods=["GET", "POST"]
)
def change_password():

    required = customer_login_required()

    if required:
        return required

    if request.method == "GET":

        return render_template(
            "customer/change_password.html"
        )

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

    customer = current_customer()

    if not customer:

        session.clear()

        return redirect(
            url_for("customer.login")
        )

    try:

        valid_current = check_password_hash(
            customer["password"],
            current_password
        )

    except Exception:

        valid_current = False

    if not valid_current:

        flash(
            "Current password is incorrect.",
            "error"
        )

        return render_template(
            "customer/change_password.html"
        )

    if len(new_password) < 6:

        flash(
            "New password must contain at least 6 characters.",
            "error"
        )

        return render_template(
            "customer/change_password.html"
        )

    if new_password != confirm_password:

        flash(
            "Passwords do not match.",
            "error"
        )

        return render_template(
            "customer/change_password.html"
        )

    password_hash = generate_password_hash(
        new_password
    )

    conn = get_db()

    try:

        conn.execute(
            """
            UPDATE customers
            SET password = ?
            WHERE id = ?
            """,
            (
                password_hash,
                customer["id"]
            )
        )

        conn.commit()

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "CHANGE PASSWORD ERROR:",
            error
        )

        flash(
            "Password could not be changed.",
            "error"
        )

        return render_template(
            "customer/change_password.html"
        )

    finally:

        conn.close()

    flash(
        "Password changed successfully.",
        "success"
    )

    return redirect(
        url_for("customer.profile")
    )
