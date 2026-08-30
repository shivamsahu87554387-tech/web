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
# ADD COLUMN SAFELY
# ==========================================================

def add_column_if_not_exists(cursor, table, column, column_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]

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

    # ==========================================================
    # WORKERS
    # ==========================================================

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


    # ==========================================================
    # PARTNERS
    # ==========================================================

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


    # ==========================================================
    # JOBS
    # ==========================================================

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


    # ==========================================================
    # JOB REQUESTS
    # ==========================================================

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


    # ==========================================================
    # NOTIFICATIONS
    # ==========================================================

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


    # ==========================================================
    # WALLET TRANSACTIONS
    # ==========================================================

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


    # ==========================================================
    # PARTNER WORKERS
    # ==========================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS partner_workers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            partner_id TEXT,

            worker_id TEXT,

            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ==========================================================
    # ADMIN
    # ==========================================================

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


    # ==========================================================
    # WITHDRAW REQUESTS
    # ==========================================================

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


    # ==========================================================
    # PARTNER BANK
    # ==========================================================

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


    # ==========================================================
    # APP RATINGS
    # ==========================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_ratings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            partner_id TEXT NOT NULL,

            rating INTEGER NOT NULL,

            feedback TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ==========================================================
    # WORKER RATINGS
    # ==========================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS worker_ratings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            worker_id TEXT NOT NULL,

            rating INTEGER NOT NULL,

            feedback TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ==========================================================
    # BOOKINGS
    # ==========================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            booking_id TEXT UNIQUE NOT NULL,

            customer_id TEXT,

            category TEXT NOT NULL,

            description TEXT NOT NULL,

            service_type TEXT,

            quantity INTEGER,

            address TEXT NOT NULL,

            latitude REAL,

            longitude REAL,

            booking_date TEXT NOT NULL,

            booking_time TEXT NOT NULL,

            status TEXT DEFAULT 'pending',

            assigned_worker_id TEXT,

            assigned_partner_id TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            priority TEXT DEFAULT 'normal'
        )
    """)


    # ==========================================================
    # CUSTOMERS
    # ==========================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_id TEXT UNIQUE NOT NULL,

            fullname TEXT NOT NULL,

            email TEXT UNIQUE,

            mobile TEXT UNIQUE,

            password TEXT NOT NULL,

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


    # ==========================================================
    # SERVICES
    # ==========================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL UNIQUE,

            icon TEXT,

            status TEXT DEFAULT 'Active'
        )
    """)


    # ==========================================================
    # ADD MISSING COLUMNS TO OLD WORKERS TABLE
    # ==========================================================

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


    # ==========================================================
    # ADD MISSING COLUMNS TO OLD PARTNERS TABLE
    # ==========================================================

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


    # ==========================================================
    # SAVE DATABASE
    # ==========================================================

    conn.commit()
    conn.close()


# ==========================================================
# RUN DATABASE SETUP
# ==========================================================

if __name__ == "__main__":

    create_tables()

    print("Database tables created successfully.")
