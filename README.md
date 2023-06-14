# FirstStep Backend System
## Overview
This repository contains a Flask-based RESTful API server that offers various endpoints for user authentication, user profile management, and personality prediction based on a machine learning model. The server is designed to work with a MySQL database and utilizes Google Cloud Storage for file storage.

## Requirements
To run the code in this repository, you need to have the following dependencies installed:
• Python 3.x
• Flask
• Flask-RESTful
• Flask-CORS
• mysql-connector-python
• PyJWT
• NumPy
• TensorFlow
• requests
• Werkzeug
• google-cloud-storage

You can install the required dependencies using the following command:

`pip install -r requirements.txt`

## Configuration
Before running the server, you need to configure the following environment variables:

`MYSQL_HOST`: The hostname of the MySQL database.
`MYSQL_USER`: The username for connecting to the MySQL database.
`MYSQL_PASSWORD`: The password for connecting to the MySQL database.
`MYSQL_DB`: The name of the MySQL database.
`SECRET_KEY`: A secret key used for JWT token encoding and decoding.
`GCS_BUCKET_NAME`: The name of the Google Cloud Storage bucket for storing user profile photos.

Make sure to set these environment variables before starting the server.

## Database Setup
The server requires a MySQL database to store user authentication information. You need to create a table named auth_model in the database with the following schema:

### auth_model
```
CREATE TABLE IF NOT EXISTS auth_model (
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
);
```

Another datasets table:
### personality
```
CREATE TABLE personality (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mbti TEXT,
    acronym TEXT,
    description TEXT,
    job TEXT
);
```

### questions
```
CREATE TABLE questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_text TEXT
);
```

## Starting the Server

`python main.py`

The server will start running on `http://localhost:5000`.

## API Endpoints
The following API endpoints are available:

• `POST /api/register`: Register a new user with the provided information.
• `POST /api/login`: Authenticate a user and generate a JWT token for further requests.
• `GET /api/dashboard`: Get the current user's dashboard information (requires authentication).
• `GET /api/profile`: Get the current user's profile information (requires authentication).
• `POST /api/changepassword`: Change the current user's password (requires authentication).
• `DELETE /api/users/{username}`: Delete a user (requires authentication and matching username).
• `POST /api/predict`: Predict the user's personality type based on input data (requires authentication).
• `GET /api/questions`: Get the list of questions for personality prediction (requires authentication).
• `GET /api/personality`: Get the personality information for the current user's predicted type (requires authentication).
• `POST /api/uploadphoto`: Upload a profile photo for the current user (requires authentication).
• `DELETE /api/deletephoto`: Delete a profile photo for the current user (requires authentication)

Please refer to the code for detailed information on the request payloads and responses for each endpoint.

## Machine Learning Model
The server uses a TensorFlow Lite model (`model(1).tflite`) for personality prediction. The model takes a set of input features and predicts the personality type. The model file should be placed in the same directory as `main.py`.

## File Storage
The server uses Google Cloud Storage to store user profile photos. You need to provide valid Google Cloud Storage credentials by setting up the appropriate environment variables or authentication mechanisms.

## CI/CD Deployment
We utilize Google's Cloud Build and Cloud Deployment services for our CI/CD process. Initially, we set up a trigger in Cloud Build where we provide the necessary details such as the trigger name, region (set to global), event, repository sources, branch, configuration (cloudbuild.yaml), and additional environment variables to store our database credentials.

We create Dockerfile with the configuration below.
```
# syntax=docker/dockerfile:1
FROM python:3.9.6
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

ARG MYSQL_HOST
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ARG MYSQL_DB
ARG SECRET_KEY
ARG GCS_BUCKET_NAME

ENV MYSQL_HOST=$MYSQL_HOST
ENV MYSQL_USER=$MYSQL_USER
ENV MYSQL_PASSWORD=$MYSQL_PASSWORD
ENV MYSQL_DB=$MYSQL_DB
ENV SECRET_KEY=$SECRET_KEY
ENV GCS_BUCKET_NAME=$GCS_BUCKET_NAME

COPY . .

EXPOSE 5000
ENV PORT 5000

CMD exec gunicorn --bind :$PORT main:app --workers 1 --threads 1
```

## API Documentation
Here is the API documentation:
### Register
```
• URL
    ○ /api/register
• Method
    ○ POST
• Request Body
    ○ frontName as string
    ○ lastName as string
    ○ email as string
    ○ password as string
• Response
    {
        "error": false,
        "msg": "Registrasi Berhasil"
    }
```

