from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import sqlite3
import secrets
import math
from datetime import datetime

from config import Config


# ============================================================
# BLUEPRINT
# ============================================================

customer_bp = Blueprint(
    "customer",
    __name__,
    url_prefix="/customer"
)

# Compatibility with older app.py
customer = customer_bp


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ============================================================
# AUTH HELPERS
# ============================================================

def login_required():
    if not session.get("customer_id"):
        return redirect(url_for("customer.login"))
    return None


def get_current_customer():
    customer_id = session.get("customer_id")

    if not customer_id:
        return None

    conn = get_db()

    try:
        return conn.execute(
            """
            SELECT *
            FROM customers
            WHERE id = ?
            LIMIT 1
            """,
            (customer_id,)
        ).fetchone()

    except sqlite3.Error as error:
        print("GET CUSTOMER ERROR:", error)
        return None

    finally:
        conn.close()


# ============================================================
# ID GENERATORS
# ============================================================

def generate_customer_id():

    while True:

        value = "CUS-" + secrets.token_hex(4).upper()

        conn = get_db()

        try:
            exists = conn.execute(
                """
                SELECT id
                FROM customers
                WHERE customer_id = ?
                LIMIT 1
                """,
                (value,)
            ).fetchone()

        except sqlite3.Error:
            exists = None

        finally:
            conn.close()

        if not exists:
            return value


def generate_booking_id():

    while True:

        value = "WM-" + secrets.token_hex(3).upper()

        conn = get_db()

        try:
            exists = conn.execute(
                """
                SELECT id
                FROM bookings
                WHERE booking_id = ?
                LIMIT 1
                """,
                (value,)
            ).fetchone()

        except sqlite3.Error:
            exists = None

        finally:
            conn.close()

        if not exists:
            return value


# ============================================================
# TABLE / COLUMN HELPERS
# ============================================================

