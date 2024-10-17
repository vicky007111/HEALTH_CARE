from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB connection using environment variable
mongo_uri = os.environ.get('MONGODB_URI', 'mongodb+srv://admin1:iambatman@health.xvrmo.mongodb.net/?retryWrites=true&w=majority&appName=HEALTH')
client = MongoClient(mongo_uri)
db = client['HEALTH']  # Specify the database you want to use
users_collection = db['users']  # Collection for users
patient_data_collection = db['patient_data']  # Collection for patient data
alerts_collection = db['alerts']  # Collection for storing alerts

# Home Route
@app.route('/')
def home():
    return render_template('index.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')  # Get the user role from the form
        hashed_password = generate_password_hash(password)

        # Check if the username or email already exists
        if users_collection.find_one({"username": username}):
            flash('Username already exists!')
            return redirect(url_for('register'))
        
        if users_collection.find_one({"email": email}):
            flash('Email already exists!')
            return redirect(url_for('register'))

        # Insert new user data into MongoDB
        users_collection.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'role': role  # Store the user's role
        })
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = users_collection.find_one({"email": email})
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']  # Store username in session
            session['role'] = user['role']  # Store user role from the database

            # Redirect based on role
            if user['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))  # Redirect to patient's dashboard
        flash('Invalid email or password!')
        return redirect(url_for('login'))
    return render_template('login.html')

# Patient Dashboard Route
@app.route('/patient')
def patient_dashboard():
    if 'username' in session and session['role'] == 'patient':
        # Fetch doctors from the database for selection
        doctors = users_collection.find({"role": "doctor"})
        return render_template('patient.html', user=session, doctors=doctors)
    return redirect(url_for('login'))

# Example route to insert patient data
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

        # Insert data into MongoDB
        patient_data_collection.insert_one(patient_data)
        flash('Health data added successfully!')

        # Initialize alerts list
        alerts = []

        # Check blood rate for alerts
        if blood_rate < 90 or blood_rate > 140:  # Adjust these levels as needed
            alerts.append('Alert: Blood rate is outside the normal range!')

        # Check sugar level for alerts
        if sugar_level < 70 or sugar_level > 180:  # Adjust these levels as needed
            alerts.append('Alert: Sugar level is outside the normal range!')

        # Notify patient and doctor if there are any alerts
        if alerts:
            for alert in alerts:
                flash(alert)

            # Store alerts in the database for the doctor
            alerts_collection.insert_one({
                'doctor': doctor_username,
                'patient': patient_name,
                'alerts': alerts,
                'data_entry': patient_data  # Store relevant data for future reference
            })

        return redirect(url_for('patient_dashboard'))  # Redirect to patient's dashboard
    return redirect(url_for('login'))

# Doctor Dashboard Route
@app.route('/doctor')
def doctor_dashboard():
    if 'username' in session and session['role'] == 'doctor':
        user = {
            'username': session['username'],
            'role': session['role']
        }
        # Retrieve all patients assigned to the doctor
        patients = patient_data_collection.find({"doctor": session['username']})
        patient_data = []
        for patient in patients:
            patient_data.append(patient)

        # Create a graph for each patient
        graphs = []
        for patient in patient_data:
            blood_rates = [int(patient['blood_rate'])]
            sugar_levels = [int(patient['sugar_level'])]
            weights = [float(patient['weight'])]

            # Generate graph for this patient
            plt.figure(figsize=(10, 5))
            plt.plot(blood_rates, label='Blood Rate')
            plt.plot(sugar_levels, label='Sugar Level')
            plt.plot(weights, label='Weight')
            plt.title(f'Health Metrics for {patient["patient_name"]}')
            plt.xlabel('Metric Type')
            plt.ylabel('Value')
            plt.legend()
            plt.grid()
            graph_path = f'static/patient_{patient["patient_name"]}_data_graph.png'
            plt.savefig(graph_path)  # Save graph as an image
            plt.close()

            graphs.append(graph_path)  # Append each graph path to a list

        # Retrieve any alerts for the doctor
        doctor_alerts = alerts_collection.find({"doctor": session['username']})

        # Pass the user, patient data, alerts, and graphs to the template
        return render_template('doctor.html', user=user, patients=patient_data, alerts=doctor_alerts, graphs=graphs)
    return redirect(url_for('login'))

# Logout Route
@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    flash('You have been logged out!')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)





