from flask import Flask, request, make_response, jsonify
from flask_restful import Resource, Api
from flask_cors import CORS
import mysql.connector
import jwt
import os
import datetime
from functools import wraps
import numpy as np
import tensorflow as tf

app = Flask(__name__)
api = Api(app)
CORS(app)

# Mengambil credential

MYSQL_HOST = os.environ.get('MYSQL_HOST')
MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DB = os.environ.get('MYSQL_DB')
SECRET_KEY = os.environ.get('SECRET_KEY')

# Konfigurasi database
app.config['MYSQL_HOST'] = MYSQL_HOST
app.config['MYSQL_USER'] = MYSQL_USER
app.config['MYSQL_PASSWORD'] = MYSQL_PASSWORD
app.config['MYSQL_DB'] = MYSQL_DB
app.config['SECRET_KEY'] = SECRET_KEY

# Inisialisasi objek MySQL
mysql = mysql.connector.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB']
)

# Membuat cursor
cursor = mysql.cursor(dictionary=True)

# Perintah untuk membuat tabel auth_model
create_table_query = """
CREATE TABLE IF NOT EXISTS auth_model (
    username VARCHAR(50) NOT NULL,
    frontName VARCHAR(50),
    lastName VARCHAR(50),
    email VARCHAR(100) NOT NULL,
    password VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mbti varchar(50)
)
"""
# Commit perubahan ke database
mysql.commit()

# Menjalankan perintah pembuatan tabel
cursor.execute(create_table_query)

# Model database untuk authentication login register
class AuthModel:
    def __init__(self, username, frontName, lastName, email, password, status, created_at, mbti):
        self.username = username
        self.frontName = frontName
        self.lastName = lastName
        self.email = email
        self.password = password
        self.status = status
        self.created_at = created_at
        self.mbti = mbti

# Load the TensorFlow Lite model
interpreter = tf.lite.Interpreter(model_path='model(1).tflite')
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Define class labels
class_labels = ['ESTJ', 'ENTJ', 'ESFJ', 'ENFJ', 'ISTJ', 'ISFJ', 'INTJ', 'INFJ', 'ESTP', 'ESFP', 'ENTP', 'ENFP', 'ISTP', 'ISFP', 'INTP', 'INFP']


# Decorator untuk kunci endpoint / authentication
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return make_response(jsonify({
                "error": True,
                "msg": "token tidak ada"}), 404)

        try:
            # Memisahkan token dari string "Bearer [token]"
            _, token_value = token.split(' ')
            output = jwt.decode(token_value, app.config['SECRET_KEY'], algorithms=["HS256"])
        except jwt.DecodeError:
            return make_response(jsonify({
                "error": True,
                "msg": "Token invalid"}), 401)

        return f(*args, **kwargs)
    return decorator

# Fungsi untuk mendapatkan informasi pengguna yang saat ini login
def get_current_user():
    token = request.headers.get('Authorization')

    if not token:
        return make_response(jsonify({
            "error": True,
            "msg": "token tidak ada"}), 404)

    try:
        # Memisahkan token dari string "Bearer [token]"
        _, token_value = token.split(' ')
        payload = jwt.decode(token_value, app.config['SECRET_KEY'], algorithms=["HS256"])
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
                user['created_at'],
                user['mbti']
            )
            return current_user
        else:
            return None
    except jwt.DecodeError:
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
                return make_response(jsonify({
                    "error": True,
                    "msg": "Email sudah digunakan"}), 400)

            cursor.execute("SELECT COUNT(*) FROM auth_model")
            result = cursor.fetchone()

            if result and len(result) > 0:
                user_count = result['COUNT(*)']
            else:
                user_count = 0


            default_status = "User"
            username = f"{default_status}{user_count+1}{datetime.datetime.now().strftime('%Y%m%d')}"

            created_at = datetime.datetime.utcnow()

            cursor.execute("INSERT INTO auth_model (username, frontName, lastName, email, password, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)", (username, dataFrontName, dataLastName, dataEmail, dataPassword, default_status, created_at))
            mysql.commit()

            return make_response(jsonify({
                "error": False,
                "msg": "Registrasi Berhasil"}), 200)

        return make_response(jsonify({
            "error": True,
            "msg": "Email atau Password tidak boleh kosong"}), 400)

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
                    "token": token
                }

                if user['frontName'] and user['lastName']:
                    login_result["name"] = f"{user['frontName']} {user['lastName']}"
                elif user['frontName']:
                    login_result["name"] = user['frontName']

                return jsonify({
                    "error": False,
                    "msg": "success",
                    "loginResult": login_result
                })

        return jsonify({
            "error": True,
            "msg": "Login gagal, silahkan coba lagi !!!"
        })


class Dashboard(Resource):
    @token_required
    def get(self):
        current_user = get_current_user()
        
        if current_user.frontName and current_user.lastName:
            name = f"{current_user.frontName} {current_user.lastName}"
        elif current_user.frontName:
            name = current_user.frontName

        try:
            dashboard_result = {
                "name": name,
                "profilePicture": None
            }

            return jsonify({
                "error": False,
                "msg": "dashboard sukses",
                "dashboardResult": dashboard_result
            })
        except:
            return jsonify({
                "error": True,
                "msg": "dashboard gagal"
            })


