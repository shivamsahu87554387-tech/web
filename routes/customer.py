# =========================================================
# WORKMITRA - CUSTOMER SYSTEM
# customer.py
# PART 1
# =========================================================


# =========================================================
# IMPORTS
# =========================================================

import os
import random
import sqlite3

from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    current_app
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# =========================================================
# BLUEPRINT
# =========================================================

customer = Blueprint(
    "customer",
    __name__,
    url_prefix="/customer"
)


# =========================================================
# CONFIGURATION
# =========================================================

DATABASE = "database.db"

UPLOAD_FOLDER = "static/uploads/customer"

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    conn = sqlite3.connect(
        DATABASE
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# CREATE CUSTOMER TABLES
# =========================================================

def create_customer_tables():

    conn = get_db()

    cursor = conn.cursor()


    # =====================================================
    # CUSTOMERS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_id TEXT UNIQUE NOT NULL,

            fullname TEXT NOT NULL,

            mobile TEXT UNIQUE NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            email_verified INTEGER DEFAULT 0,

            profile_photo TEXT,

            address TEXT,

            city TEXT,

            state TEXT,

            pincode TEXT,

            latitude REAL,

            longitude REAL,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # =====================================================
    # CUSTOMER OTP TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_otps (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            email TEXT NOT NULL,

            otp TEXT NOT NULL,

            purpose TEXT NOT NULL,

            expires_at TEXT NOT NULL,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # =====================================================
    # SERVICES TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE NOT NULL,

            icon TEXT,

            description TEXT,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # =====================================================
    # BOOKINGS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            booking_id TEXT UNIQUE NOT NULL,

            customer_id INTEGER NOT NULL,

            service_id INTEGER,

            category TEXT NOT NULL,

            description TEXT,

            address TEXT NOT NULL,

            city TEXT,

            state TEXT,

            pincode TEXT,

            latitude REAL,

            longitude REAL,

            preferred_date TEXT,

            preferred_time TEXT,


            service_charge REAL DEFAULT 0,

            platform_fee REAL DEFAULT 0,

            total_amount REAL DEFAULT 0,


            payment_method TEXT,

            payment_id TEXT,

            payment_status TEXT
            DEFAULT 'pending',


            worker_id INTEGER,


            booking_status TEXT
            DEFAULT 'pending',


            cancellation_reason TEXT,


            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,


            updated_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # =====================================================
    # REVIEWS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            booking_id INTEGER UNIQUE NOT NULL,

            customer_id INTEGER NOT NULL,

            worker_id INTEGER,

            rating INTEGER NOT NULL,

            review TEXT,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # =====================================================
    # DEFAULT SERVICES
    # =====================================================

    default_services = [

        (
            "Electrician",
            "⚡",
            "Electrical repair and installation"
        ),

        (
            "Plumber",
            "🔧",
            "Plumbing and water related services"
        ),

        (
            "Carpenter",
            "🪚",
            "Furniture and wood work services"
        ),

        (
            "Painter",
            "🎨",
            "Home and office painting services"
        ),

        (
            "AC Repair",
            "❄️",
            "Air conditioner repair and service"
        ),

        (
            "Appliance Repair",
            "🛠️",
            "Home appliance repair services"
        ),

        (
            "Cleaning",
            "🧹",
            "Home and office cleaning services"
        ),

        (
            "Gardening",
            "🌿",
            "Garden maintenance services"
        )

    ]


    for service in default_services:

        cursor.execute(
            """
            INSERT OR IGNORE INTO services
            (
                name,
                icon,
                description
            )

            VALUES (?, ?, ?)
            """,
            service
        )


    # =====================================================
    # CREATE UPLOAD FOLDER
    # =====================================================

    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True
    )


    conn.commit()

    conn.close()


# =========================================================
# GENERATE CUSTOMER ID
# =========================================================

def generate_customer_id():

    conn = get_db()


    while True:

        customer_id = (

            "WM-CUS-"

            + str(
                random.randint(
                    100000,
                    999999
                )
            )

        )


        existing = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE customer_id = ?
            """,
            (customer_id,)
        ).fetchone()


        if not existing:

            conn.close()

            return customer_id


# =========================================================
# GENERATE BOOKING ID
# =========================================================

def generate_booking_id():

    conn = get_db()


    while True:

        booking_id = (

            "WM-"

            + datetime.now().strftime(
                "%Y%m%d"
            )

            + "-"

            + str(
                random.randint(
                    10000,
                    99999
                )
            )

        )


        existing = conn.execute(
            """
            SELECT id
            FROM bookings
            WHERE booking_id = ?
            """,
            (booking_id,)
        ).fetchone()


        if not existing:

            conn.close()

            return booking_id


# =========================================================
# GENERATE PAYMENT ID
# =========================================================

def generate_payment_id():

    return (

        "PAY-"

        + datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )

        + "-"

        + str(
            random.randint(
                100,
                999
            )
        )

    )


# =========================================================
# ALLOWED FILE CHECK
# =========================================================

def allowed_file(filename):

    if "." not in filename:

        return False


    extension = (

        filename
        .rsplit(".", 1)[1]
        .lower()

    )


    return extension in ALLOWED_EXTENSIONS


# =========================================================
# CUSTOMER LOGIN REQUIRED
# =========================================================

def customer_login_required(function):

    @wraps(function)

    def decorated_function(
        *args,
        **kwargs
    ):


        if "customer_id" not in session:

            flash(
                "Please login first.",
                "warning"
            )


            return redirect(
                url_for(
                    "customer.login"
                )
            )


        return function(
            *args,
            **kwargs
        )


    return decorated_function


# =========================================================
# GET CURRENT CUSTOMER
# =========================================================

def get_current_customer():

    customer_id = session.get(
        "customer_id"
    )


    if not customer_id:

        return None


    conn = get_db()


    customer_data = conn.execute(
        """
        SELECT *

        FROM customers

        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()


    conn.close()


    return customer_data


# =========================================================
# GENERATE OTP
# =========================================================

def generate_otp():

    return str(

        random.randint(
            100000,
            999999
        )

    )


# =========================================================
# SAVE OTP
# =========================================================

