from flask import Flask, request, make_response, jsonify
from flask_restful import Resource, Api
from flask_cors import CORS
import mysql.connector
import jwt
import os
import datetime
from functools import wraps

app = Flask(__name__)
api = Api(app)
CORS(app)

# Konfigurasi database
app.config['MYSQL_HOST'] = '%'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'userdb'
app.config['SECRET_KEY'] = 'bangkit'

# Inisialisasi objek MySQL
mysql = mysql.connector.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB']
)

# Membuat cursor
cursor = mysql.cursor(dictionary=True)

# Model database untuk authentication login register
class AuthModel:
    def __init__(self, username, frontName, lastName, email, password, status, created_at):
        self.username = username
        self.frontName = frontName
        self.lastName = lastName
        self.email = email
        self.password = password
        self.status = status
        self.created_at = created_at

# Decorator untuk kunci endpoint / authentication
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.args.get('token')

        if not token:
            return make_response(jsonify({"msg": "token tidak ada"}), 404)

        try:
            output = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return make_response(jsonify({"msg": "token invalid"}), 401)
        return f(*args, **kwargs)
    return decorator

# Fungsi untuk mendapatkan informasi pengguna yang saat ini login
def get_current_user():
    token = request.args.get('token')

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        email = payload["email"]

        cursor.execute("SELECT * FROM auth_model WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            current_user = AuthModel(
                user['username'],
                user['frontName'],
                user['lastName'],
                user['email'],
                user['password'],
                user['status'],
                user['created_at']
            )
            return current_user
        else:
            return None
    except:
        return None

class RegisterUser(Resource):
    def post(self):
        dataFrontName = request.form.get('frontName')
        dataLastName = request.form.get('lastName')
        dataEmail = request.form.get('email')
        dataPassword = request.form.get('password')

        if dataEmail and dataPassword:
            cursor.execute("SELECT * FROM auth_model WHERE email = %s", (dataEmail,))
            user = cursor.fetchone()

            if user:
                return make_response(jsonify({"error": True, "msg": "Email sudah digunakan"}), 400)

            cursor.execute("SELECT COUNT(*) FROM auth_model")
            user_count = cursor.fetchone()[0]

            default_status = "user"
            username = f"{default_status}{user_count+1}{datetime.datetime.now().strftime('%Y%m%d')}"

            created_at = datetime.datetime.utcnow()

            cursor.execute("INSERT INTO auth_model (username, frontName, lastName, email, password, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)", (username, dataFrontName, dataLastName, dataEmail, dataPassword, default_status, created_at))
            mysql.commit()

            return make_response(jsonify({"error": False, "msg": "Registrasi Berhasil"}), 200)

        return make_response(jsonify({"error": True, "msg": "Email atau Password tidak boleh kosong"}), 400)

class LoginUser(Resource):
    def post(self):
        dataEmail = request.form.get('email')
        dataPassword = request.form.get('password')

        cursor.execute("SELECT * FROM auth_model WHERE email = %s", (dataEmail,))
        user = cursor.fetchone()

        if user:
            if user['password'] == dataPassword:
                token = jwt.encode(
                    {"email": dataEmail},
                    app.config['SECRET_KEY'],
                    algorithm="HS256"
                )

                login_result = {
                    "username": user['username'],
                    "email": dataEmail,
                    "token": token.decode('utf-8')
                }

                if user['frontName'] and user['lastName']:
                    login_result["name"] = f"{user['frontName']} {user['lastName']}"

                return jsonify({
                    "error": False,
                    "message": "success",
                    "loginResult": login_result
                })

        return jsonify({
            "error": True,
            "message": "Login gagal, silahkan coba lagi !!!"
        })

class Dashboard(Resource):
    @token_required
    def get(self):
        return jsonify({"msg": "ini adalah halaman dashboard / butuh login"})

class Survey(Resource):
    @token_required
    def get(self):
        return jsonify({"msg": "ini adalah halaman survey / butuh login"})

class DeleteUser(Resource):
    @token_required
    def delete(self, username):
        current_user = get_current_user()

        if current_user.username == username:
            cursor.execute("DELETE FROM auth_model WHERE username = %s", (username,))
            mysql.commit()

            return jsonify({"message": "User berhasil dihapus"})

        return jsonify({"error": True, "message": "Anda tidak memiliki izin untuk menghapus pengguna ini"})

api.add_resource(RegisterUser, "/api/register", methods=["POST"])
api.add_resource(LoginUser, "/api/login", methods=["POST"])
api.add_resource(Dashboard, "/api/dashboard", methods=["GET"])
api.add_resource(Survey, "/api/survey", methods=["GET"])
api.add_resource(DeleteUser, "/api/deleteuser/<string:username>", methods=["DELETE"])

if __name__ == "__main__":
    app.run(debug=True)
