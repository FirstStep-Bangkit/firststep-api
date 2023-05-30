#import library flask dkk
from flask import Flask, request, make_response, jsonify
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
 
#import library pendukung
import jwt
import os
import datetime
#import library decorator
from functools import wraps

#inisialisasi flask dkk
app = Flask(__name__)
api = Api(app)

#konfigurasi database --> create file db.sqlite
filename = os.path.dirname(os.path.abspath(__file__))
database = 'sqlite:///' + os.path.join(filename, 'db.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = database
app.config['SECRET_KEY'] = 'bangkit'


# Inisialisasi objek SQLAlchemy
db = SQLAlchemy(app)

# Inisialisasi CORS
CORS(app)

#membuat schema model database untuk authentication login register
class AuthModel(db.Model):
    username = db.Column(db.String(100), primary_key=True)
    frontName = db.Column(db.String(50))
    lastName = db.Column(db.String(50))
    email = db.Column(db.String(50))
    password = db.Column(db.String(50))
    status = db.Column(db.String(50))
    #membuat kolom created at
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Fungsi untuk melakukan pengecekan token pada setiap permintaan yang membutuhkan autentikasi
#decorator untuk kunci endpoint / authentication
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        #token akan diparsing melalui parameter di endpoints
        token = request.args.get('token')

        #cek ketersediaan token
        if not token:
            return make_response(jsonify({"msg":"token tidak ada"}), 404)
        
        #decode token yang diterima
        try:
            output = jwt.decode(token, app.config['SECRET_KEY'], algorithms={"HS256"})
        except:
            return make_response(jsonify({"msg":"token invalid"}))
        return f(*args, **kwargs)
    return decorator

# Fungsi untuk mendapatkan informasi pengguna yang saat ini login
def get_current_user():
    # Mendapatkan token dari permintaan
    token = request.args.get('token')

    # Mendekode token untuk mendapatkan informasi pengguna
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        email = payload["email"]
        # Query informasi pengguna berdasarkan email
        current_user = AuthModel.query.filter_by(email=email).first()
        return current_user
    except:
        return None

#membuat routing endpoint 
# routing authentication register
class RegisterUser(Resource):
    # posting data dari frontend untuk disimpan ke database
    def post(self):
        dataFrontName = request.form.get('frontName')
        dataLastName = request.form.get('lastName')
        dataEmail = request.form.get('email')
        dataPassword = request.form.get('password')

        # cek username password ada(?)
        if dataEmail and dataPassword:
            # cek apakah username sudah ada dalam database
            existing_user = AuthModel.query.filter_by(email=dataEmail).first()
            if existing_user:
                return make_response(jsonify({"error":"True","msg": "Email sudah digunakan"}), 400)

            # menghitung jumlah user yang ada untuk mendapatkan urutan berikutnya
            user_count = AuthModel.query.count()

            # Set nilai default untuk field "status" saat registrasi
            default_status = "user"

            # membuat ID berdasarkan urutan terbaru
            username = f"{default_status}{user_count+1}{datetime.datetime.now().strftime('%Y%m%d')}"

            # tulis data ke db.sqlite
            dataModel = AuthModel(username=username, email=dataEmail, frontName=dataFrontName, lastName=dataLastName, password=dataPassword, status=default_status)
            db.session.add(dataModel)
            db.session.commit()
            return make_response(jsonify({"error":"False","msg": "Registrasi Berhasil"}), 200)
        
        return make_response(jsonify({"error":"True","msg": "Email atau Password tidak boleh kosong"}), 400)

#routing authentication login
class LoginUser(Resource):
    def post(self):
        dataEmail = request.form.get('email')
        dataPassword = request.form.get('password')

        #query data berdasarkan username
        user = AuthModel.query.filter_by(email=dataEmail).first()

        if user:
            # jika username ditemukan, periksa password
            if user.password == dataPassword:
                # jika password cocok, login berhasil
                token = jwt.encode(
                    {
                        "email": dataEmail, 
                        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
                    }, app.config['SECRET_KEY'], algorithm="HS256"
                )

                login_result = {
                    "username": user.username,
                    "email": dataEmail,
                    "token": token
                }

                if user.frontName and user.lastName:
                    login_result["name"] = f"{user.frontName} {user.lastName}"

                return jsonify({
                    "error": False,
                    "message": "success",
                    "loginResult": login_result
                })
        
        #jika username atau password salah, login gagal
        return jsonify({
            "error": True,
            "message": "Login gagal, silahkan coba lagi !!!"
        })
    
#halaman yang diprotected
class Dashboard(Resource):
    #menambahkan decorator untuk mengunci halaman
    @token_required
    def get(self):
        return jsonify({"msg":"ini adalah halaman dashboard / butuh login"})

class Survey(Resource):
    #menambahkan decorator untuk mengunci halaman
    @token_required
    def get(self):
        return jsonify({"msg":"ini adalah halaman survey / butuh login"})

class DeleteUser(Resource):
    # Menghapus user berdasarkan username
    @token_required
    def delete(self, username):
        # Mendapatkan informasi pengguna yang saat ini login
        current_user = get_current_user()

        # Cek apakah pengguna yang melakukan permintaan adalah pengguna yang bersangkutan
        if current_user.username == username:
            # Hapus user dari database
            db.session.delete(current_user)
            db.session.commit()
            return jsonify({"message": "User berhasil dihapus"})

        return jsonify({"error": True, "message": "Anda tidak memiliki izin untuk menghapus pengguna ini"})

#inisiasi resource api
api.add_resource(RegisterUser, "/api/register", methods=["POST"])
api.add_resource(LoginUser, "/api/login", methods=["POST"] )
api.add_resource(Dashboard, "/api/dashboard", methods=["GET"])
api.add_resource(Survey, "/api/survey", methods=["GET"])
api.add_resource(DeleteUser, "/api/deleteuser/<string:username>", methods=["DELETE"])

#jalankan aplikasi app.py
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)