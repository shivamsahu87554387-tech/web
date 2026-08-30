import sqlite3
from config import Config


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==========================================================
# HELPERS
# ==========================================================

def table_exists(cursor, table):
    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table,)
    )

    return cursor.fetchone() is not None


def get_table_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def add_column_if_not_exists(cursor, table, column, column_type):

    if not table_exists(cursor, table):
        return

    columns = get_table_columns(cursor, table)

    if column not in columns:

        cursor.execute(
            f"ALTER TABLE {table} "
            f"ADD COLUMN {column} {column_type}"
        )


# ==========================================================
# CREATE TABLES
# ==========================================================

def create_tables():

    conn = get_db()
    cur = conn.cursor()

    try:

        # ==================================================
        # WORKERS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS workers (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                worker_id TEXT UNIQUE NOT NULL,

                fullname TEXT NOT NULL,

                email TEXT UNIQUE NOT NULL,

                mobile TEXT UNIQUE NOT NULL,

                password TEXT NOT NULL,

                profile_photo TEXT,

                address TEXT,

                city TEXT,

                state TEXT,

                pincode TEXT,

                skills TEXT,

                experience TEXT,

                aadhar_no TEXT,

                referral_code TEXT,

                referred_by TEXT DEFAULT 'WM00000',

                wallet REAL DEFAULT 0,

                rating REAL DEFAULT 0,

                status TEXT DEFAULT 'Active',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                bank_name TEXT,

                account_holder TEXT,

                account_number TEXT,

                ifsc TEXT,

                app_notification INTEGER DEFAULT 1,

                email_notification INTEGER DEFAULT 1,

                job_notification INTEGER DEFAULT 1,

                payment_notification INTEGER DEFAULT 1,

                promo_notification INTEGER DEFAULT 0,

                language TEXT DEFAULT 'English',

                is_deleted INTEGER DEFAULT 0,

                latitude REAL,

                longitude REAL
            )
        """)


        # ==================================================
        # PARTNERS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS partners (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                partner_id TEXT UNIQUE NOT NULL,

                referral_code TEXT UNIQUE,

                fullname TEXT NOT NULL,

                email TEXT UNIQUE NOT NULL,

                mobile TEXT UNIQUE NOT NULL,

                password TEXT NOT NULL,

                company_name TEXT,

                profile_photo TEXT,

                address TEXT,

                city TEXT,

                state TEXT,

                pincode TEXT,

                wallet REAL DEFAULT 0,

                bank_name TEXT,

                account_holder TEXT,

                account_number TEXT,

                ifsc TEXT,

                rating REAL DEFAULT 0,

                status TEXT DEFAULT 'Active',

                dark_mode INTEGER DEFAULT 0,

                language TEXT DEFAULT 'English',

                app_notification INTEGER DEFAULT 1,

                email_notification INTEGER DEFAULT 1,

                job_notification INTEGER DEFAULT 1,

                withdraw_notification INTEGER DEFAULT 1,

                promo_notification INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                is_deleted INTEGER DEFAULT 0
            )
        """)


        # ==================================================
        # JOBS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                job_id TEXT UNIQUE NOT NULL,

                customer_name TEXT NOT NULL,

                customer_mobile TEXT NOT NULL,

                customer_address TEXT NOT NULL,

                service TEXT NOT NULL,

                description TEXT,

                booking_date TEXT,

                booking_time TEXT,

                amount REAL DEFAULT 0,

                partner_id TEXT,

                worker_id TEXT,

                job_status TEXT DEFAULT 'Pending',

                payment_status TEXT DEFAULT 'Pending',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # JOB REQUESTS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS job_requests (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                job_id TEXT NOT NULL,

                partner_id TEXT NOT NULL,

                worker_id TEXT NOT NULL,

                request_status TEXT DEFAULT 'Pending',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # NOTIFICATIONS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_type TEXT,

                user_id TEXT,

                title TEXT,

                message TEXT,

                is_read INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # WALLET TRANSACTIONS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS wallet_transactions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_type TEXT,

                user_id TEXT,

                amount REAL,

                transaction_type TEXT,

                description TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # PARTNER WORKERS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS partner_workers (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                partner_id TEXT,

                worker_id TEXT,

                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # ADMIN
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                admin_id TEXT UNIQUE NOT NULL,

                fullname TEXT NOT NULL,

                email TEXT UNIQUE NOT NULL,

                password TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # WITHDRAW REQUESTS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                partner_id TEXT NOT NULL,

                amount REAL NOT NULL,

                bank_name TEXT NOT NULL,

                account_holder TEXT,

                account_number TEXT NOT NULL,

                ifsc TEXT NOT NULL,

                status TEXT DEFAULT 'Pending',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # PARTNER BANK
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS partner_bank (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                partner_id TEXT UNIQUE NOT NULL,

                account_holder TEXT NOT NULL,

                bank_name TEXT NOT NULL,

                account_number TEXT NOT NULL,

                ifsc TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (partner_id)
                REFERENCES partners(partner_id)
            )
        """)


        # ==================================================
        # APP RATINGS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_ratings (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                partner_id TEXT NOT NULL,

                rating INTEGER NOT NULL,

                feedback TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # WORKER RATINGS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS worker_ratings (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                worker_id TEXT NOT NULL,

                rating INTEGER NOT NULL,

                feedback TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # CUSTOMERS
        # ==================================================

        cur.execute("""
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

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # CUSTOMER OTP
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_otps (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                email TEXT NOT NULL,

                otp TEXT NOT NULL,

                purpose TEXT NOT NULL,

                expires_at TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # SERVICES
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS services (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT UNIQUE NOT NULL,

                icon TEXT,

                description TEXT,

                active INTEGER DEFAULT 1,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # BOOKINGS
        # ==================================================

        cur.execute("""
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

                payment_status TEXT DEFAULT 'pending',

                worker_id INTEGER,

                booking_status TEXT DEFAULT 'pending',

                cancellation_reason TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # REVIEWS
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS reviews (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                booking_id INTEGER UNIQUE NOT NULL,

                customer_id INTEGER NOT NULL,

                worker_id INTEGER,

                rating INTEGER NOT NULL,

                review TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ==================================================
        # UPDATE OLD WORKERS TABLE
        # ==================================================

        worker_columns = [

            ("bank_name", "TEXT"),
            ("account_holder", "TEXT"),
            ("account_number", "TEXT"),
            ("ifsc", "TEXT"),

            ("app_notification", "INTEGER DEFAULT 1"),
            ("email_notification", "INTEGER DEFAULT 1"),
            ("job_notification", "INTEGER DEFAULT 1"),
            ("payment_notification", "INTEGER DEFAULT 1"),
            ("promo_notification", "INTEGER DEFAULT 0"),

            ("language", "TEXT DEFAULT 'English'"),
            ("is_deleted", "INTEGER DEFAULT 0"),

            ("latitude", "REAL"),
            ("longitude", "REAL")
        ]

        for column, column_type in worker_columns:

            add_column_if_not_exists(
                cur,
                "workers",
                column,
                column_type
            )


        # ==================================================
        # UPDATE OLD PARTNERS TABLE
        # ==================================================

        partner_columns = [

            ("bank_name", "TEXT"),
            ("account_holder", "TEXT"),
            ("account_number", "TEXT"),
            ("ifsc", "TEXT"),

            ("dark_mode", "INTEGER DEFAULT 0"),
            ("language", "TEXT DEFAULT 'English'"),

            ("app_notification", "INTEGER DEFAULT 1"),
            ("email_notification", "INTEGER DEFAULT 1"),
            ("job_notification", "INTEGER DEFAULT 1"),
            ("withdraw_notification", "INTEGER DEFAULT 1"),
            ("promo_notification", "INTEGER DEFAULT 0"),

            ("is_deleted", "INTEGER DEFAULT 0")
        ]

        for column, column_type in partner_columns:

            add_column_if_not_exists(
                cur,
                "partners",
                column,
                column_type
            )


        # ==================================================
        # UPDATE OLD CUSTOMERS TABLE
        # ==================================================

        customer_columns = [

            ("email_verified", "INTEGER DEFAULT 0"),

            ("profile_photo", "TEXT"),

            ("address", "TEXT"),

            ("city", "TEXT"),

            ("state", "TEXT"),

            ("pincode", "TEXT"),

            ("latitude", "REAL"),

            ("longitude", "REAL")
        ]

        for column, column_type in customer_columns:

            add_column_if_not_exists(
                cur,
                "customers",
                column,
                column_type
            )


        # ==================================================
        # UPDATE OLD SERVICES TABLE
        # IMPORTANT: BEFORE INSERTING DEFAULT SERVICES
        # ==================================================

        service_columns = [

            ("description", "TEXT"),

            ("active", "INTEGER DEFAULT 1"),

            ("created_at", "TIMESTAMP")
        ]

        for column, column_type in service_columns:

            add_column_if_not_exists(
                cur,
                "services",
                column,
                column_type
            )


        # ==================================================
        # UPDATE OLD BOOKINGS TABLE
        # ==================================================

        booking_columns = [

            ("service_id", "INTEGER"),

            ("city", "TEXT"),

            ("state", "TEXT"),

            ("pincode", "TEXT"),

            ("preferred_date", "TEXT"),

            ("preferred_time", "TEXT"),

            ("service_charge", "REAL DEFAULT 0"),

            ("platform_fee", "REAL DEFAULT 0"),

            ("total_amount", "REAL DEFAULT 0"),

            ("payment_method", "TEXT"),

            ("payment_id", "TEXT"),

            ("payment_status", "TEXT DEFAULT 'pending'"),

            ("worker_id", "INTEGER"),

            ("booking_status", "TEXT DEFAULT 'pending'"),

            ("cancellation_reason", "TEXT"),

            ("updated_at", "TIMESTAMP")
        ]

        for column, column_type in booking_columns:

            add_column_if_not_exists(
                cur,
                "bookings",
                column,
                column_type
            )


        # ==================================================
        # DEFAULT SERVICES
        # IMPORTANT: THIS MUST COME AFTER SERVICE UPDATE
        # ==================================================

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

            cur.execute(
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


        # ==================================================
        # SAVE DATABASE
        # ==================================================

        conn.commit()

        print(
            "Database tables created/updated successfully."
        )


    except Exception as error:

        conn.rollback()

        print(
            "Database error:",
            error
        )

        raise


    finally:

        conn.close()


# ==========================================================
# RUN DATABASE SETUP
# ==========================================================

if __name__ == "__main__":

    create_tables()
