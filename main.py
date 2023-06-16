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
import requests
from werkzeug.utils import secure_filename
from google.cloud import storage
from google.oauth2 import service_account
from google.auth import exceptions

app = Flask(__name__)
api = Api(app)
CORS(app)

# Mengambil credential
MYSQL_HOST = os.environ.get('MYSQL_HOST')
MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DB = os.environ.get('MYSQL_DB')
SECRET_KEY = os.environ.get('SECRET_KEY')
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')

# Konfigurasi database
app.config['MYSQL_HOST'] = MYSQL_HOST
app.config['MYSQL_USER'] = MYSQL_USER
app.config['MYSQL_PASSWORD'] = MYSQL_PASSWORD
app.config['MYSQL_DB'] = MYSQL_DB
app.config['SECRET_KEY'] = SECRET_KEY
app.config['GCS_BUCKET_NAME'] = GCS_BUCKET_NAME

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
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    frontName VARCHAR(50),
    lastName VARCHAR(50),
    email VARCHAR(100) NOT NULL,
    password VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mbti varchar(50),
    photo_profile VARCHAR(255),
    update_counter INT
)
"""

# Commit perubahan ke database
mysql.commit()

# Menjalankan perintah pembuatan tabel
cursor.execute(create_table_query)

# Model database untuk authentication login register
class AuthModel:
    def __init__(self, id, username, frontName, lastName, email, password, status, created_at, mbti, photo_profile, update_counter):
        self.id = id
        self.username = username
        self.frontName = frontName
        self.lastName = lastName
        self.email = email
        self.password = password
        self.status = status
        self.created_at = created_at
        self.mbti = mbti
        self.photo_profile = photo_profile
        self.update_counter = update_counter

# Load the TensorFlow Lite model
interpreter = tf.lite.Interpreter(model_path='model(1).tflite')
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Define class labels
class_labels = ['ESTJ', 'ENTJ', 'ESFJ', 'ENFJ', 'ISTJ', 'ISFJ', 'INTJ', 'INFJ', 'ESTP', 'ESFP', 'ENTP', 'ENFP', 'ISTP', 'ISFP', 'INTP', 'INFP']

storage_client = storage.Client()

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
                user['id'],
                user['username'],
                user['frontName'],
                user['lastName'],
                user['email'],
                user['password'],
                user['status'],
                user['created_at'],
                user['mbti'],
                user['photo_profile'],
                user['update_counter']
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
                    "msg": "Email sudah digunakan"
                }), 400)

            cursor.execute("SELECT MAX(id) FROM auth_model")
            result = cursor.fetchone()
            user_count = result['MAX(id)']

            if user_count is not None:
                user_count = int(user_count)
            else:
                user_count = 0

            default_status = "User"
            username = f"{default_status}{user_count + 1}{datetime.datetime.now().strftime('%Y%m%d')}"

            created_at = datetime.datetime.utcnow()

            cursor.execute("INSERT INTO auth_model (username, frontName, lastName, email, password, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)", (username, dataFrontName, dataLastName, dataEmail, dataPassword, default_status, created_at))
            mysql.commit()

            return make_response(jsonify({
                "error": False,
                "msg": "Registrasi Berhasil"
            }), 200)

        return make_response(jsonify({
            "error": True,
            "msg": "Email atau Password tidak boleh kosong"
        }), 400)

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
            if current_user.photo_profile:
                profile_picture = current_user.photo_profile
            else:
                profile_picture = None

            dashboard_result = {
                "name": name,
                "profilePicture": profile_picture
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
            if current_user.photo_profile:
                profile_picture = current_user.photo_profile
            else:
                profile_picture = None

            if current_user.mbti:
                mbti = current_user.mbti
            else:
                mbti = None

            profile_result = {
                "username": current_user.username,
                "name": name,
                "profilePicture": profile_picture,
                "status": current_user.status,
                "mbti": mbti
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
                "msg": "Password tidak boleh kosong"
            }), 400)

        # Periksa apakah password saat ini sesuai dengan yang tersimpan dalam basis data
        cursor.execute("SELECT * FROM auth_model WHERE email = %s", (current_user.email,))
        user = cursor.fetchone()

        if user and user['password'] == dataCurrentPassword:
            # Update password baru dalam basis data
            cursor.execute("UPDATE auth_model SET password = %s WHERE email = %s", (dataNewPassword, current_user.email))
            mysql.commit()

            return make_response(jsonify({
                "error": False,
                "msg": "Password berhasil diubah"
            }), 200)
        else:
            return make_response(jsonify({
                "error": True,
                "msg": "Password saat ini tidak valid"
            }), 401)

class DeleteUser(Resource):
    @token_required
    def delete(self, username):
        current_user = get_current_user()

        if current_user.username == username:
            cursor.execute("DELETE FROM auth_model WHERE username = %s", (username,))
            mysql.commit()

            return jsonify({
                "error": False,
                "msg": "User berhasil dihapus"
                })

        return jsonify({
            "error": True,
            "msg": "Anda tidak memiliki izin untuk menghapus pengguna ini"
            })

class Predict(Resource):
    @token_required
    def post(self):
        current_user = get_current_user()
        try:
            # Get input data
            data = request.json
            input_data = np.array(data['input']).astype(np.float32)  # Convert to FLOAT32

            # Memastikan jawaban berisi 60
            if len(input_data) != 60:
                return jsonify({'error': 'Jawaban harus berisi 60'}), 400

            # Reshape input data
            input_data = np.reshape(input_data, (1, 60))

            # Set input tensor
            interpreter.set_tensor(input_details[0]['index'], input_data)

            # Menjalankan inference
            interpreter.invoke()

            # Get output tensor
            output_data = interpreter.get_tensor(output_details[0]['index'])
            predicted_class = int(np.argmax(output_data))  # Convert to int

            # Get predicted label
            predicted_label = class_labels[predicted_class]

            # Update current user MBTI
            current_user = get_current_user()
            current_user.mbti = predicted_label

            # Menyimpan predicted label ke table auth_model
            cursor.execute("UPDATE auth_model SET mbti = %s WHERE email = %s", (predicted_label, current_user.email))
            mysql.commit()

            # Menyimpan response
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
        
# Fungsi untuk mengunggah foto profil ke Google Cloud Storage
def upload_photo_profile(file, filename):
    bucket = storage_client.bucket(app.config['GCS_BUCKET_NAME'])
    blob = bucket.blob(filename)
    blob.upload_from_file(file)
    blob.make_public()
    return blob.public_url

class UploadPhoto(Resource):
    @token_required
    def post(self):
        current_user = get_current_user()
        # Cek apakah file foto profil tersedia dalam request
        if 'photo_profile' not in request.files:
            return jsonify({
                'error': True,
                'msg': 'Tidak memiliki foto profile'
            })

        photo_profile = request.files['photo_profile']

        # Cek apakah file yang diunggah adalah gambar
        if photo_profile.mimetype not in ['image/jpeg', 'image/png']:
            return jsonify({
                'error': True,
                'msg': 'Invalid photo profile format (jpg/png)'
            })

        # Cek apakah pengguna sudah memiliki foto profil sebelumnya
        cursor.execute("SELECT photo_profile, update_counter FROM auth_model WHERE username = %s", (current_user.username,))
        user = cursor.fetchone()
        if user and user['photo_profile']:
            # Hapus foto profil sebelumnya di GCS
            try:
                bucket = storage_client.bucket(app.config['GCS_BUCKET_NAME'])
                previous_update_counter = user['update_counter']
                previous_extension = user['photo_profile'].split('.')[-1]
                previous_filename = secure_filename(f"{current_user.username}_{previous_update_counter}.{previous_extension}")
                blob = bucket.blob(previous_filename)
                blob.delete()
            except:
                pass

        # Generate nama file yang aman untuk foto profil dengan menggunakan username pengguna dan counter update
        cursor.execute("SELECT update_counter FROM auth_model WHERE username = %s", (current_user.username,))
        result = cursor.fetchone()
        update_counter = result['update_counter'] + 1 if result and result['update_counter'] else 1
        filename = secure_filename(f"{current_user.username}_{update_counter}.jpg")  # Ubah ekstensi file sesuai kebutuhan

        # Upload foto profil ke GCS
        photo_url = upload_photo_profile(photo_profile, filename)

        # Simpan URL foto profil dan counter update ke database
        cursor.execute("UPDATE auth_model SET photo_profile = %s, update_counter = %s WHERE username = %s", (photo_url, update_counter, current_user.username))
        mysql.commit()

        return jsonify({
            'error': False,
            'msg': 'Photo profile berhasil di-upload',
            'photo_url': photo_url
        })
    
class DeletePhoto(Resource):
    @token_required
    def delete(self):
        current_user = get_current_user()

        # Cek apakah pengguna memiliki foto profil
        if current_user.photo_profile is None:
            return jsonify({
                'error': True,
                'msg': 'User saat ini tidak mempunyai foto profil'
            }), 404

        # Menghapus foto profil dari Google Cloud Storage
        try:
            # Mendapatkan nama file dari URL foto profil
            filename = current_user.photo_profile.split('/')[-1]

            # Menghapus foto profil dari Google Cloud Storage
            bucket = storage_client.bucket(app.config['GCS_BUCKET_NAME'])
            blob = bucket.blob(filename)
            blob.delete()
        except Exception as e:
            return jsonify({
                'error': True,
                'msg': 'Gagal menghapus foto profil',
                'details': str(e)
            }), 500

        # Menghapus foto profil dari basis data
        try:
            cursor.execute("UPDATE auth_model SET photo_profile = NULL WHERE email = %s", (current_user.email,))
            mysql.commit()
        except Exception as e:
            return jsonify({
                'error': True,
                'msg': 'Gagal menghapus foto profil',
                'details': str(e)
            }), 500

        return jsonify({
            'error': False,
            'msg': 'Foto profil berhasil dihapus'
        })

api.add_resource(RegisterUser, "/api/register", methods=["POST"])
api.add_resource(LoginUser, "/api/login", methods=["POST"])
api.add_resource(Dashboard, "/api/dashboard", methods=["GET"])
api.add_resource(Profile, "/api/profile", methods=["GET"])
api.add_resource(DeleteUser, "/api/deleteuser/<string:username>", methods=["DELETE"])
api.add_resource(ChangePassword, "/api/changepassword", methods=["POST"])
api.add_resource(Predict, "/api/predict")  
api.add_resource(Question, "/api/questions", methods=["GET"])
api.add_resource(Personality, "/api/personality", methods=["GET"])
api.add_resource(UploadPhoto, "/api/uploadphoto")
api.add_resource(DeletePhoto, '/api/deletephoto')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)