### Login
```
• URL
    ○ /api/login
• Method
    ○ POST
• Request Body
    ○ email as string
    ○ password as string
• Response
    {
        "error": false,
        "loginResult": {
            "email": "frnspry14@gmail.com",
            "name": "Fransiscus Prayoga",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImZybnNwcnkxNEBnbWFpbC5jb20ifQ.IIMRuObKSWohBZ4x7FgBzYbNH2KD-BTIUXcKU6qLtW4",
            "username": "User1820230614"
        },
        "msg": "success"
    }
```

### Delete User
```
• URL
    ○ /api/deleteuser/<string:username>
• Method
    ○ DELETE
• Headers
    ○ Authorization : Bearer <token>
• Response
    {
        "error": false,
        "msg": "User berhasil dihapus"
    }
```

### Change Password
```
• URL
    ○ /api/changepassword
• Method
    ○ POST
• Request Body
    ○ currrentPassword as string
    ○ newPassword as string
• Headers
    ○ Authorization : Bearer <token>
• Response
    {
        "error": false,
        "msg": "Password berhasil diubah"
    }
```

### Predict
```
• URL
    ○ /api/predict
• Method
    ○ POST
• Request Body
    ○ input as array[int]
      example : 
      {
        "input": [0, 0, 1, 2, -1, 2, 1, 0, 1, 0, 0, 0, 3, 1, -1 , 0, 0, 2, -1, 2, 0, 0, 0, 0, 3, 1, -2, 0, -3, -1, 1, 0, -1, 0, -1, 3, 1, 2, 0, 1, 1, -2, -1, -1, -1, 0, 0, 0, -1, -1, 0, 1, 0, 0, 2, 0, 0, 1, 2, 1]
      }
• Headers
    ○ Authorization : Bearer <token>
    ○ Content-Type : appplication/json
• Response
    {
        "predicted_class": 7,
        "predicted_label": "INFJ"
    }
```

### Question
```
• URL
    ○ /api/questions
• Method
    ○ GET
• Headers
    ○ Authorization : Bearer <token>
• Response
    {
        "error": false,
        "msg": "success",
        "questions": [
            "questions appear here"
        ]
    }
```

### Personality
```
• URL
    ○ /api/personality
• Method
    ○ GET
• Headers
    ○ Authorization : Bearer <token>
• Response
    {
        "acronym": "Introversion Intuition Feeling Judging",
        "description": "INFJ adalah tipe yang penuh empati, visioner, dan terdorong oleh nilai-nilai. Anda cenderung peka terhadap kebutuhan orang lain dan berdedikasi untuk membantu meningkatkan dunia.",
        "job": "Profesi yang mungkin cocok sebagai konsultan, pengembang organisasi, atau penulis.",
        "mbti": "INFJ"
    }
```

### Upload Photo
```
• URL
    ○ /api/uploadphoto
• Method
    ○ POST
• Request Body
    ○ photo_profile as .jpg/png
• Headers
    ○ Authorization : Bearer <token>
• Response
    {
        "error": false,
        "msg": "Photo profile berhasil di-upload",
        "photo_url": "your/url/User1820230614_1.jpg"
    }
```

### Delete Photo
```
• URL
    ○ /api/deletephoto
• Method
    ○ DELETE
• Headers
    ○ Authorization : Bearer <token>
• Response
    {
        "error": false,
        "msg": "Foto profil berhasil dihapus”
    }
```

### Dashboard
```
• URL
    ○ /api/dashboard
• Method
    ○ GET
• Headers
    ○ Authorization : Bearer <token>
• Response
    {
        "dashboardResult": {
            "name": "Fransiscus Prayoga",
            "profilePicture": "your/url/User1820230614_1.jpg"
        },
        "error": false,
        "msg": "dashboard sukses"
    }
```

### Profile
```
• URL
    ○ /api/profile
• Method
    ○ GET
• Headers
    ○ Authorization : Bearer <token>
• Response
    {
        "error": false,
        "msg": "Profile berhasil",
        "profileResult": {
            "mbti": "INFJ",
            "name": "Fransiscus Prayoga",
            "profilePicture": "your/url/User1820230614_1.jpg",
            "status": "User",
            "username": "User1820230614"
        }
    }
```

This README provides a brief overview of the repository and the functionality of the Flask API server. For more detailed information, please refer to the code comments.