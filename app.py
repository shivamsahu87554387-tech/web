from flask import Flask

from config import Config
from database import create_tables

# ==========================
# Blueprints
# ==========================

from routes.auth import auth_bp
from routes.worker import worker_bp
from routes.partner import partner_bp
from routes.admin import admin_bp
from routes.customer import customer

# ==========================
# Flask App
# ==========================

app = Flask(__name__)

app.config.from_object(Config)


# Secret Key
app.secret_key = Config.SECRET_KEY


# Create Database Tables
create_tables()


# ==========================
# Register Blueprints
# ==========================

app.register_blueprint(auth_bp)
app.register_blueprint(worker_bp)
app.register_blueprint(partner_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(customer)

# ==========================
# Run Server
# ==========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

