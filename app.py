from flask import Flask, request, jsonify, render_template
import pymysql
import os
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("AZURE_MYSQL_HOST"),
    "user": os.getenv("AZURE_MYSQL_USER"),
    "password": os.getenv("AZURE_MYSQL_PASSWORD"),
    "database": os.getenv("AZURE_MYSQL_NAME"),
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 10
}

# --------------------------------------------------
# DB Connection code
# --------------------------------------------------
def get_db_connection():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        logger.error(f"MySQL connection failed: {e}")
        return None

# --------------------------------------------------
# Init DB (AUTO RUN on Azure startup)
# --------------------------------------------------
def init_db():
    logger.info("Checking / Creating database table...")

    connection = get_db_connection()
    if not connection:
        logger.error("Database not reachable. Table not created.")
        return

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
            logger.info("Users table is ready ✅")
    except Exception as e:
        logger.error(f"Table creation failed: {e}")
    finally:
        connection.close()

init_db()

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "running",
        "message": "Azure Flask App with MySQL is live"
    })

# --------------------------------------------------
# Get All Users
# --------------------------------------------------
@app.route("/users", methods=["GET"])
def get_users():
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 200   # frontend crash avoid

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users ORDER BY id DESC")
            users = cursor.fetchall()
            return jsonify(users), 200
    except Exception as e:
        logger.error(e)
        return jsonify([]), 200
    finally:
        connection.close()

# --------------------------------------------------
# Create User
# --------------------------------------------------
@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    if not data or "name" not in data or "email" not in data:
        return jsonify({"error": "Name and email required"}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database unavailable"}), 500

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                (data["name"], data["email"])
            )
            connection.commit()
            return jsonify({"message": "User created"}), 201
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Insert failed"}), 500
    finally:
        connection.close()

# --------------------------------------------------
# Update User
# --------------------------------------------------
@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database unavailable"}), 500

    try:
        fields = []
        values = []

        if "name" in data:
            fields.append("name=%s")
            values.append(data["name"])
        if "email" in data:
            fields.append("email=%s")
            values.append(data["email"])

        if not fields:
            return jsonify({"error": "Nothing to update"}), 400

        values.append(user_id)

        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id=%s",
                values
            )
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({"error": "User not found"}), 404

            return jsonify({"message": "User updated"}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Update failed"}), 500
    finally:
        connection.close()

# --------------------------------------------------
# Delete User
# --------------------------------------------------
@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database unavailable"}), 500

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({"error": "User not found"}), 404

            return jsonify({"message": "User deleted"}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Delete failed"}), 500
    finally:
        connection.close()