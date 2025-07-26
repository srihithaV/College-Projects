from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session, jsonify
from pymongo import MongoClient
from datetime import datetime
import io
import os
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from bson.json_util import dumps


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['flight_booking']
contact_collection = db['contact_form']
users_collection = db['users']
payment_collection = db['payment_proof']
booking_collection = db['bookings']
flights_collection = db['flights']

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        pwd = request.form['pwd']
        
        user = users_collection.find_one({'name': name})
        
        if user and check_password_hash(user['pwd'], pwd):
            session['user'] = name
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('home1'))
        else:
            flash('Invalid login!', 'error')
    return render_template('login.html')



# User Home route
@app.route('/home1')
def home1():
    if 'user' in session and session['role'] == 'user':
        return render_template('home1.html')
    return redirect(url_for('login'))

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        pwd = request.form.get('pwd')
        re_password = request.form.get('rpwd')
        gender = request.form.get('gender')
        phone = request.form.get('phn')
        address = request.form.get('address')
        role = request.form.get('role')

        if pwd != re_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(pwd, method='pbkdf2:sha256')

        users_collection.insert_one({
            'name': name,
            'email': email,
            'pwd': hashed_password,
            'gender': gender,
            'phone': phone,
            'address': address,
            'role': role
        })
        flash('Registration successful! You can log in now.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# About route
@app.route('/about')
def about():
    return render_template('about.html')

# Contact form route
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        contact_collection.insert_one({
            'name': name,
            'email': email,
            'message': message
        })

        return redirect(url_for('contact_confirmation'))

    return render_template('contact.html')

@app.route('/contact_confirmation')
def contact_confirmation():
    return render_template('contact_confirmation.html')

# Flights display route
@app.route('/flight')
def flights():
    flights_list = flights_collection.find()
    return render_template('flights.html', flights=flights_list)


# Admin page to add/edit/delete flights
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        flight_id = request.form.get('flight_id')  # Get flight_id from the form
        flight_data = {
            'airline': request.form['flight_name'],
            'departure_time': request.form['departure_time'],
            'arrival_time': request.form['arrival_time'],
            'class_type': request.form['class_type'],
            'available_seats': int(request.form['seats']),
        }

        if flight_id:  # If flight_id exists, update the existing flight
            flights_collection.update_one({'_id': ObjectId(flight_id)}, {'$set': flight_data})
        else:  # Otherwise, insert a new flight
            flights_collection.insert_one(flight_data)
        
        return redirect(url_for('admin'))

    # Fetch all flights to display in the admin panel
    flights = list(flights_collection.find())
    return render_template('admin.html', flights=flights)

# Fetch flight details for editing
@app.route('/edit_flight/<flight_id>', methods=['GET'])
def edit_flight(flight_id):
    flight = flights_collection.find_one({'_id': ObjectId(flight_id)})
    if flight:
        return dumps(flight)  # Return the flight data in JSON format
    return jsonify({'error': 'Flight not found'}), 404


# Delete flight (for admin)
@app.route('/delete/<flight_id>', methods=['POST'])
def delete_flight(flight_id):
    flights_collection.delete_one({'_id': ObjectId(flight_id)})
    return redirect(url_for('admin'))

# User page to view available flights
@app.route('/viewflights')
def viewflights():
    flights = list(flights_collection.find())
    return render_template('viewflights.html', flights=flights)

# Booking form route
@app.route('/booking_form')
def booking_form():
    return render_template('booking_form.html')

@app.route('/cab')
def cab():
    return render_template('cab.html')

# Submit Booking route
@app.route('/submit_booking', methods=['POST'])
def submit_booking():
    name = request.form['name']
    email = request.form['email']
    contact = request.form['contact']
    from_location = request.form['from']
    to_location = request.form['to']
    departure_date = request.form['departure_date']
    arrival_date = request.form.get('arrival_date', departure_date)
    class_type = request.form['class_type']
    seat_no = request.form['seat_no']
    price = float(request.form['price'])
    payment_UTR = request.form['payment_UTR']
    departure = datetime.strptime(departure_date, '%Y-%m-%d')
    arrival = datetime.strptime(arrival_date, '%Y-%m-%d')
    days_difference = (arrival - departure).days if arrival > departure else 0

    booking_id = booking_collection.insert_one({
        'name': name,
        'email': email,
        'contact': contact,
        'from': from_location,
        'to': to_location,
        'departure_date': departure_date,
        'arrival_date': arrival_date,
        'class_type': class_type,
        'seat_no': seat_no,
        'price': price,
        'payment_UTR': payment_UTR,
        'days_difference': days_difference,
        'booking_date': datetime.now()
    }).inserted_id

    ticket_content = f"""
    Booking Confirmation:
    Name: {name}
    Contact: {contact}
    From: {from_location}
    To: {to_location}
    Departure Date: {departure_date}
    Arrival Date: {arrival_date}
    Class Type: {class_type}
    Seat Number: {seat_no}
    Price: ${price:.2f}
    Flight Duration: {days_difference} days
    """

    ticket_io = io.BytesIO()
    ticket_io.write(ticket_content.encode('utf-8'))
    ticket_io.seek(0)

    return send_file(ticket_io, as_attachment=True, download_name=f"{booking_id}_ticket.txt", mimetype='text/plain')

# View all tickets route
@app.route('/view_tickets')
def view_tickets():
    tickets = []
    for booking in booking_collection.find():
        tickets.append({
            'ticket_id': str(booking['_id']),
            'info': booking
        })
    return render_template('view_tickets.html', tickets=tickets)

# Delete ticket route
@app.route('/delete_ticket/<ticket_id>', methods=['POST'])
def delete_ticket(ticket_id):
    result = booking_collection.delete_one({'_id': ObjectId(ticket_id)})
    if result.deleted_count == 0:
        flash('Ticket not found or already deleted', 'error')
    else:
        flash('Ticket deleted successfully', 'success')
    
    return redirect(url_for('view_tickets'))

# API Endpoints for Flight Management
@app.route('/api/flights', methods=['GET'])
def api_get_flights():
    flights = list(flights_collection.find())
    return jsonify(flights)

@app.route('/api/flights/<flight_id>', methods=['GET'])
def api_get_flight(flight_id):
    flight = flights_collection.find_one({'_id': ObjectId(flight_id)})
    if flight:
        return jsonify(flight)
    else:
        return jsonify({'error': 'Flight not found'}), 404

@app.route('/api/flights', methods=['POST'])
def api_create_flight():
    data = request.json
    result = flights_collection.insert_one(data)
    return jsonify({'id': str(result.inserted_id)}), 201

@app.route('/api/flights/<flight_id>', methods=['PUT'])
def api_update_flight(flight_id):
    data = request.json
    result = flights_collection.update_one(
        {'_id': ObjectId(flight_id)},
        {'$set': data}
    )
    if result.matched_count > 0:
        return jsonify({'message': 'Flight updated successfully'})
    else:
        return jsonify({'error': 'Flight not found'}), 404

@app.route('/api/flights/<flight_id>', methods=['DELETE'])
def api_delete_flight(flight_id):
    result = flights_collection.delete_one({'_id': ObjectId(flight_id)})
    if result.deleted_count > 0:
        return jsonify({'message': 'Flight deleted successfully'})
    else:
        return jsonify({'error': 'Flight not found'}), 404

# Main application run
if __name__ == '__main__':
    app.run(debug=True)
