from database import get_db


# ======================================
# Worker ID
# Format : WM10001
# ======================================

def generate_worker_id():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM workers")

    total = cur.fetchone()[0]

    conn.close()

    return f"WM{10001 + total}"


# ======================================
# Partner ID
# Format : WP10001
# ======================================

def generate_partner_id():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM partners")

    total = cur.fetchone()[0]

    conn.close()

    return f"WP{10001 + total}"


# ======================================
# Admin ID
# Format : AD10001
# ======================================

def generate_admin_id():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM admin")

    total = cur.fetchone()[0]

    conn.close()

    return f"AD{10001 + total}"


# ======================================
# Job ID
# Format : JB10001
# ======================================

def generate_job_id():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM jobs")

    total = cur.fetchone()[0]

    conn.close()

    return f"JB{10001 + total}"


# ======================================
# Partner Referral Code
# Format : RP10001
# ======================================

def generate_referral_code():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM partners")

    total = cur.fetchone()[0]

    conn.close()

    return f"RP{10001 + total}"