def table_exists(conn, table_name):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
        LIMIT 1
        """,
        (table_name,)
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):

    try:
        rows = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        return {
            row["name"]
            for row in rows
        }

    except sqlite3.Error:
        return set()


# ============================================================
# BOOKING FINDER
# ============================================================

def find_booking(value):

    customer_id = session.get("customer_id")

    if not customer_id or not value:
        return None

    conn = get_db()

    try:

        if str(value).isdigit():

            booking = conn.execute(
                """
                SELECT *
                FROM bookings
                WHERE id = ?
                AND customer_id = ?
                LIMIT 1
                """,
                (
                    int(value),
                    customer_id
                )
            ).fetchone()

            if booking:
                return booking

        return conn.execute(
            """
            SELECT *
            FROM bookings
            WHERE booking_id = ?
            AND customer_id = ?
            LIMIT 1
            """,
            (
                value,
                customer_id
            )
        ).fetchone()

    except sqlite3.Error as error:

        print("FIND BOOKING ERROR:", error)
        return None

    finally:
        conn.close()


# ============================================================
# DISTANCE
# ============================================================

def calculate_distance(lat1, lon1, lat2, lon2):

    try:

        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)

    except (
        TypeError,
        ValueError
    ):

        return None

    radius = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(
        float(lon2) - float(lon1)
    )

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        *
        math.cos(lat2)
        *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radius * c


# ============================================================
# FIND NEAREST WORKER
# ============================================================

def find_nearest_worker(
    conn,
    category,
    latitude,
    longitude
):

    """
    Finds nearest available worker.

    This function is intentionally schema-safe.

    It checks the actual workers table columns before
    constructing the query.

    Possible supported columns:

        id
        worker_id
        fullname/name
        category/service/service_type/skill
        status
        is_active
        latitude
        longitude
        available/is_available
    """

    if latitude is None or longitude is None:
        return None

    if not table_exists(
        conn,
        "workers"
    ):
        print(
            "WORKER ASSIGNMENT: workers table not found."
        )
        return None

    columns = get_columns(
        conn,
        "workers"
    )

    if "id" not in columns:
        return None

    if "latitude" not in columns:
        return None

    if "longitude" not in columns:
        return None

    # --------------------------------------------------------
    # Worker identity
    # --------------------------------------------------------

    worker_id_column = "id"

    if "worker_id" in columns:
        worker_public_column = "worker_id"
    else:
        worker_public_column = None

    # --------------------------------------------------------
    # Name column
    # --------------------------------------------------------

    if "fullname" in columns:
        name_column = "fullname"

    elif "name" in columns:
        name_column = "name"

    else:
        name_column = None

    # --------------------------------------------------------
    # Service/category column
    # --------------------------------------------------------

    category_column = None

    for column in (
        "category",
        "service",
        "service_type",
        "skill",
        "skills"
    ):

        if column in columns:
            category_column = column
            break

    # --------------------------------------------------------
    # Availability/status
    # --------------------------------------------------------

    availability_column = None

    for column in (
        "is_available",
        "available",
        "is_active",
        "status"
    ):

        if column in columns:
            availability_column = column
            break

    select_parts = [
        f"w.{worker_id_column} AS worker_db_id",
        "w.latitude",
        "w.longitude"
    ]

    if worker_public_column:
        select_parts.append(
            f"w.{worker_public_column} AS worker_public_id"
        )
    else:
        select_parts.append(
            "NULL AS worker_public_id"
        )

    if name_column:
        select_parts.append(
            f"w.{name_column} AS worker_name"
        )
    else:
        select_parts.append(
            "NULL AS worker_name"
        )

    if category_column:
        select_parts.append(
            f"w.{category_column} AS worker_category"
        )
    else:
        select_parts.append(
            "NULL AS worker_category"
        )

    if availability_column:
        select_parts.append(
            f"w.{availability_column} AS worker_availability"
        )
    else:
        select_parts.append(
            "NULL AS worker_availability"
        )

    sql = f"""
        SELECT
            {", ".join(select_parts)}
        FROM workers w
    """

    # --------------------------------------------------------
    # Availability filter
    # --------------------------------------------------------

    params = []

    if availability_column:

        if availability_column in (
            "is_available",
            "available",
            "is_active"
        ):

            sql += f"""
                WHERE (
                    w.{availability_column} = 1
                    OR LOWER(
                        CAST(
                            w.{availability_column}
                            AS TEXT
                        )
                    ) IN (
                        'true',
                        'yes',
                        'active',
                        'available'
                    )
                )
            """

        elif availability_column == "status":

            sql += """
                WHERE LOWER(
                    CAST(
                        w.status
                        AS TEXT
                    )
                ) IN (
                    'active',
                    'available',
                    'online',
                    'free',
                    'idle'
                )
            """

    try:

        workers = conn.execute(
            sql,
            params
        ).fetchall()

    except sqlite3.Error as error:

        print(
            "WORKER SEARCH ERROR:",
            error
        )
        return None

    # --------------------------------------------------------
    # Filter + calculate distance
    # --------------------------------------------------------

    nearest = None
    nearest_distance = None

    requested_category = (
        str(category)
        .strip()
        .lower()
    )

    for worker in workers:
        print(
    "CHECKING WORKER:",
    worker["worker_public_id"],
    "| NAME:",
    worker["worker_name"],
    "| SKILLS:",
    worker["worker_category"],
    "| LAT:",
    worker["latitude"],
    "| LON:",
    worker["longitude"]
)

        worker_lat = worker["latitude"]
        worker_lon = worker["longitude"]

        distance = calculate_distance(
            latitude,
            longitude,
            worker_lat,
            worker_lon
        )

        if distance is None:
            continue

        # ----------------------------------------------------
        # Category matching
        # ----------------------------------------------------

        if category_column:

            worker_category = (
                worker["worker_category"]
                or ""
            )

            worker_category = str(
                worker_category
            ).lower()

            category_match = (
                requested_category
                in worker_category
                or worker_category
                in requested_category
            )

            if not category_match:
                continue

        # ----------------------------------------------------
        # Nearest worker
        # ----------------------------------------------------

        if (
            nearest is None
            or distance < nearest_distance
        ):

            nearest = worker
            nearest_distance = distance

    if nearest:

        return {
            "worker_db_id": nearest["worker_db_id"],
            "worker_public_id": nearest["worker_public_id"],
            "worker_name": nearest["worker_name"],
            "distance_km": round(
                nearest_distance,
                2
            )
        }

    return None


# ============================================================
# ROOT
# ============================================================

@customer_bp.route("/")
def index():

    if session.get("customer_id"):
        return redirect(
            url_for("customer.home")
        )

    return redirect(
        url_for("customer.login")
    )


# ============================================================
# SIGNUP
# ============================================================

@customer_bp.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if session.get("customer_id"):
        return redirect(
            url_for("customer.home")
        )

    if request.method == "GET":

        return render_template(
            "customer/signup.html"
        )

    fullname = request.form.get(
        "fullname",
        request.form.get("name", "")
    ).strip()

    mobile = request.form.get(
        "mobile",
        request.form.get("phone", "")
    ).strip()

    email = request.form.get(
        "email",
        request.form.get(
            "email_address",
            ""
        )
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    if not fullname:

        flash(
            "Please enter your full name.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    if (
        not mobile.isdigit()
        or len(mobile) != 10
    ):

        flash(
            "Please enter a valid 10-digit mobile number.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    if not email or "@" not in email:

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

        existing = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE LOWER(email) = ?
            OR mobile = ?
            LIMIT 1
            """,
            (
                email,
                mobile
            )
        ).fetchone()

        if existing:

            flash(
                "Email or mobile number is already registered.",
                "error"
            )

            return render_template(
                "customer/signup.html"
            )

        customer_code = generate_customer_id()

        password_hash = generate_password_hash(
            password
        )

        cursor = conn.execute(
            """
            INSERT INTO customers
            (
                customer_id,
                fullname,
                mobile,
                email,
                password
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                customer_code,
                fullname,
                mobile,
                email,
                password_hash
            )
        )

        customer_db_id = cursor.lastrowid

        conn.commit()

    except sqlite3.IntegrityError as error:

        conn.rollback()

        print(
            "CUSTOMER SIGNUP ERROR:",
            error
        )

        flash(
            "Email or mobile may already exist.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "CUSTOMER DATABASE ERROR:",
            error
        )

        flash(
            "Database error while creating account.",
            "error"
        )

        return render_template(
            "customer/signup.html"
        )

    finally:

        conn.close()

    session.clear()

    session["customer_id"] = customer_db_id
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
# LOGIN
# ============================================================

@customer_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if session.get("customer_id"):
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

        login_value = request.form.get(
            "email",
            ""
        ).strip()

    if not login_value:

        login_value = request.form.get(
            "mobile",
            ""
        ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if not login_value or not password:

        flash(
            "Please enter your login details.",
            "error"
        )

        return render_template(
            "customer/login.html"
        )

    conn = get_db()

    try:

        customer_row = conn.execute(
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

        customer_row = None

    finally:

        conn.close()

    if not customer_row:

        flash(
            "Invalid email/mobile or password.",
            "error"
        )

        return render_template(
            "customer/login.html"
        )

    try:

        password_ok = check_password_hash(
            customer_row["password"],
            password
        )

    except Exception as error:

        print(
            "PASSWORD CHECK ERROR:",
            error
        )

        password_ok = False

    if not password_ok:

        flash(
            "Invalid email/mobile or password.",
            "error"
        )

        return render_template(
            "customer/login.html"
        )

    session.clear()

    session["customer_id"] = customer_row["id"]
    session["customer_code"] = customer_row["customer_id"]
    session["customer_name"] = customer_row["fullname"]
    session["customer_email"] = customer_row["email"]
    session["customer_mobile"] = customer_row["mobile"]

    flash(
        "Login successful.",
        "success"
    )

    return redirect(
        url_for("customer.home")
    )


# ============================================================
# LOGOUT
# ============================================================

@customer_bp.route("/logout")
def logout():

    session.clear()

    flash(
        "Logged out successfully.",
        "success"
    )

    return redirect(
        url_for("customer.login")
    )


# ============================================================
# HOME
# ============================================================

@customer_bp.route("/home")
def home():

    required = login_required()

    if required:
        return required

    customer_row = get_current_customer()

    if not customer_row:

        session.clear()

        return redirect(
            url_for("customer.login")
        )

    return render_template(
        "customer/home.html",
        customer=customer_row
    )


# ============================================================
# SERVICE DETAILS
# ============================================================

@customer_bp.route("/service-details")
def service_details():

    required = login_required()

    if required:
        return required

    category = request.args.get(
        "category",
        ""
    ).strip()

    service_id = request.args.get(
        "service_id",
        ""
    ).strip()

    service = None

    conn = get_db()

    try:

        if (
            service_id
            and service_id.isdigit()
        ):

            service = conn.execute(
                """
                SELECT *
                FROM services
                WHERE id = ?
                LIMIT 1
                """,
                (int(service_id),)
            ).fetchone()

        elif category:

            service = conn.execute(
                """
                SELECT *
                FROM services
                WHERE LOWER(name) = LOWER(?)
                LIMIT 1
                """,
                (category,)
            ).fetchone()

    except sqlite3.Error as error:

        print(
            "SERVICE DETAILS ERROR:",
            error
        )

    finally:

        conn.close()

    return render_template(
        "customer/service_details.html",
        service=service,
        category=category
    )


# ============================================================
# LOCATION
# ============================================================

@customer_bp.route(
    "/location",
    methods=["GET", "POST"]
)
def location():

    required = login_required()

    if required:
        return required

    customer_row = get_current_customer()

    if request.method == "GET":

        return render_template(
            "customer/location.html",
            customer=customer_row
        )

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

    latitude_value = request.form.get(
        "latitude",
        ""
    ).strip()

    longitude_value = request.form.get(
        "longitude",
        ""
    ).strip()

    if not address:

        flash(
            "Please enter your address.",
            "error"
        )

        return render_template(
            "customer/location.html",
            customer=customer_row
        )

    if pincode and (
        not pincode.isdigit()
        or len(pincode) != 6
    ):

        flash(
            "Please enter a valid 6-digit pincode.",
            "error"
        )

        return render_template(
            "customer/location.html",
            customer=customer_row
        )

    latitude = None
    longitude = None

    try:

        if latitude_value:
            latitude = float(latitude_value)

        if longitude_value:
            longitude = float(longitude_value)

    except ValueError:

        latitude = None
        longitude = None

    customer_id = session.get(
        "customer_id"
    )

    conn = get_db()

    try:

        columns = get_columns(
            conn,
            "customers"
        )

        update_fields = [
            "address = ?",
            "city = ?",
            "state = ?",
            "pincode = ?"
        ]

        values = [
            address,
            city,
            state,
            pincode
        ]

        if (
            "latitude" in columns
            and "longitude" in columns
        ):

            update_fields.extend([
                "latitude = ?",
                "longitude = ?"
            ])

            values.extend([
                latitude,
                longitude
            ])

        values.append(customer_id)

        conn.execute(
            f"""
            UPDATE customers
            SET
                {", ".join(update_fields)}
            WHERE id = ?
            """,
            values
        )

        conn.commit()

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "LOCATION UPDATE ERROR:",
            error
        )

        flash(
            "Address could not be saved.",
            "error"
        )

        return render_template(
            "customer/location.html",
            customer=customer_row
        )

    finally:

        conn.close()

    session["customer_address"] = address
    session["customer_city"] = city
    session["customer_state"] = state
    session["customer_pincode"] = pincode

    if latitude is not None:
        session["customer_latitude"] = latitude

    if longitude is not None:
        session["customer_longitude"] = longitude

    flash(
        "Address saved successfully.",
        "success"
    )

    return redirect(
        url_for("customer.booking")
    )


# ============================================================
# BOOKING PAGE
# ============================================================

@customer_bp.route("/booking")
def booking():

    required = login_required()

    if required:
        return required

    customer_row = get_current_customer()

    return render_template(
        "customer/booking.html",
        customer=customer_row
    )


# ============================================================
# PAYMENT
# ============================================================

@customer_bp.route("/payment")
def payment():

    required = login_required()

    if required:
        return required

    return render_template(
        "customer/payments.html"
    )


@customer_bp.route("/payments")
def payments():

    return redirect(
        url_for("customer.payment")
    )


# ============================================================
# CREATE BOOKING
# ============================================================

@customer_bp.route(
    "/create-booking",
    methods=["POST"]
)
def create_booking():

    required = login_required()

    if required:
        return required

    customer_id = session.get(
        "customer_id"
    )

    if not customer_id:

        return jsonify({
            "success": False,
            "message": "Customer session expired."
        }), 401

    # --------------------------------------------------------
    # READ JSON / FORM
    # --------------------------------------------------------

    data = request.get_json(
        silent=True
    )

    if data is None:
        data = request.form.to_dict()

    def get_value(*keys):

        for key in keys:

            value = data.get(key)

            if value is not None:

                value = str(value).strip()

                if value:
                    return value

        return ""

    # --------------------------------------------------------
    # BASIC DATA
    # --------------------------------------------------------

    category = get_value(
        "category",
        "service",
        "service_name"
    )

    description = get_value(
        "description",
        "details",
        "problem"
    )

    service_type = get_value(
        "service_type",
        "serviceType"
    )

    address = get_value(
        "address",
        "service_address"
    )

    city = get_value(
        "city"
    )

    state = get_value(
        "state"
    )

    pincode = get_value(
        "pincode"
    )

    preferred_date = get_value(
        "preferred_date",
        "booking_date",
        "date",
        "bookingDate"
    )

    preferred_time = get_value(
        "preferred_time",
        "booking_time",
        "time",
        "bookingTime"
    )

    quantity_value = get_value(
        "quantity"
    )

    latitude_value = get_value(
        "latitude"
    )

    longitude_value = get_value(
        "longitude"
    )

    priority = get_value(
        "priority"
    )

    payment_method = get_value(
        "payment_method",
        "paymentMethod"
    )

    payment_id = get_value(
        "payment_id",
        "paymentId",
        "transaction_id"
    )

    payment_status = get_value(
        "payment_status",
        "paymentStatus"
    )

    if not priority:
        priority = "normal"

    if not payment_method:
        payment_method = "UPI"

    if not payment_status:
        payment_status = "paid"

    # --------------------------------------------------------
    # SAVED CUSTOMER DATA
    # --------------------------------------------------------

    customer_row = get_current_customer()

    if customer_row:

        if not address:
            address = (
                customer_row["address"]
                or ""
            ).strip()

        if not city:
            city = (
                customer_row["city"]
                or ""
            ).strip()

        if not state:
            state = (
                customer_row["state"]
                or ""
            ).strip()

        if not pincode:
            pincode = (
                customer_row["pincode"]
                or ""
            ).strip()

        # Only use customer coordinates if
        # booking request did not provide them.

        if not latitude_value:

            try:

                latitude_value = str(
                    customer_row["latitude"]
                )

            except (
                KeyError,
                IndexError
            ):
                pass

        if not longitude_value:

            try:

                longitude_value = str(
                    customer_row["longitude"]
                )

            except (
                KeyError,
                IndexError
            ):
                pass

    # --------------------------------------------------------
    # REQUIRED VALIDATION
    # --------------------------------------------------------

    if not category:

        return jsonify({
            "success": False,
            "message":
                "Service category is required."
        }), 400

    if not address:

        return jsonify({
            "success": False,
            "message":
                "Service address is required."
        }), 400

    if not preferred_date:

        return jsonify({
            "success": False,
            "message":
                "Booking date is required."
        }), 400

    if not preferred_time:

        return jsonify({
            "success": False,
            "message":
                "Booking time is required."
        }), 400

    if not description:
        description = "Service booking"

    # --------------------------------------------------------
    # QUANTITY
    # --------------------------------------------------------

    quantity = None

    if quantity_value:

        try:
            quantity = int(
                quantity_value
            )

        except ValueError:

            return jsonify({
                "success": False,
                "message":
                    "Invalid quantity."
            }), 400

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    latitude = None
    longitude = None

    if latitude_value:

        try:
            latitude = float(
                latitude_value
            )

        except ValueError:
            latitude = None

    if longitude_value:

        try:
            longitude = float(
                longitude_value
            )

        except ValueError:
            longitude = None

    # --------------------------------------------------------
    # BOOKING ID
    # --------------------------------------------------------

    booking_id = generate_booking_id()

    conn = get_db()

    try:

        booking_columns = get_columns(
            conn,
            "bookings"
        )

        # ----------------------------------------------------
        # SERVICE ID
        # ----------------------------------------------------

        service_id = None

        if table_exists(
            conn,
            "services"
        ):

            try:

                service_row = conn.execute(
                    """
                    SELECT id
                    FROM services
                    WHERE LOWER(name) = LOWER(?)
                    LIMIT 1
                    """,
                    (category,)
                ).fetchone()

                if service_row:
                    service_id = service_row["id"]

            except sqlite3.Error:
                service_id = None

        # ----------------------------------------------------
        # NEAREST WORKER
        # ----------------------------------------------------
        print("\n========== BOOKING WORKER CHECK ==========")
        print("BOOKING CATEGORY:", category)
        print("CUSTOMER LATITUDE:", latitude)
        print("CUSTOMER LONGITUDE:", longitude)
        print("==========================================\n")
        nearest_worker = find_nearest_worker(
            conn,
            category,
            latitude,
            longitude
        )

        worker_db_id = None

        if nearest_worker:

            worker_db_id = (
                nearest_worker["worker_db_id"]
            )

            print(
                "NEAREST WORKER ASSIGNED:",
                nearest_worker["worker_name"],
                nearest_worker["distance_km"],
                "KM"
            )

        else:

            print(
                "NO SUITABLE WORKER FOUND."
            )

        # ----------------------------------------------------
        # BUILD INSERT DYNAMICALLY
        #
        # This prevents errors when optional columns
        # differ between database versions.
        # ----------------------------------------------------

        values_map = {
            "booking_id": booking_id,
            "customer_id": customer_id,
            "service_id": service_id,
            "category": category,
            "description": description,
            "service_type": service_type or None,
            "quantity": quantity,
            "address": address,
            "city": city or None,
            "state": state or None,
            "pincode": pincode or None,
            "latitude": latitude,
            "longitude": longitude,

            # IMPORTANT:
            # database.py uses preferred_date/time.
"preferred_date": preferred_date,
"booking_date": preferred_date,

"preferred_time": preferred_time,
"booking_time": preferred_time,

            "status": (
                "assigned"
                if worker_db_id
                else "pending"
            ),

            "booking_status": (
                "assigned"
                if worker_db_id
                else "pending"
            ),

            "priority": priority,

            "worker_id": worker_db_id,
            "assigned_worker_id": worker_db_id,

            "payment_method": payment_method,
            "payment_id": payment_id or None,
            "payment_status": payment_status
        }

        # ----------------------------------------------------
        # Only insert columns that actually exist.
        # ----------------------------------------------------

        insert_columns = []
        insert_values = []

        for column, value in values_map.items():

            if column in booking_columns:

                insert_columns.append(column)
                insert_values.append(value)

        if "booking_id" not in insert_columns:
            raise sqlite3.Error(
                "bookings.booking_id column not found."
            )

        if "customer_id" not in insert_columns:
            raise sqlite3.Error(
                "bookings.customer_id column not found."
            )

        # ----------------------------------------------------
        # INSERT
        # ----------------------------------------------------

        placeholders = ", ".join(
            ["?"] * len(insert_values)
        )

        sql = f"""
            INSERT INTO bookings
            (
                {", ".join(insert_columns)}
            )
            VALUES
            (
                {placeholders}
            )
        """

        cursor = conn.execute(
            sql,
            insert_values
        )

        database_id = cursor.lastrowid

        conn.commit()

    except sqlite3.IntegrityError as error:

        conn.rollback()

        print(
            "CREATE BOOKING INTEGRITY ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message":
                "Booking data is invalid.",
            "error": str(error)
        }), 400

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "CREATE BOOKING DATABASE ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message":
                "Booking could not be created.",
            "error": str(error)
        }), 500

    finally:

        conn.close()

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    session["last_booking_id"] = booking_id

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    response = {
        "success": True,
        "message": (
            "Booking created and worker assigned."
            if worker_db_id
            else
            "Booking created. Searching for a worker."
        ),
        "booking_id": booking_id,
        "database_id": database_id,
        "worker_assigned": bool(worker_db_id),
        "redirect_url": url_for(
            "customer.booking_success_query",
            id=booking_id
        )
    }

    if nearest_worker:

        response["worker"] = {
            "id": nearest_worker["worker_public_id"]
            or nearest_worker["worker_db_id"],
            "name": nearest_worker["worker_name"],
            "distance_km":
                nearest_worker["distance_km"]
        }

    return jsonify(response)


# ============================================================
# BOOKING SUCCESS
# ============================================================

@customer_bp.route("/booking-success")
def booking_success_query():

    required = login_required()

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

        booking_value = session.get(
            "last_booking_id",
            ""
        )

    if not booking_value:

        flash(
            "Booking ID is missing.",
            "error"
        )

        return redirect(
            url_for("customer.bookings")
        )

    booking_row = find_booking(
        booking_value
    )

    if not booking_row:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("customer.bookings")
        )

    return render_template(
        "customer/booking_success.html",
        booking=booking_row
    )


# ============================================================
# BOOKING DETAILS
# ============================================================

@customer_bp.route("/booking-details")
def booking_details_query():

    required = login_required()

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
            "Booking ID is missing.",
            "error"
        )

        return redirect(
            url_for("customer.bookings")
        )

    booking_row = find_booking(
        booking_value
    )

    if not booking_row:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("customer.bookings")
        )

    return render_template(
        "customer/booking_details.html",
        booking=booking_row
    )


# ============================================================
# NUMERIC BOOKING DETAILS
# ============================================================

@customer_bp.route(
    "/booking/<int:booking_id>"
)
def booking_details_numeric(
    booking_id
):

    required = login_required()

    if required:
        return required

    booking_row = find_booking(
        str(booking_id)
    )

    if not booking_row:

        flash(
            "Booking not found.",
            "error"
        )

        return redirect(
            url_for("customer.bookings")
        )

    return render_template(
        "customer/booking_details.html",
        booking=booking_row
    )


# ============================================================
# BOOKINGS LIST
# ============================================================

@customer_bp.route("/bookings")
def bookings():

    required = login_required()

    if required:
        return required

    customer_id = session.get(
        "customer_id"
    )

    if not customer_id:

        session.clear()

        return redirect(
            url_for("customer.login")
        )

    conn = get_db()

    try:

        bookings_list = conn.execute(
            """
            SELECT *
            FROM bookings
            WHERE customer_id = ?
            ORDER BY id DESC
            """,
            (
                customer_id,
            )
        ).fetchall()

    except sqlite3.Error as error:

        print(
            "BOOKINGS LIST ERROR:",
            error
        )

        bookings_list = []

    finally:

        conn.close()

    return render_template(
        "customer/bookings.html",
        bookings=bookings_list
    )


# ============================================================
# MY BOOKINGS
# ============================================================

@customer_bp.route("/my-bookings")
def my_bookings():

    return redirect(
        url_for("customer.bookings")
    )


# ============================================================
# CANCEL BOOKING
# ============================================================

@customer_bp.route(
    "/cancel-booking",
    methods=["POST"]
)
def cancel_booking():

    required = login_required()

    if required:
        return required

    customer_id = session.get(
        "customer_id"
    )

    data = request.get_json(
        silent=True
    )

    if data is None:
        data = request.form.to_dict()

    booking_value = str(
        data.get(
            "booking_id",
            data.get(
                "id",
                ""
            )
        )
    ).strip()

    if not booking_value:

        return jsonify({
            "success": False,
            "message":
                "Booking ID is required."
        }), 400

    booking_row = find_booking(
        booking_value
    )

    if not booking_row:

        return jsonify({
            "success": False,
            "message":
                "Booking not found."
        }), 404

    current_status = (
        booking_row["status"]
        if "status" in booking_row.keys()
        else "pending"
    )

    current_status = (
        current_status
        or "pending"
    ).lower()

    if current_status in (
        "completed",
        "cancelled"
    ):

        return jsonify({
            "success": False,
            "message":
                "This booking cannot be cancelled."
        }), 400

    conn = get_db()

    try:

        columns = get_columns(
            conn,
            "bookings"
        )

        updates = []
        values = []

        if "status" in columns:

            updates.append(
                "status = ?"
            )

            values.append(
                "cancelled"
            )

        if "booking_status" in columns:

            updates.append(
                "booking_status = ?"
            )

            values.append(
                "cancelled"
            )

        if "assigned_worker_id" in columns:

            updates.append(
                "assigned_worker_id = NULL"
            )

        if "worker_id" in columns:

            updates.append(
                "worker_id = NULL"
            )

        if not updates:

            raise sqlite3.Error(
                "No booking status column found."
            )

        values.extend([
            booking_row["id"],
            customer_id
        ])

        conn.execute(
            f"""
            UPDATE bookings
            SET
                {", ".join(updates)}
            WHERE id = ?
            AND customer_id = ?
            """,
            values
        )

        conn.commit()

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "CANCEL BOOKING ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message":
                "Booking could not be cancelled.",
            "error": str(error)
        }), 500

    finally:

        conn.close()

    return jsonify({
        "success": True,
        "message":
            "Booking cancelled successfully."
    })


# ============================================================
# PROFILE
# ============================================================

@customer_bp.route("/profile")
def profile():

    required = login_required()

    if required:
        return required

    customer_row = get_current_customer()

    if not customer_row:

        session.clear()

        return redirect(
            url_for("customer.login")
        )

    return render_template(
        "customer/profile.html",
        customer=customer_row
    )


# ============================================================
# PROFILE UPDATE
# ============================================================

@customer_bp.route(
    "/profile/edit",
    methods=["POST"]
)
def edit_profile():

    required = login_required()

    if required:
        return required

    customer_id = session.get(
        "customer_id"
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
            "Name is required.",
            "error"
        )

        return redirect(
            url_for("customer.profile")
        )

    if (
        not mobile.isdigit()
        or len(mobile) != 10
    ):

        flash(
            "Enter a valid 10-digit mobile number.",
            "error"
        )

        return redirect(
            url_for("customer.profile")
        )

    if not email or "@" not in email:

        flash(
            "Enter a valid email address.",
            "error"
        )

        return redirect(
            url_for("customer.profile")
        )

    conn = get_db()

    try:

        duplicate = conn.execute(
            """
            SELECT id
            FROM customers
            WHERE id != ?
            AND (
                LOWER(email) = ?
                OR mobile = ?
            )
            LIMIT 1
            """,
            (
                customer_id,
                email,
                mobile
            )
        ).fetchone()

        if duplicate:

            flash(
                "Email or mobile is already in use.",
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
                mobile = ?,
                email = ?
            WHERE id = ?
            """,
            (
                fullname,
                mobile,
                email,
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
    session["customer_mobile"] = mobile
    session["customer_email"] = email

    flash(
        "Profile updated successfully.",
        "success"
    )

    return redirect(
        url_for("customer.profile")
    )


# ============================================================
# APP VERSION
# ============================================================

@customer_bp.route("/app-version")
def app_version():

    return render_template(
        "customer/app_version.html"
    )