def save_otp(
    email,
    purpose
):

    otp = generate_otp()


    expires_at = (

        datetime.now()

        + timedelta(
            minutes=10
        )

    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    conn = get_db()


    # =============================================
    # DELETE OLD OTP
    # =============================================

    conn.execute(
        """
        DELETE FROM customer_otps

        WHERE email = ?

        AND purpose = ?
        """,
        (
            email,
            purpose
        )
    )


    # =============================================
    # INSERT NEW OTP
    # =============================================

    conn.execute(
        """
        INSERT INTO customer_otps
        (
            email,
            otp,
            purpose,
            expires_at
        )

        VALUES (?, ?, ?, ?)
        """,
        (
            email,
            otp,
            purpose,
            expires_at
        )
    )


    conn.commit()

    conn.close()


    return otp


# =========================================================
# VERIFY OTP
# =========================================================

def verify_otp(
    email,
    entered_otp,
    purpose
):

    conn = get_db()


    otp_data = conn.execute(
        """
        SELECT *

        FROM customer_otps

        WHERE email = ?

        AND purpose = ?

        ORDER BY id DESC

        LIMIT 1
        """,
        (
            email,
            purpose
        )
    ).fetchone()


    conn.close()


    # =============================================
    # OTP NOT FOUND
    # =============================================

    if not otp_data:

        return False


    # =============================================
    # WRONG OTP
    # =============================================

    if otp_data["otp"] != entered_otp:

        return False


    # =============================================
    # CHECK EXPIRY
    # =============================================

    expires_at = datetime.strptime(

        otp_data["expires_at"],

        "%Y-%m-%d %H:%M:%S"

    )


    if datetime.now() > expires_at:

        return False


    return True


# =========================================================
# DELETE OTP
# =========================================================

def delete_otp(
    email,
    purpose
):

    conn = get_db()


    conn.execute(
        """
        DELETE FROM customer_otps

        WHERE email = ?

        AND purpose = ?
        """,
        (
            email,
            purpose
        )
    )


    conn.commit()

    conn.close()


# =========================================================
# SEND EMAIL OTP
# =========================================================

def send_email_otp(
    email,
    otp,
    purpose
):

    """
    IMPORTANT:

    Abhi testing mode hai.

    OTP terminal / console mein show hoga.

    Baad mein Gmail SMTP ya
    proper email service connect karenge.
    """


    print("\n")

    print(
        "======================================"
    )

    print(
        "WORKMITRA CUSTOMER OTP"
    )

    print(
        "======================================"
    )

    print(
        "EMAIL:",
        email
    )

    print(
        "PURPOSE:",
        purpose
    )

    print(
        "OTP:",
        otp
    )

    print(
        "======================================"
    )

    print("\n")


    return True


# =========================================================
# START OTP VERIFICATION SESSION
# =========================================================

def start_verification_session(
    email,
    purpose
):

    otp = save_otp(
        email,
        purpose
    )


    send_email_otp(
        email,
        otp,
        purpose
    )


    session["verify_email"] = email

    session["verify_purpose"] = purpose


# =========================================================
# CLEAR VERIFICATION SESSION
# =========================================================

def clear_verification_session():

    session.pop(
        "verify_email",
        None
    )


    session.pop(
        "verify_purpose",
        None
    )


    session.pop(
        "otp_verified",
        None
    )


# =========================================================
# GET SERVICE BASE PRICE
# =========================================================

def get_service_base_price(category):

    prices = {

        "Electrician": 199,

        "Plumber": 199,

        "Carpenter": 249,

        "Painter": 299,

        "AC Repair": 299,

        "Appliance Repair": 249,

        "Cleaning": 299,

        "Gardening": 249

    }


    return prices.get(
        category,
        199
    )


# =========================================================
# CLEAR TEMP BOOKING SESSION
# =========================================================

def clear_booking_session():

    booking_keys = [

        "selected_service",

        "selected_service_icon",

        "booking_address",

        "booking_city",

        "booking_state",

        "booking_pincode",

        "booking_latitude",

        "booking_longitude",

        "booking_description",

        "preferred_date",

        "preferred_time",

        "booking_service_charge",

        "booking_platform_fee",

        "booking_total_amount"

    ]


    for key in booking_keys:

        session.pop(
            key,
            None
        )


# =========================================================
# PART 1 END
# =========================================================

# =========================================================
# WORKMITRA - CUSTOMER SYSTEM
# customer.py
# PART 2
#
# AUTHENTICATION
# SIGNUP
# LOGIN
# EMAIL OTP
# FORGOT PASSWORD
# CHANGE PASSWORD
# =========================================================


# =========================================================
# SIGNUP
# =========================================================

@customer.route(
    "/signup",
    methods=["GET", "POST"]
)

def signup():

    # =============================================
    # ALREADY LOGGED IN
    # =============================================

    if "customer_id" in session:

        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # POST
    # =============================================

    if request.method == "POST":

        fullname = (
            request.form
            .get("fullname", "")
            .strip()
        )


        mobile = (
            request.form
            .get("mobile", "")
            .strip()
        )


        email = (
            request.form
            .get("email", "")
            .strip()
            .lower()
        )


        password = (
            request.form
            .get("password", "")
        )


        confirm_password = (
            request.form
            .get(
                "confirm_password",
                ""
            )
        )


        terms = request.form.get(
            "terms"
        )


        # =========================================
        # VALIDATE NAME
        # =========================================

        if len(fullname) < 2:

            flash(
                "Please enter your full name.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.signup"
                )
            )


        # =========================================
        # VALIDATE MOBILE
        # =========================================

        if (

            not mobile.isdigit()

            or

            len(mobile) != 10

        ):

            flash(
                "Please enter a valid 10 digit mobile number.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.signup"
                )
            )


        # =========================================
        # VALIDATE EMAIL
        # =========================================

        if (

            not email

            or

            "@" not in email

            or

            "." not in email

        ):

            flash(
                "Please enter a valid email address.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.signup"
                )
            )


        # =========================================
        # PASSWORD LENGTH
        # =========================================

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.signup"
                )
            )


        # =========================================
        # PASSWORD MATCH
        # =========================================

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.signup"
                )
            )


        # =========================================
        # TERMS
        # =========================================

        if not terms:

            flash(
                "Please accept Terms & Conditions.",
                "warning"
            )

            return redirect(
                url_for(
                    "customer.signup"
                )
            )


        # =========================================
        # DATABASE CHECK
        # =========================================

        conn = get_db()


        existing_email = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        existing_mobile = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE mobile = ?
            """,
            (mobile,)
        ).fetchone()


        # =========================================
        # EMAIL ALREADY EXISTS
        # =========================================

        if existing_email:

            conn.close()


            flash(
                "This email is already registered. Please login.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.login"
                )
            )


        # =========================================
        # MOBILE ALREADY EXISTS
        # =========================================

        if existing_mobile:

            conn.close()


            flash(
                "This mobile number is already registered.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.signup"
                )
            )


        # =========================================
        # CREATE CUSTOMER
        # =========================================

        customer_id = (
            generate_customer_id()
        )


        hashed_password = (
            generate_password_hash(
                password
            )
        )


        conn.execute(
            """
            INSERT INTO customers
            (
                customer_id,
                fullname,
                mobile,
                email,
                password,
                email_verified
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                fullname,
                mobile,
                email,
                hashed_password,
                0
            )
        )


        conn.commit()

        conn.close()


        # =========================================
        # SEND OTP
        # =========================================

        start_verification_session(
            email,
            "signup_verify"
        )


        flash(
            "Verification code has been sent to your email.",
            "success"
        )


        return redirect(
            url_for(
                "customer.verify"
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(
        "customer/signup.html"
    )


# =========================================================
# VERIFY OTP
#
# ONE ROUTE FOR:
#
# signup_verify
# forgot_password
# change_password
# =========================================================

@customer.route(
    "/verify",
    methods=["GET", "POST"]
)

def verify():

    email = session.get(
        "verify_email"
    )


    purpose = session.get(
        "verify_purpose"
    )


    # =============================================
    # VALID SESSION
    # =============================================

    allowed_purposes = [

        "signup_verify",

        "forgot_password",

        "change_password"

    ]


    if (

        not email

        or

        purpose not in allowed_purposes

    ):

        flash(
            "Verification session expired. Please try again.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # POST
    # =============================================

    if request.method == "POST":

        entered_otp = (

            request.form
            .get("otp", "")
            .strip()

        )


        # =========================================
        # OTP VALIDATION
        # =========================================

        if (

            not entered_otp.isdigit()

            or

            len(entered_otp) != 6

        ):

            flash(
                "Please enter a valid 6 digit OTP.",
                "danger"
            )

            return render_template(
                "customer/verify.html",
                email=email
            )


        # =========================================
        # VERIFY OTP
        # =========================================

        valid_otp = verify_otp(

            email,

            entered_otp,

            purpose

        )


        if not valid_otp:

            flash(
                "Invalid or expired verification code.",
                "danger"
            )

            return render_template(
                "customer/verify.html",
                email=email
            )


        # =========================================
        # SIGNUP VERIFY
        # =========================================

        if purpose == "signup_verify":

            conn = get_db()


            conn.execute(
                """
                UPDATE customers

                SET email_verified = 1

                WHERE email = ?
                """,
                (email,)
            )


            conn.commit()


            customer_data = conn.execute(
                """
                SELECT *

                FROM customers

                WHERE email = ?
                """,
                (email,)
            ).fetchone()


            conn.close()


            # DELETE OTP
            delete_otp(
                email,
                purpose
            )


            # CLEAR VERIFY DATA
            session.pop(
                "verify_email",
                None
            )


            session.pop(
                "verify_purpose",
                None
            )


            # LOGIN CUSTOMER
            session["customer_id"] = (

                customer_data[
                    "customer_id"
                ]

            )


            session["fullname"] = (

                customer_data[
                    "fullname"
                ]

            )


            flash(
                "Email verified successfully. Welcome to WorkMitra!",
                "success"
            )


            return redirect(
                url_for(
                    "customer.home"
                )
            )


        # =========================================
        # FORGOT PASSWORD
        # =========================================

        if purpose == "forgot_password":

            session["otp_verified"] = True


            delete_otp(
                email,
                purpose
            )


            flash(
                "OTP verified successfully. You can now reset your password.",
                "success"
            )


            return redirect(
                url_for(
                    "customer.reset_password"
                )
            )


        # =========================================
        # CHANGE PASSWORD
        # =========================================

        if purpose == "change_password":

            session["otp_verified"] = True


            delete_otp(
                email,
                purpose
            )


            flash(
                "OTP verified successfully. You can now set a new password.",
                "success"
            )


            return redirect(
                url_for(
                    "customer.reset_password"
                )
            )


    # =============================================
    # GET
    # =============================================

    return render_template(
        "customer/verify.html",
        email=email
    )


# =========================================================
# RESEND OTP
# =========================================================

@customer.route(
    "/resend-otp",
    methods=["POST"]
)

def resend_otp():

    email = session.get(
        "verify_email"
    )


    purpose = session.get(
        "verify_purpose"
    )


    # =============================================
    # CHECK SESSION
    # =============================================

    if not email or not purpose:

        flash(
            "Verification session expired.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # NEW OTP
    # =============================================

    start_verification_session(
        email,
        purpose
    )


    flash(
        "A new verification code has been sent.",
        "success"
    )


    return redirect(
        url_for(
            "customer.verify"
        )
    )


# =========================================================
# LOGIN
# =========================================================

@customer.route(
    "/login",
    methods=["GET", "POST"]
)

def login():

    # =============================================
    # ALREADY LOGGED IN
    # =============================================

    if "customer_id" in session:

        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # POST
    # =============================================

    if request.method == "POST":

        email = (

            request.form
            .get("email", "")
            .strip()
            .lower()

        )


        password = (

            request.form
            .get("password", "")

        )


        # =========================================
        # VALIDATION
        # =========================================

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.login"
                )
            )


        # =========================================
        # GET CUSTOMER
        # =========================================

        conn = get_db()


        customer_data = conn.execute(
            """
            SELECT *

            FROM customers

            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        conn.close()


        # =========================================
        # ACCOUNT NOT FOUND
        # =========================================

        if not customer_data:

            flash(
                "Account not found. Please sign up first.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.signup"
                )
            )


        # =========================================
        # CHECK PASSWORD
        # =========================================

        if not check_password_hash(

            customer_data["password"],

            password

        ):

            flash(
                "Incorrect password.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.login"
                )
            )


        # =========================================
        # EMAIL NOT VERIFIED
        # =========================================

        if not customer_data["email_verified"]:

            start_verification_session(
                email,
                "signup_verify"
            )


            flash(
                "Please verify your email first.",
                "warning"
            )


            return redirect(
                url_for(
                    "customer.verify"
                )
            )


        # =========================================
        # CREATE LOGIN SESSION
        # =========================================

        session["customer_id"] = (

            customer_data[
                "customer_id"
            ]

        )


        session["fullname"] = (

            customer_data[
                "fullname"
            ]

        )


        flash(
            "Welcome back!",
            "success"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(
        "customer/login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@customer.route(
    "/logout"
)

def logout():

    session.clear()


    flash(
        "You have been logged out successfully.",
        "success"
    )


    return redirect(
        url_for(
            "customer.login"
        )
    )


# =========================================================
# FORGOT PASSWORD
# =========================================================

@customer.route(
    "/forgot-password",
    methods=["GET", "POST"]
)

def forgot_password():

    # =============================================
    # POST
    # =============================================

    if request.method == "POST":

        email = (

            request.form
            .get("email", "")
            .strip()
            .lower()

        )


        # =========================================
        # VALIDATE
        # =========================================

        if not email:

            flash(
                "Please enter your registered email.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.forgot_password"
                )
            )


        # =========================================
        # CHECK CUSTOMER
        # =========================================

        conn = get_db()


        customer_data = conn.execute(
            """
            SELECT *

            FROM customers

            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        conn.close()


        # =========================================
        # NOT FOUND
        # =========================================

        if not customer_data:

            flash(
                "No account found with this email.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.forgot_password"
                )
            )


        # =========================================
        # SEND OTP
        # =========================================

        start_verification_session(
            email,
            "forgot_password"
        )


        flash(
            "Verification code sent to your registered email.",
            "success"
        )


        return redirect(
            url_for(
                "customer.verify"
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(
        "customer/forgot_password.html"
    )


# =========================================================
# RESET PASSWORD
#
# USED FOR:
#
# FORGOT PASSWORD
# CHANGE PASSWORD
# =========================================================

@customer.route(
    "/reset-password",
    methods=["GET", "POST"]
)

def reset_password():

    email = session.get(
        "verify_email"
    )


    purpose = session.get(
        "verify_purpose"
    )


    otp_verified = session.get(
        "otp_verified"
    )


    # =============================================
    # SECURITY CHECK
    # =============================================

    allowed_purposes = [

        "forgot_password",

        "change_password"

    ]


    if (

        not email

        or

        not otp_verified

        or

        purpose not in allowed_purposes

    ):

        flash(
            "Please verify OTP first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # POST
    # =============================================

    if request.method == "POST":

        password = (

            request.form
            .get("password", "")

        )


        confirm_password = (

            request.form
            .get(
                "confirm_password",
                ""
            )

        )


        # =========================================
        # PASSWORD LENGTH
        # =========================================

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.reset_password"
                )
            )


        # =========================================
        # PASSWORD MATCH
        # =========================================

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.reset_password"
                )
            )


        # =========================================
        # HASH PASSWORD
        # =========================================

        hashed_password = (

            generate_password_hash(
                password
            )

        )


        # =========================================
        # UPDATE DATABASE
        # =========================================

        conn = get_db()


        conn.execute(
            """
            UPDATE customers

            SET password = ?

            WHERE email = ?
            """,
            (
                hashed_password,
                email
            )
        )


        conn.commit()

        conn.close()


        # =========================================
        # CHANGE PASSWORD FLOW
        # =========================================

        if purpose == "change_password":

            clear_verification_session()


            flash(
                "Password changed successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "customer.profile"
                )
            )


        # =========================================
        # FORGOT PASSWORD FLOW
        # =========================================

        clear_verification_session()


        flash(
            "Password reset successfully. Please login.",
            "success"
        )


        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(
        "customer/reset_password.html"
    )


