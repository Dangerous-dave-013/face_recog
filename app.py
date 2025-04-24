import os
import time
import json
import cv2
import face_recognition
import numpy as np
from datetime import datetime
from flask import Flask, render_template, Response, request, redirect, url_for, session, jsonify, send_from_directory
import base64
from PIL import Image
from io import BytesIO
from twilio.rest import Client
from werkzeug.utils import secure_filename

last_unknown_save_time = 0  # global timestamp
cooldown_seconds = 10       # change this to whatever cooldown you want
last_detected_user_info = None


app = Flask(__name__)
app.secret_key = "13072005"

# Face data
KNOWN_FACES_DIR = "faces"
LOGS_FILE = "logs.json"
AUTHORIZED_PASSWORD = "1hk23is023"  # 👈 Change this to your own secure pass

known_face_encodings = []
known_face_names = []

def load_faces():
    known_face_encodings.clear()
    known_face_names.clear()
    if not os.path.exists(KNOWN_FACES_DIR):
        os.makedirs(KNOWN_FACES_DIR)

    for name in os.listdir(KNOWN_FACES_DIR):
        person_dir = os.path.join(KNOWN_FACES_DIR, name)
        for filename in os.listdir(person_dir):
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue  # Skip non-image files like metadata.json

            image_path = os.path.join(person_dir, filename)
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_face_encodings.append(encodings[0])
                known_face_names.append(name)

FACES_FOLDER = os.path.join(app.root_path, 'faces')

@app.route('/faces/<user_name>/<filename>')
def serve_face_image(user_name, filename):
    # Serve the image from the 'faces' folder
    return send_from_directory(os.path.join(FACES_FOLDER, user_name), filename)


load_faces()
LOGS_FILE = "logs.json"

def log_event(name):
    log_entry = {
        'name': name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Check if the logs file exists
    if os.path.exists(LOGS_FILE):
        # If the file exists, read its contents
        with open(LOGS_FILE, 'r') as file:
            logs = json.load(file)
    else:
        # If the file doesn't exist, initialize logs as an empty list
        logs = []

    # Append the new log entry to the list
    logs.append(log_entry)

    # Write the updated logs back to the JSON file
    with open(LOGS_FILE, 'w') as file:
        json.dump(logs, file, indent=4)


last_detected_user_info = {}

def generate_video():
    global last_detected_user_info
    cam = cv2.VideoCapture(0)

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, faces)

        detected_user_info = None

        for (top, right, bottom, left), face_encoding in zip(faces, encodings):
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"

            if True in matches:
                matched_idx = matches.index(True)
                name = known_face_names[matched_idx]
                log_event(name)  # Log known face

                users_file = "users_data.json"
                if os.path.exists(users_file):
                    with open(users_file, 'r') as file:
                        users_data = json.load(file)
                        for user in users_data:
                            if user['name'] == name:
                                detected_user_info = user
                                break
            else:
                log_event(name)  # Log unknown face

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0) if name != "Unknown" else (0, 0, 255), 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        if detected_user_info:
            last_detected_user_info = detected_user_info
        else:
            last_detected_user_info = None

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cam.release()



@app.route('/video_feed')
def video_feed():
    return Response(generate_video(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if password == AUTHORIZED_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))  # Redirect to the dashboard
        else:
            return "Unauthorized", 401
    return render_template('admin.html')  # Show the login page if it's a GET request



@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))  # Redirect to login if not logged in
    return render_template('admin_dashboard.html')  # Serve the admin dashboard if logged in


@app.route('/logs')
def logs_page():
    logs = []
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r') as f:
            try:
                logs = json.load(f)
            except Exception as e:
                print(f"Error reading log file: {e}")  # Debug print
    return render_template('logs.html', logs=logs)

@app.route('/')
def index():
    # This is your index page where the user will be redirected after registration
    return render_template('index.html')


@app.route('/register_face', methods=['POST'])
def register_face():
    if not session.get('admin_logged_in'):
        return "Unauthorized", 401

    name = request.form['name']
    phone_number = request.form['phone_number']  # Get phone number from form data
    image_data = request.form.get('image_data')

    if not image_data:
        return "No image", 400

    # Decode base64 image
    header, encoded = image_data.split(",", 1)
    image_bytes = base64.b64decode(encoded)
    image = Image.open(BytesIO(image_bytes))

    save_path = os.path.join(KNOWN_FACES_DIR, name)
    os.makedirs(save_path, exist_ok=True)

    count = len(os.listdir(save_path)) + 1
    image_path = os.path.join(save_path, f"{count}.jpg")
    image.save(image_path)

    # Save user metadata to metadata.json
    metadata = {
        "name": name,
        "age": request.form.get('age', 'N/A'),
        "phone_number": phone_number
    }

    with open(os.path.join(save_path, "metadata.json"), 'w') as metadata_file:
        json.dump(metadata, metadata_file, indent=4)

    # Store user data in users_data.json
    users_data = []
    users_file = "users_data.json"
    if os.path.exists(users_file):
        with open(users_file, 'r') as file:
            users_data = json.load(file)

    user_data = {
        "name": name,
        "age": request.form.get('age', 'N/A'),  # Optionally handle age
        "phone_number": phone_number
    }

    users_data.append(user_data)

    with open(users_file, 'w') as file:
        json.dump(users_data, file, indent=4)

    load_faces()
    return redirect(url_for('index'))
    



video_capture = None

def get_camera():
    global video_capture
    if video_capture is None or not video_capture.isOpened():
        video_capture = cv2.VideoCapture(0)
    return video_capture

def stop_camera():
    global video_capture
    if video_capture and video_capture.isOpened():
        video_capture.release()
        video_capture = None

@app.route('/stop_feed')
def stop_feed():
    stop_camera()
    return "OK", 200

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/view_members')
def view_members():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    members = []
    for name in os.listdir(KNOWN_FACES_DIR):
        path = os.path.join(KNOWN_FACES_DIR, name, "metadata.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                metadata = json.load(f)
                members.append(metadata)

    return render_template("view_members.html", members=members)

@app.route('/delete_member/<name>', methods=['POST'])
def delete_member(name):
    if not session.get('admin_logged_in'):
        return "Unauthorized", 401

    member_dir = os.path.join(KNOWN_FACES_DIR, name)
    if os.path.exists(member_dir):
        for file in os.listdir(member_dir):
            os.remove(os.path.join(member_dir, file))
        os.rmdir(member_dir)

    load_faces()
    return redirect(url_for('view_members'))

@app.route('/get_detected_user_info')
def get_detected_user_info():
    global last_detected_user_info
    if last_detected_user_info:
        return jsonify(last_detected_user_info)
    else:
        return jsonify({'message': 'No user info available'})
    

def save_unknown_face(frame, face_location):
    top, right, bottom, left = face_location
    face_image = frame[top:bottom, left:right]

    # Make sure the folder exists
    os.makedirs('static/unknown_faces', exist_ok=True)

    # Create the filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"static/unknown_faces/{timestamp}.jpg"

    # Save the image
    cv2.imwrite(filename, face_image)


@app.route('/unknown-faces')
def unknown_faces():
    image_files = sorted(os.listdir('unknown_faces'), reverse=True)
    images = [{'file': img, 'time': img.replace('.jpg', '').replace('_', ' ')} for img in image_files]
    return render_template('unknown_faces.html', images=images)


    

if __name__ == '__main__':
    app.run(debug=True)