class Profile(Resource):
    @token_required
    def get(self):
        current_user = get_current_user()
        
        if current_user.frontName and current_user.lastName:
            name = f"{current_user.frontName} {current_user.lastName}"
        elif current_user.frontName:
            name = current_user.frontName

        try:
            if current_user.mbti:  # Cek apakah pengguna memiliki nilai mbti
                mbti = current_user.mbti
            else:
                mbti = None

            profile_result = {
                "username": current_user.username,
                "name": name,
                "profilePicture": None,
                "status": current_user.status,
                "mbti": mbti  # Menggunakan variabel mbti yang ditentukan di atas
            }

            return jsonify({
                "error": False,
                "msg": "Profile berhasil",
                "profileResult": profile_result
            })
        except:
            return jsonify({
                "error": True,
                "msg": "Profile gagal"
            })


class ChangePassword(Resource):
    @token_required
    def post(self):
        current_user = get_current_user()
        dataCurrentPassword = request.form.get('currentPassword')
        dataNewPassword = request.form.get('newPassword')

        if not dataCurrentPassword or not dataNewPassword:
            return make_response(jsonify({
                "error": True,
                "msg": "Password tidak boleh kosong"}), 400)

        # Periksa apakah password saat ini sesuai dengan yang tersimpan dalam basis data
        cursor.execute("SELECT * FROM auth_model WHERE email = %s", (current_user.email,))
        user = cursor.fetchone()

        if user and user['password'] == dataCurrentPassword:
            # Update password baru dalam basis data
            cursor.execute("UPDATE auth_model SET password = %s WHERE email = %s", (dataNewPassword, current_user.email))
            mysql.commit()

            return make_response(jsonify({
                "error": False,
                "msg": "Password berhasil diubah"}), 200)
        else:
            return make_response(jsonify({
                "error": True,
                "msg": "Password saat ini tidak valid"}), 401)

class DeleteUser(Resource):
    @token_required
    def delete(self, username):
        current_user = get_current_user()

        if current_user.username == username:
            cursor.execute("DELETE FROM auth_model WHERE username = %s", (username,))
            mysql.commit()

            return jsonify({
                "error": False,
                "message": "User berhasil dihapus"
                })

        return jsonify({
            "error": True,
            "message": "Anda tidak memiliki izin untuk menghapus pengguna ini"})

class Predict(Resource):
    @token_required
    def post(self):
        current_user = get_current_user()
        try:
            # Get the input data
            data = request.json
            input_data = np.array(data['input']).astype(np.float32)  # Convert to FLOAT32

            # Check if input length matches the expected length
            if len(input_data) != 60:
                return jsonify({'error': 'Jawaban harus berisi 60'}), 400

            # Reshape input data
            input_data = np.reshape(input_data, (1, 60))

            # Set the input tensor
            interpreter.set_tensor(input_details[0]['index'], input_data)

            # Run inference
            interpreter.invoke()

            # Get the output tensor
            output_data = interpreter.get_tensor(output_details[0]['index'])
            predicted_class = int(np.argmax(output_data))  # Convert to int

            # Get the predicted label
            predicted_label = class_labels[predicted_class]

            # Update the current user's MBTI
            current_user = get_current_user()
            current_user.mbti = predicted_label

            # Save the predicted label to auth_model table
            cursor.execute("UPDATE auth_model SET mbti = %s WHERE email = %s", (predicted_label, current_user.email))
            mysql.commit()

            # Prepare the response
            response = {
                'predicted_class': predicted_class,
                'predicted_label': predicted_label
            }

            return jsonify(response)

        except Exception as e:
            return jsonify({'error': str(e)}), 400
        
class Question(Resource):
    @token_required
    def get(self):
        cursor.execute("SELECT question_text FROM questions")
        questions = cursor.fetchall()
        
        question_texts = [question['question_text'] for question in questions]
        
        return jsonify({
            "error": False,
            "msg": "success",
            "questions": question_texts
        })

class Personality(Resource):
    @token_required
    def get(self):
        current_user = get_current_user()
        if current_user.mbti:
            cursor.execute("SELECT * FROM personality WHERE mbti = %s", (current_user.mbti,))
            result = cursor.fetchone()
            if result:
                response = {
                    'mbti': result['mbti'],
                    'acronym': result['acronym'],
                    'description': result['description'],
                    'job': result['job']
                }
                return jsonify(response)
            else:
                return jsonify({'error': 'Data tidak ditemukan'}), 404
        else:
            return jsonify({'error': 'Pengguna tidak memiliki nilai mbti'}), 400

api.add_resource(RegisterUser, "/api/register", methods=["POST"])
api.add_resource(LoginUser, "/api/login", methods=["POST"])
api.add_resource(Dashboard, "/api/dashboard", methods=["GET"])
api.add_resource(Profile, "/api/profile", methods=["GET"])
api.add_resource(DeleteUser, "/api/deleteuser/<string:username>", methods=["DELETE"])
api.add_resource(ChangePassword, "/api/changepassword", methods=["POST"])
api.add_resource(Predict, "/api/predict")  
api.add_resource(Question, "/api/questions", methods=["GET"])
api.add_resource(Personality, "/api/personality", methods=["GET"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