# =========================================================
# CHANGE PASSWORD
#
# PROFILE MENU
# OTP BASED
# =========================================================

@customer.route(
    "/change-password",
    methods=["GET", "POST"]
)

@customer_login_required

def change_password():

    customer_data = (
        get_current_customer()
    )


    # =============================================
    # CUSTOMER CHECK
    # =============================================

    if not customer_data:

        session.clear()


        flash(
            "Session expired. Please login again.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # POST
    #
    # SEND OTP
    # =============================================

    if request.method == "POST":

        email = (
            customer_data["email"]
        )


        # =========================================
        # CLEAR OLD VERIFY SESSION
        # =========================================

        clear_verification_session()


        # =========================================
        # SEND CHANGE PASSWORD OTP
        # =========================================

        start_verification_session(
            email,
            "change_password"
        )


        flash(
            "Verification code sent to your registered email.",
            "success"
        )


        return redirect(
            url_for(
                "customer.verify"
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(
        "customer/change_password.html",
        customer=customer_data
    )


# =========================================================
# PART 2 END
# =========================================================

# =========================================================
# WORKMITRA - CUSTOMER SYSTEM
# customer.py
# PART 3
#
# HOME
# SERVICES
# LOCATION
# SERVICE DETAILS
# BOOKING SUMMARY
# =========================================================


# =========================================================
# CUSTOMER HOME
# =========================================================

@customer.route(
    "/home"
)

@customer_login_required

def home():

    customer_data = (
        get_current_customer()
    )


    if not customer_data:

        session.clear()

        return redirect(
            url_for(
                "customer.login"
            )
        )


    conn = get_db()


    services = conn.execute(
        """
        SELECT *

        FROM services

        WHERE active = 1

        ORDER BY id ASC
        """
    ).fetchall()


    conn.close()


    return render_template(
        "customer/home.html",

        customer=customer_data,

        services=services
    )


# =========================================================
# SELECT SERVICE
# =========================================================

@customer.route(
    "/service/<int:service_id>"
)

@customer_login_required

def select_service(service_id):

    conn = get_db()


    service = conn.execute(
        """
        SELECT *

        FROM services

        WHERE id = ?

        AND active = 1
        """,
        (service_id,)
    ).fetchone()


    conn.close()


    # =============================================
    # SERVICE NOT FOUND
    # =============================================

    if not service:

        flash(
            "Service not found.",
            "danger"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # CLEAR OLD BOOKING DATA
    # =============================================

    clear_booking_session()


    # =============================================
    # SAVE SERVICE IN SESSION
    # =============================================

    session["selected_service_id"] = (
        service["id"]
    )


    session["selected_service"] = (
        service["name"]
    )


    session["selected_service_icon"] = (
        service["icon"]
        or "🛠️"
    )


    # =============================================
    # NEXT PAGE
    # =============================================

    return redirect(
        url_for(
            "customer.location"
        )
    )


# =========================================================
# LOCATION
# =========================================================

@customer.route(
    "/location",
    methods=["GET", "POST"]
)

@customer_login_required

def location():

    # =============================================
    # CHECK SERVICE
    # =============================================

    service_id = session.get(
        "selected_service_id"
    )


    if not service_id:

        flash(
            "Please select a service first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    conn = get_db()


    service = conn.execute(
        """
        SELECT *

        FROM services

        WHERE id = ?

        AND active = 1
        """,
        (service_id,)
    ).fetchone()


    conn.close()


    if not service:

        clear_booking_session()


        flash(
            "Service not found.",
            "danger"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # CURRENT CUSTOMER
    # =============================================

    customer_data = (
        get_current_customer()
    )


    # =============================================
    # POST
    # =============================================

    if request.method == "POST":

        address = (
            request.form
            .get("address", "")
            .strip()
        )


        city = (
            request.form
            .get("city", "")
            .strip()
        )


        state = (
            request.form
            .get("state", "")
            .strip()
        )


        pincode = (
            request.form
            .get("pincode", "")
            .strip()
        )


        latitude = (
            request.form
            .get("latitude", "")
            .strip()
        )


        longitude = (
            request.form
            .get("longitude", "")
            .strip()
        )


        # =========================================
        # VALIDATE ADDRESS
        # =========================================

        if len(address) < 5:

            flash(
                "Please enter a complete address.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.location"
                )
            )


        # =========================================
        # VALIDATE CITY
        # =========================================

        if not city:

            flash(
                "Please enter your city or village.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.location"
                )
            )


        # =========================================
        # VALIDATE STATE
        # =========================================

        if not state:

            flash(
                "Please enter your state.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.location"
                )
            )


        # =========================================
        # VALIDATE PINCODE
        # =========================================

        if (

            not pincode.isdigit()

            or

            len(pincode) != 6

        ):

            flash(
                "Please enter a valid 6 digit pincode.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.location"
                )
            )


        # =========================================
        # CONVERT GPS
        # =========================================

        latitude_value = None

        longitude_value = None


        if latitude:

            try:

                latitude_value = float(
                    latitude
                )

            except ValueError:

                latitude_value = None


        if longitude:

            try:

                longitude_value = float(
                    longitude
                )

            except ValueError:

                longitude_value = None


        # =========================================
        # SAVE LOCATION IN SESSION
        # =========================================

        session["booking_address"] = (
            address
        )


        session["booking_city"] = (
            city
        )


        session["booking_state"] = (
            state
        )


        session["booking_pincode"] = (
            pincode
        )


        session["booking_latitude"] = (
            latitude_value
        )


        session["booking_longitude"] = (
            longitude_value
        )


        # =========================================
        # NEXT PAGE
        # =========================================

        return redirect(
            url_for(
                "customer.service_details"
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(

        "customer/location.html",

        customer=customer_data,

        service=service

    )


# =========================================================
# SERVICE DETAILS
# =========================================================

@customer.route(
    "/service-details",
    methods=["GET", "POST"]
)

@customer_login_required

def service_details():

    # =============================================
    # CHECK SERVICE
    # =============================================

    service_id = session.get(
        "selected_service_id"
    )


    if not service_id:

        flash(
            "Please select a service first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # CHECK LOCATION
    # =============================================

    if not session.get(
        "booking_address"
    ):

        flash(
            "Please add your service location first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.location"
            )
        )


    # =============================================
    # GET SERVICE
    # =============================================

    conn = get_db()


    service = conn.execute(
        """
        SELECT *

        FROM services

        WHERE id = ?

        AND active = 1
        """,
        (service_id,)
    ).fetchone()


    conn.close()


    if not service:

        clear_booking_session()


        flash(
            "Service not found.",
            "danger"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # POST
    # =============================================

    if request.method == "POST":

        description = (
            request.form
            .get("description", "")
            .strip()
        )


        preferred_date = (
            request.form
            .get("preferred_date", "")
            .strip()
        )


        preferred_time = (
            request.form
            .get("preferred_time", "")
            .strip()
        )


        # =========================================
        # VALIDATE DESCRIPTION
        # =========================================

        if len(description) < 5:

            flash(
                "Please describe the work you need.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.service_details"
                )
            )


        # =========================================
        # DATE REQUIRED
        # =========================================

        if not preferred_date:

            flash(
                "Please select your preferred date.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.service_details"
                )
            )


        # =========================================
        # TIME REQUIRED
        # =========================================

        if not preferred_time:

            flash(
                "Please select your preferred time.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.service_details"
                )
            )


        # =========================================
        # SAVE DETAILS
        # =========================================

        session["booking_description"] = (
            description
        )


        session["preferred_date"] = (
            preferred_date
        )


        session["preferred_time"] = (
            preferred_time
        )


        # =========================================
        # NEXT
        # =========================================

        return redirect(
            url_for(
                "customer.booking_summary"
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(

        "customer/service_details.html",

        service=service

    )


# =========================================================
# SERVICE PRICE HELPER
#
# फिलहाल FIXED BASE PRICE
#
# बाद में Admin Panel से
# dynamic pricing करेंगे.
# =========================================================

def get_service_base_price(
    service_name
):

    prices = {

        "Electrician": 199,

        "Plumber": 199,

        "Carpenter": 249,

        "Painter": 299,

        "AC Repair": 299,

        "Appliance Repair": 249,

        "Cleaning": 299,

        "Gardening": 249

    }


    return prices.get(
        service_name,
        199
    )


# =========================================================
# BOOKING SUMMARY
# =========================================================

@customer.route(
    "/booking-summary"
)

@customer_login_required

def booking_summary():

    # =============================================
    # GET SESSION DATA
    # =============================================

    service_id = session.get(
        "selected_service_id"
    )


    address = session.get(
        "booking_address"
    )


    description = session.get(
        "booking_description"
    )


    preferred_date = session.get(
        "preferred_date"
    )


    preferred_time = session.get(
        "preferred_time"
    )


    # =============================================
    # CHECK REQUIRED DATA
    # =============================================

    if not service_id:

        flash(
            "Please select a service first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    if not address:

        flash(
            "Please add your location first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.location"
            )
        )


    if (

        not description

        or

        not preferred_date

        or

        not preferred_time

    ):

        flash(
            "Please complete the service details.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.service_details"
            )
        )


    # =============================================
    # GET SERVICE
    # =============================================

    conn = get_db()


    service = conn.execute(
        """
        SELECT *

        FROM services

        WHERE id = ?

        AND active = 1
        """,
        (service_id,)
    ).fetchone()


    conn.close()


    if not service:

        clear_booking_session()


        flash(
            "Service not found.",
            "danger"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # CALCULATE PRICE
    # =============================================

    service_charge = (
        get_service_base_price(
            service["name"]
        )
    )


    platform_fee = 29


    total_amount = (

        service_charge

        +

        platform_fee

    )


    # =============================================
    # SAVE PRICE IN SESSION
    # =============================================

    session[
        "booking_service_charge"
    ] = service_charge


    session[
        "booking_platform_fee"
    ] = platform_fee


    session[
        "booking_total_amount"
    ] = total_amount


    # =============================================
    # RENDER
    # =============================================

    return render_template(

        "customer/booking_summary.html",


        service=service,


        service_charge=(
            service_charge
        ),


        platform_fee=(
            platform_fee
        ),


        total_amount=(
            total_amount
        ),


        address=(
            session.get(
                "booking_address"
            )
        ),


        city=(
            session.get(
                "booking_city"
            )
        ),


        state=(
            session.get(
                "booking_state"
            )
        ),


        pincode=(
            session.get(
                "booking_pincode"
            )
        ),


        description=(
            session.get(
                "booking_description"
            )
        ),


        preferred_date=(
            session.get(
                "preferred_date"
            )
        ),


        preferred_time=(
            session.get(
                "preferred_time"
            )
        )

    )


# =========================================================
# CLEAR TEMP BOOKING SESSION
# =========================================================

def clear_booking_session():

    booking_keys = [

        "selected_service_id",

        "selected_service",

        "selected_service_icon",


        "booking_address",

        "booking_city",

        "booking_state",

        "booking_pincode",

        "booking_latitude",

        "booking_longitude",


        "booking_description",

        "preferred_date",

        "preferred_time",


        "booking_service_charge",

        "booking_platform_fee",

        "booking_total_amount"

    ]


    for key in booking_keys:

        session.pop(
            key,
            None
        )


# =========================================================
# PART 3 END
# =========================================================


# =========================================================
# WORKMITRA - CUSTOMER ROUTES
# customer.py
# PART 4
# =========================================================


# =========================================================
# PROFILE
# =========================================================

@customer.route("/profile")

@customer_login_required

def profile():

    customer_data = get_current_customer()


    if not customer_data:

        session.clear()

        flash(
            "Please login again.",
            "warning"
        )

        return redirect(
            url_for(
                "customer.login"
            )
        )


    conn = get_db()


    # =============================================
    # BOOKING STATISTICS
    # =============================================

    total_bookings = conn.execute(
        """
        SELECT COUNT(*) AS total

        FROM bookings

        WHERE customer_id = ?
        """,
        (
            customer_data["id"],
        )
    ).fetchone()["total"]


    completed_bookings = conn.execute(
        """
        SELECT COUNT(*) AS total

        FROM bookings

        WHERE customer_id = ?

        AND booking_status = 'completed'
        """,
        (
            customer_data["id"],
        )
    ).fetchone()["total"]


    active_bookings = conn.execute(
        """
        SELECT COUNT(*) AS total

        FROM bookings

        WHERE customer_id = ?

        AND booking_status NOT IN
        (
            'completed',
            'cancelled',
            'worker_not_found'
        )
        """,
        (
            customer_data["id"],
        )
    ).fetchone()["total"]


    conn.close()


    return render_template(

        "customer/profile.html",

        customer=customer_data,

        total_bookings=total_bookings,

        completed_bookings=completed_bookings,

        active_bookings=active_bookings

    )


# =========================================================
# EDIT PROFILE
# =========================================================

@customer.route(
    "/edit-profile",
    methods=["GET", "POST"]
)

@customer_login_required

def edit_profile():

    customer_data = get_current_customer()


    if not customer_data:

        session.clear()

        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # UPDATE PROFILE
    # =============================================

    if request.method == "POST":


        fullname = (
            request.form
            .get("fullname", "")
            .strip()
        )


        mobile = (
            request.form
            .get("mobile", "")
            .strip()
        )


        address = (
            request.form
            .get("address", "")
            .strip()
        )


        city = (
            request.form
            .get("city", "")
            .strip()
        )


        state = (
            request.form
            .get("state", "")
            .strip()
        )


        pincode = (
            request.form
            .get("pincode", "")
            .strip()
        )


        # =============================================
        # VALIDATION
        # =============================================

        if not fullname:

            flash(
                "Please enter your full name.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.edit_profile"
                )
            )


        if (
            not mobile.isdigit()
            or len(mobile) != 10
        ):

            flash(
                "Please enter a valid 10 digit mobile number.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.edit_profile"
                )
            )


        if pincode:

            if (
                not pincode.isdigit()
                or len(pincode) != 6
            ):

                flash(
                    "Please enter a valid 6 digit pincode.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "customer.edit_profile"
                    )
                )


        conn = get_db()


        # =============================================
        # CHECK MOBILE
        # =============================================

        existing_mobile = conn.execute(
            """
            SELECT id

            FROM customers

            WHERE mobile = ?

            AND id != ?
            """,
            (
                mobile,
                customer_data["id"]
            )
        ).fetchone()


        if existing_mobile:

            conn.close()


            flash(
                "This mobile number is already used by another account.",
                "danger"
            )

            return redirect(
                url_for(
                    "customer.edit_profile"
                )
            )


        # =============================================
        # PROFILE PHOTO
        # =============================================

        profile_photo = (
            customer_data["profile_photo"]
        )


        photo = request.files.get(
            "profile_photo"
        )


        if photo and photo.filename:


            if not allowed_file(
                photo.filename
            ):

                conn.close()


                flash(
                    "Only PNG, JPG, JPEG and WEBP images are allowed.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "customer.edit_profile"
                    )
                )


            # =========================================
            # CREATE UPLOAD FOLDER
            # =========================================

            upload_path = os.path.join(

                current_app.root_path,

                UPLOAD_FOLDER,

                "customers"

            )


            os.makedirs(
                upload_path,
                exist_ok=True
            )


            # =========================================
            # UNIQUE FILE NAME
            # =========================================

            extension = (
                secure_filename(
                    photo.filename
                )
                .rsplit(
                    ".",
                    1
                )[1]
                .lower()
            )


            filename = (

                "customer_"

                + str(
                    customer_data["id"]
                )

                + "_"

                + datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )

                + "."

                + extension

            )


            photo.save(

                os.path.join(

                    upload_path,

                    filename

                )

            )


            profile_photo = (

                "uploads/customers/"

                + filename

            )


        # =============================================
        # UPDATE CUSTOMER
        # =============================================

        conn.execute(
            """
            UPDATE customers

            SET

                fullname = ?,

                mobile = ?,

                address = ?,

                city = ?,

                state = ?,

                pincode = ?,

                profile_photo = ?

            WHERE id = ?
            """,
            (

                fullname,

                mobile,

                address,

                city,

                state,

                pincode,

                profile_photo,

                customer_data["id"]

            )
        )


        conn.commit()

        conn.close()


        # =============================================
        # UPDATE SESSION
        # =============================================

        session["fullname"] = fullname


        flash(
            "Profile updated successfully.",
            "success"
        )


        return redirect(
            url_for(
                "customer.profile"
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(

        "customer/edit_profile.html",

        customer=customer_data

    )


# =========================================================
# DELETE PROFILE PHOTO
# =========================================================

@customer.route(
    "/delete-profile-photo",
    methods=["POST"]
)

@customer_login_required

def delete_profile_photo():

    customer_data = get_current_customer()


    if not customer_data:

        return redirect(
            url_for(
                "customer.login"
            )
        )


    old_photo = (
        customer_data["profile_photo"]
    )


    conn = get_db()


    conn.execute(
        """
        UPDATE customers

        SET profile_photo = NULL

        WHERE id = ?
        """,
        (
            customer_data["id"],
        )
    )


    conn.commit()

    conn.close()


    # =============================================
    # DELETE FILE
    # =============================================

    if old_photo:

        try:

            file_path = os.path.join(

                current_app.root_path,

                "static",

                old_photo

            )


            if os.path.exists(
                file_path
            ):

                os.remove(
                    file_path
                )

        except Exception as error:

            print(
                "PHOTO DELETE ERROR:",
                error
            )


    flash(
        "Profile photo removed.",
        "success"
    )


    return redirect(
        url_for(
            "customer.edit_profile"
        )
    )


# =========================================================
# SETTINGS
# =========================================================

@customer.route(
    "/settings"
)

@customer_login_required

def settings():

    customer_data = get_current_customer()


    return render_template(

        "customer/settings.html",

        customer=customer_data

    )


# =========================================================
# HELP
# =========================================================

@customer.route(
    "/help"
)

@customer_login_required

def help():

    return render_template(
        "customer/help.html"
    )


# =========================================================
# CUSTOMER DEFAULT ADDRESS
#
# Future booking me profile address use karne ke liye
# =========================================================

@customer.route(
    "/use-profile-location/<category>"
)

@customer_login_required

def use_profile_location(category):

    customer_data = get_current_customer()


    if not customer_data:

        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # CHECK ADDRESS
    # =============================================

    if (

        not customer_data["address"]

        or

        not customer_data["city"]

        or

        not customer_data["pincode"]

    ):

        flash(
            "Please complete your profile address first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.location",
                category=category
            )
        )


    # =============================================
    # SAVE PROFILE LOCATION
    # =============================================

    session["booking_address"] = (
        customer_data["address"]
    )


    session["booking_city"] = (
        customer_data["city"]
    )


    session["booking_state"] = (

        customer_data["state"]

        or

        "Uttar Pradesh"

    )


    session["booking_pincode"] = (
        customer_data["pincode"]
    )


    session["booking_latitude"] = (
        customer_data["latitude"]
    )


    session["booking_longitude"] = (
        customer_data["longitude"]
    )


    return redirect(
        url_for(
            "customer.service_details",
            category=category
        )
    )


# =========================================================
# CUSTOMER BOOKING HISTORY
#
# API - OPTIONAL
# =========================================================

@customer.route(
    "/api/my-bookings"
)

@customer_login_required

def customer_bookings_api():

    customer_data = get_current_customer()


    conn = get_db()


    booking_data = conn.execute(
        """
        SELECT

            id,

            category,

            booking_status,

            payment_status,

            total_amount,

            preferred_date,

            preferred_time,

            created_at

        FROM bookings

        WHERE customer_id = ?

        ORDER BY id DESC
        """,
        (
            customer_data["id"],
        )
    ).fetchall()


    conn.close()


    bookings_list = []


    for booking in booking_data:

        bookings_list.append({

            "id":
                booking["id"],

            "category":
                booking["category"],

            "booking_status":
                booking["booking_status"],

            "payment_status":
                booking["payment_status"],

            "total_amount":
                booking["total_amount"],

            "preferred_date":
                booking["preferred_date"],

            "preferred_time":
                booking["preferred_time"],

            "created_at":
                booking["created_at"]

        })


    return {

        "success": True,

        "bookings": bookings_list

    }


# =========================================================
# CHECK CUSTOMER BOOKING OWNERSHIP
#
# Helper
# =========================================================

def customer_owns_booking(
    customer_id,
    booking_id
):

    conn = get_db()


    booking = conn.execute(
        """
        SELECT id

        FROM bookings

        WHERE id = ?

        AND customer_id = ?
        """,
        (
            booking_id,
            customer_id
        )
    ).fetchone()


    conn.close()


    return bool(
        booking
    )


# =========================================================
# CLEAN EXPIRED OTP
#
# Optional helper
# =========================================================

def clean_expired_otps():

    try:

        conn = get_db()


        current_time = (
            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        conn.execute(
            """
            DELETE FROM customer_otps

            WHERE expires_at < ?
            """,
            (
                current_time,
            )
        )


        conn.commit()

        conn.close()


    except Exception as error:

        print(
            "OTP CLEAN ERROR:",
            error
        )


# =========================================================
# CUSTOMER BLUEPRINT INITIALIZATION
# =========================================================

def initialize_customer_system():

    """
    इस function को app.py से
    application start होने के बाद call करना है.
    """

    try:

        create_customer_tables()

        clean_expired_otps()

        print(
            "Customer system initialized successfully."
        )


    except Exception as error:

        print(
            "CUSTOMER SYSTEM INITIALIZATION ERROR:",
            error
        )


# =========================================================
# PART 4 END
# =========================================================


# =========================================================
# WORKMITRA - CUSTOMER SYSTEM
# customer.py
# PART 5
#
# CONFIRM BOOKING
# PAYMENT METHOD
# SAVE BOOKING
# BOOKING SUCCESS
# =========================================================


# =========================================================
# CONFIRM BOOKING
# =========================================================

@customer.route(
    "/confirm-booking",
    methods=["GET", "POST"]
)

@customer_login_required

def confirm_booking():

    # =============================================
    # CURRENT CUSTOMER
    # =============================================

    customer_data = get_current_customer()


    if not customer_data:

        session.clear()


        flash(
            "Session expired. Please login again.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # GET BOOKING SESSION DATA
    # =============================================

    service_id = session.get(
        "selected_service_id"
    )


    address = session.get(
        "booking_address"
    )


    city = session.get(
        "booking_city"
    )


    state = session.get(
        "booking_state"
    )


    pincode = session.get(
        "booking_pincode"
    )


    latitude = session.get(
        "booking_latitude"
    )


    longitude = session.get(
        "booking_longitude"
    )


    description = session.get(
        "booking_description"
    )


    preferred_date = session.get(
        "preferred_date"
    )


    preferred_time = session.get(
        "preferred_time"
    )


    service_charge = session.get(
        "booking_service_charge"
    )


    platform_fee = session.get(
        "booking_platform_fee"
    )


    total_amount = session.get(
        "booking_total_amount"
    )


    # =============================================
    # CHECK REQUIRED DATA
    # =============================================

    if not service_id:

        flash(
            "Please select a service first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    if not address:

        flash(
            "Please add your service location first.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.location"
            )
        )


    if (

        not description

        or

        not preferred_date

        or

        not preferred_time

    ):

        flash(
            "Please complete service details.",
            "warning"
        )


        return redirect(
            url_for(
                "customer.service_details"
            )
        )


    # =============================================
    # GET SERVICE
    # =============================================

    conn = get_db()


    service = conn.execute(
        """
        SELECT *

        FROM services

        WHERE id = ?

        AND active = 1
        """,
        (
            service_id,
        )
    ).fetchone()


    conn.close()


    # =============================================
    # SERVICE CHECK
    # =============================================

    if not service:

        clear_booking_session()


        flash(
            "Service not found.",
            "danger"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # RECALCULATE PRICE
    # SECURITY
    #
    # Session price par completely depend
    # nahi karenge.
    # =============================================

    service_charge = get_service_base_price(
        service["name"]
    )


    platform_fee = 29


    total_amount = (

        service_charge

        +

        platform_fee

    )


    # =============================================
    # POST
    # =============================================

    if request.method == "POST":

        payment_method = (

            request.form
            .get(
                "payment_method",
                ""
            )
            .strip()
            .lower()

        )


        # =========================================
        # VALIDATE PAYMENT METHOD
        # =========================================

        allowed_payment_methods = [

            "cash",

            "online"

        ]


        if payment_method not in allowed_payment_methods:

            flash(
                "Please select a valid payment method.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.confirm_booking"
                )
            )


        # =========================================
        # GENERATE BOOKING ID
        # =========================================

        booking_id = generate_booking_id()


        # =========================================
        # PAYMENT VALUES
        # =========================================

        payment_id = None


        payment_status = "pending"


        # =========================================
        # CASH PAYMENT
        # =========================================

        if payment_method == "cash":

            payment_status = "pending"


        # =========================================
        # ONLINE PAYMENT
        #
        # अभी DEMO MODE
        #
        # बाद में Razorpay etc. connect
        # करेंगे.
        # =========================================

        if payment_method == "online":

            payment_id = generate_payment_id()


            payment_status = "paid"


        # =========================================
        # SAVE BOOKING
        # =========================================

        conn = get_db()


        try:


            conn.execute(
                """
                INSERT INTO bookings
                (

                    booking_id,

                    customer_id,

                    service_id,

                    category,

                    description,

                    address,

                    city,

                    state,

                    pincode,

                    latitude,

                    longitude,

                    preferred_date,

                    preferred_time,

                    service_charge,

                    platform_fee,

                    total_amount,

                    payment_method,

                    payment_id,

                    payment_status,

                    booking_status

                )

                VALUES
                (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                (

                    booking_id,

                    customer_data["id"],

                    service["id"],

                    service["name"],

                    description,

                    address,

                    city,

                    state,

                    pincode,

                    latitude,

                    longitude,

                    preferred_date,

                    preferred_time,

                    service_charge,

                    platform_fee,

                    total_amount,

                    payment_method,

                    payment_id,

                    payment_status,

                    "pending"

                )
            )


            conn.commit()


        except Exception as error:


            conn.rollback()


            conn.close()


            print(
                "BOOKING SAVE ERROR:",
                error
            )


            flash(
                "Unable to create booking. Please try again.",
                "danger"
            )


            return redirect(
                url_for(
                    "customer.booking_summary"
                )
            )


        # =========================================
        # GET CREATED BOOKING
        # =========================================

        booking = conn.execute(
            """
            SELECT *

            FROM bookings

            WHERE booking_id = ?
            """,
            (
                booking_id,
            )
        ).fetchone()


        conn.close()


        # =========================================
        # SAVE SUCCESS BOOKING ID
        # =========================================

        session[
            "last_booking_id"
        ] = booking_id


        # =========================================
        # CLEAR TEMP BOOKING DATA
        # =========================================

        clear_booking_session()


        # =========================================
        # SUCCESS
        # =========================================

        flash(
            "Your booking has been created successfully.",
            "success"
        )


        return redirect(
            url_for(
                "customer.booking_success",
                booking_id=booking_id
            )
        )


    # =============================================
    # GET
    # =============================================

    return render_template(

        "customer/confirm_booking.html",

        customer=customer_data,

        service=service,

        address=address,

        city=city,

        state=state,

        pincode=pincode,

        description=description,

        preferred_date=preferred_date,

        preferred_time=preferred_time,

        service_charge=service_charge,

        platform_fee=platform_fee,

        total_amount=total_amount

    )


# =========================================================
# BOOKING SUCCESS
# =========================================================

@customer.route(
    "/booking-success/<booking_id>"
)

@customer_login_required

def booking_success(
    booking_id
):

    # =============================================
    # CURRENT CUSTOMER
    # =============================================

    customer_data = get_current_customer()


    if not customer_data:

        session.clear()


        return redirect(
            url_for(
                "customer.login"
            )
        )


    # =============================================
    # GET BOOKING
    # =============================================

    conn = get_db()


    booking = conn.execute(
        """
        SELECT *

        FROM bookings

        WHERE booking_id = ?

        AND customer_id = ?
        """,
        (
            booking_id,

            customer_data["id"]
        )
    ).fetchone()


    conn.close()


    # =============================================
    # BOOKING NOT FOUND
    # =============================================

    if not booking:

        flash(
            "Booking not found.",
            "danger"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # GET SERVICE
    # =============================================

    conn = get_db()


    service = None


    if booking["service_id"]:

        service = conn.execute(
            """
            SELECT *

            FROM services

            WHERE id = ?
            """,
            (
                booking["service_id"],
            )
        ).fetchone()


    conn.close()


    # =============================================
    # RENDER
    # =============================================

    return render_template(

        "customer/booking_success.html",

        customer=customer_data,

        booking=booking,

        service=service

    )


# =========================================================
# DEMO ONLINE PAYMENT SUCCESS
#
# अभी future use के लिए
# =========================================================

@customer.route(
    "/payment-demo/<booking_id>"
)

@customer_login_required

def payment_demo(
    booking_id
):

    customer_data = get_current_customer()


    if not customer_data:

        return redirect(
            url_for(
                "customer.login"
            )
        )


    conn = get_db()


    booking = conn.execute(
        """
        SELECT *

        FROM bookings

        WHERE booking_id = ?

        AND customer_id = ?
        """,
        (
            booking_id,

            customer_data["id"]
        )
    ).fetchone()


    if not booking:

        conn.close()


        flash(
            "Booking not found.",
            "danger"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    # =============================================
    # MARK PAYMENT PAID
    # =============================================

    payment_id = generate_payment_id()


    conn.execute(
        """
        UPDATE bookings

        SET

            payment_method = 'online',

            payment_id = ?,

            payment_status = 'paid',

            updated_at = CURRENT_TIMESTAMP

        WHERE booking_id = ?
        """,
        (
            payment_id,

            booking_id
        )
    )


    conn.commit()


    conn.close()


    flash(
        "Payment completed successfully.",
        "success"
    )


    return redirect(
        url_for(
            "customer.booking_success",
            booking_id=booking_id
        )
    )


# =========================================================
# GET SINGLE BOOKING
#
# Helper route
# =========================================================

@customer.route(
    "/booking/<booking_id>"
)

@customer_login_required

def booking_details(
    booking_id
):

    customer_data = get_current_customer()


    conn = get_db()


    booking = conn.execute(
        """
        SELECT *

        FROM bookings

        WHERE booking_id = ?

        AND customer_id = ?
        """,
        (
            booking_id,

            customer_data["id"]
        )
    ).fetchone()


    conn.close()


    # =============================================
    # NOT FOUND
    # =============================================

    if not booking:

        flash(
            "Booking not found.",
            "danger"
        )


        return redirect(
            url_for(
                "customer.home"
            )
        )


    return render_template(

        "customer/booking_details.html",

        customer=customer_data,

        booking=booking

    )


# =========================================================
# PART 5 END
# =========================================================
