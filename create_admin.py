from database import get_db
from werkzeug.security import generate_password_hash
from datetime import datetime


admin_id = input("Admin ID: ").strip()
fullname = input("Full Name: ").strip()
email = input("Email: ").strip()
password = input("Password: ")


if not admin_id or not fullname or not email or not password:

    print("❌ Sabhi fields bharna zaroori hai.")

else:

    conn = get_db()
    cur = conn.cursor()

    try:

        cur.execute("""
        INSERT INTO admin
        (
            admin_id,
            fullname,
            email,
            password,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            admin_id,
            fullname,
            email,
            generate_password_hash(password),
            datetime.now()
        ))

        conn.commit()

        print()
        print("✅ Admin account successfully created.")
        print("Admin ID:", admin_id)
        print("Name:", fullname)
        print("Email:", email)

    except Exception as e:

        print()
        print("❌ Admin create nahi hua.")
        print("Error:", e)

    finally:

        conn.close()
