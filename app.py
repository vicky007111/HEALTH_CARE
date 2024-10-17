from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
import matplotlib.pyplot as plt
import os

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'

mongo_uri = os.environ.get('MONGODB_URI', 'mongodb+srv://admin1:iambatman@health.xvrmo.mongodb.net/?retryWrites=true&w=majority&appName=HEALTH')
client = MongoClient(mongo_uri)
db = client['HEALTH']
users_collection = db['users']
patient_data_collection = db['patient_data']
alerts_collection = db['alerts']

if not os.path.exists('static/images'):
    os.makedirs('static/images')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        hashed_password = generate_password_hash(password)

        if users_collection.find_one({"username": username}):
            flash('Username already exists!')
            return redirect(url_for('register'))
        
        if users_collection.find_one({"email": email}):
            flash('Email already exists!')
            return redirect(url_for('register'))

        users_collection.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'role': role
        })
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = users_collection.find_one({"email": email})
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['role'] = user['role']

            if user['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        flash('Invalid email or password!')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/patient')
def patient_dashboard():
    if 'username' in session and session['role'] == 'patient':
        doctors = users_collection.find({"role": "doctor"})
        return render_template('patient.html', user=session, doctors=doctors)
    return redirect(url_for('login'))

@app.route('/health_data', methods=['POST'])
def health_data():
    if 'username' in session:
        patient_name = session['username']
        blood_rate = int(request.form.get('blood_rate'))
        sugar_level = int(request.form.get('sugar_level'))
        weight = float(request.form.get('weight'))
        doctor_username = request.form.get('doctor')

        patient_data = {
            'patient_name': patient_name,
            'blood_rate': blood_rate,
            'sugar_level': sugar_level,
            'weight': weight,
            'doctor': doctor_username
        }

        patient_data_collection.insert_one(patient_data)
        flash('Health data added successfully!')

        alerts = []

        if blood_rate < 90 or blood_rate > 140:
            alerts.append('Alert: Blood rate is outside the normal range!')

        if sugar_level < 70 or sugar_level > 180:
            alerts.append('Alert: Sugar level is outside the normal range!')

        if alerts:
            for alert in alerts:
                flash(alert)

            alerts_collection.insert_one({
                'doctor': doctor_username,
                'patient': patient_name,
                'alerts': alerts,
                'data_entry': patient_data
            })

        return redirect(url_for('patient_dashboard'))
    return redirect(url_for('login'))

@app.route('/doctor')
def doctor_dashboard():
    if 'username' in session and session['role'] == 'doctor':
        user = {
            'username': session['username'],
            'role': session['role']
        }
        patients = patient_data_collection.find({"doctor": session['username']})
        patient_data = []
        graphs = []

        for patient in patients:
            patient_data.append(patient)

            patient_health_data = patient_data_collection.find({"patient_name": patient['patient_name']})

            blood_rates = []
            sugar_levels = []
            weights = []

            for data in patient_health_data:
                blood_rates.append(int(data['blood_rate']))
                sugar_levels.append(int(data['sugar_level']))
                weights.append(float(data['weight']))

            plt.figure(figsize=(10, 5))
            plt.plot(blood_rates, label='Blood Rate')
            plt.plot(sugar_levels, label='Sugar Level')
            plt.plot(weights, label='Weight')
            plt.title(f'Health Metrics for {patient["patient_name"]}')
            plt.xlabel('Entries')
            plt.ylabel('Value')
            plt.legend()
            plt.grid()

            graph_filename = f'images/graph_{patient["patient_name"]}.png'
            graph_path = f'static/{graph_filename}'
            plt.savefig(graph_path)
            plt.close()

            graphs.append(graph_filename)

        doctor_alerts = alerts_collection.find({"doctor": session['username']})
        return render_template('doctor.html', user=user, patients=patient_data, alerts=doctor_alerts, graphs=graphs)
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
