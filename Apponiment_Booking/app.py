from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'mysecretkey123'

#MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['hospital_db']

# Add sample data (run once)
def add_sample_data():
    if db.hospitals.count_documents({}) == 0:
        h1 = db.hospitals.insert_one({'name': 'City Hospital', 'location': 'Mumbai, Andheri'})
        h2 = db.hospitals.insert_one({'name': 'Apollo Hospital', 'location': 'Mumbai, Bandra'})
        
        d1 = db.doctors.insert_one({'hospital_id': h1.inserted_id, 'name': 'Rajesh Kumar', 'specialization': 'Fever', 'fee': 500})
        d2 = db.doctors.insert_one({'hospital_id': h1.inserted_id, 'name': 'Priya Sharma', 'specialization': 'Heart', 'fee': 800})
        d3 = db.doctors.insert_one({'hospital_id': h2.inserted_id, 'name': 'Amit Patel', 'specialization': 'Bones', 'fee': 700})
        
        for i in range(5):
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            for doctor_id in [d1.inserted_id, d2.inserted_id, d3.inserted_id]:
                for time in ['10:00', '14:00', '16:00']:
                    db.slots.insert_one({'doctor_id': doctor_id, 'date': date, 'time': time, 'booked': False})

#home page 
@app.route('/')
def home():
    hospitals = list(db.hospitals.find())
    return render_template('home.html', hospitals=hospitals)

#view doctors
@app.route('/hospital/<hospital_id>')
def view_hospital(hospital_id):
    hospital = db.hospitals.find_one({'_id': ObjectId(hospital_id)})
    doctors = list(db.doctors.find({'hospital_id': ObjectId(hospital_id)}))
    return render_template('doctors.html', hospital=hospital, doctors=doctors)

#view slots of doctor :
@app.route('/doctor/<doctor_id>')
def view_slots(doctor_id):
    doctor = db.doctors.find_one({'_id': ObjectId(doctor_id)})
    hospital = db.hospitals.find_one({'_id': doctor['hospital_id']})
    today = datetime.now().strftime('%Y-%m-%d')
    slots = list(db.slots.find({'doctor_id': ObjectId(doctor_id), 'booked': False, 'date': {'$gte': today}}))
    return render_template('slots.html', doctor=doctor, hospital=hospital, slots=slots)

#Booking doctor appointment
@app.route('/book/<slot_id>', methods=['GET', 'POST'])
def book_appointment(slot_id):
    slot = db.slots.find_one({'_id': ObjectId(slot_id)})
    doctor = db.doctors.find_one({'_id': slot['doctor_id']})
    hospital = db.hospitals.find_one({'_id': doctor['hospital_id']})
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        age = request.form['age']
        problem = request.form['problem']
        amount = float(request.form['amount'])
        
        if amount < doctor['fee']:
            return f"Minimum fee is ₹{doctor['fee']}"
        
        booking = {
            'slot_id': ObjectId(slot_id),
            'doctor_id': doctor['_id'],
            'hospital_id': hospital['_id'],
            'patient_name': name,
            'phone': phone,
            'age': age,
            'problem': problem,
            'amount': amount,
            'date': slot['date'],
            'time': slot['time'],
            'booked_on': datetime.now()
        }
        
        db.bookings.insert_one(booking)
        db.slots.update_one({'_id': ObjectId(slot_id)}, {'$set': {'booked': True}})
        
        return redirect(url_for('my_bookings', phone=phone))
    
    return render_template('book.html', slot=slot, doctor=doctor, hospital=hospital)

#My bookings
@app.route('/my_bookings')
def my_bookings():
    phone = request.args.get('phone')
    if phone:
        bookings = list(db.bookings.find({'phone': phone}))
        return render_template('my_bookings.html', bookings=bookings, phone=phone)
    return render_template('search_booking.html')

#Admin page login
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin':
            session['admin'] = True
            return redirect('/admin/dashboard')
        return "Wrong password"
    return render_template('admin_login.html')

#Admin dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin')
    
    hospitals = list(db.hospitals.find())
    doctors = list(db.doctors.find())
    bookings = list(db.bookings.find())
    
# Get all slots with doctor names and specification 
    all_slots = []
    for slot in db.slots.find().limit(50):
        doctor = db.doctors.find_one({'_id': slot['doctor_id']})
        all_slots.append({
            '_id': slot['_id'],
            'doctor_name': doctor['name'] if doctor else 'Unknown',
            'date': slot['date'],
            'time': slot['time'],
            'booked': slot['booked']
        })
    
    return render_template('admin.html', hospitals=hospitals, doctors=doctors, bookings=bookings, all_slots=all_slots)

#Add new hospital
@app.route('/admin/add_hospital', methods=['POST'])
def add_hospital():
    db.hospitals.insert_one({'name': request.form['name'], 'location': request.form['location']})
    return redirect('/admin/dashboard')

#Add doctor in hospital
@app.route('/admin/add_doctor', methods=['POST'])
def add_doctor():
    db.doctors.insert_one({
        'hospital_id': ObjectId(request.form['hospital_id']),
        'name': request.form['name'],
        'specialization': request.form['specialization'],
        'fee': int(request.form['fee'])
    })
    return redirect('/admin/dashboard')

#Add slot
@app.route('/admin/add_slot', methods=['POST'])
def add_slot():
    db.slots.insert_one({
        'doctor_id': ObjectId(request.form['doctor_id']),
        'date': request.form['date'],
        'time': request.form['time'],
        'booked': False
    })
    return redirect('/admin/dashboard')

# Delete hospital
@app.route('/admin/delete_hospital/<hospital_id>')
def delete_hospital(hospital_id):
    db.hospitals.delete_one({'_id': ObjectId(hospital_id)})
    return redirect('/admin/dashboard')

# Delete doctor
@app.route('/admin/delete_doctor/<doctor_id>')
def delete_doctor(doctor_id):
    db.doctors.delete_one({'_id': ObjectId(doctor_id)})
    return redirect('/admin/dashboard')

# Delete slot
@app.route('/admin/delete_slot/<slot_id>')
def delete_slot(slot_id):
    db.slots.delete_one({'_id': ObjectId(slot_id)})
    return redirect('/admin/dashboard')

# Delete booking
@app.route('/admin/delete_booking/<booking_id>')
def delete_booking(booking_id):
    booking = db.bookings.find_one({'_id': ObjectId(booking_id)})
    if booking:
        # Mark slot as available again
        db.slots.update_one(
            {'_id': booking['slot_id']},
            {'$set': {'booked': False}}
        )
        # Delete booking
        db.bookings.delete_one({'_id': ObjectId(booking_id)})
    return redirect('/admin/dashboard')

if __name__ == '__main__':
    add_sample_data()
    app.run(debug=True)