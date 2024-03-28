from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Function to create database table
def create_table():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
    conn.commit()
    conn.close()

# Function to check if username and password match
def check_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    if user and user[2] == password:
        return True
    return False

# Function to check if username exists
def check_username(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user

# Route for login page
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if check_user(username, password):
            session['username'] = username
            return redirect('/landing')
        else:
            return render_template('login.html', message="Username or password is incorrect.")
    return render_template('login.html', message="")

# Route for signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password == confirm_password:
            if not check_username(username):
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                conn.close()
                session['username'] = username
                return redirect('/landing')
            else:
                return render_template('signup.html', message="Username already exists. Please choose another username.")
        else:
            return render_template('signup.html', message="Password and confirm password do not match.")
    return render_template('signup.html', message="")

# Route for landing page
@app.route('/landing')
# Route for landing page
@app.route('/landing')
def landing():
    if 'username' in session:
        conn = sqlite3.connect('medicine.db')
        c = conn.cursor()

        # Get sorting parameters
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')

        # Construct SQL query based on sorting parameters
        if sort_by == 'name':
            order_by = 'name ' + sort_order
        elif sort_by == 'expiry_date':
            order_by = 'expiry_date ' + sort_order
        elif sort_by == 'installation_date':
            order_by = 'installation_date ' + sort_order
        elif sort_by == 'days_remaining':
            order_by = 'days_remaining ' + sort_order
        else:
            order_by = 'name ASC'  # Default sorting

        c.execute("SELECT * FROM medicines ORDER BY " + order_by)
        medicines = c.fetchall()
        conn.close()

        # Calculate number of days until expiry for each medicine
        today = datetime.now().date()
        for med in medicines:
            expiry_date = datetime.strptime(med[2], '%Y-%m-%d').date()
            med_days_until_expiry = (expiry_date - today).days
            med = med[:4] + (med_days_until_expiry,) + med[4:]

        return render_template('landing.html', medicines=medicines, username=session['username'])
    else:
        return redirect('/')

# Function to create database table
def create_table():
    conn = sqlite3.connect('medicine.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS medicines
                 (id INTEGER PRIMARY KEY, name TEXT, expiry_date TEXT, installation_date TEXT, status TEXT)''')
    conn.commit()
    conn.close()

# Fetch all medicines from the database
def fetch_medicines():
    conn = sqlite3.connect('medicine.db')
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    medicines = c.fetchall()
    conn.close()

def update_days_remaining():
    conn = sqlite3.connect('medicine.db')
    c = conn.cursor()
    c.execute("SELECT id, expiry_date FROM medicines")
    medicines = c.fetchall()

    # Get current date
    today = datetime.now().date()

    # Update days remaining for each medicine
    for med_id, expiry_date in medicines:
        expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        days_remaining = (expiry_date - today).days
        c.execute("UPDATE medicines SET days_remaining = ? WHERE id = ?", (days_remaining, med_id))

    # Commit changes and close connection
    conn.commit()
    conn.close()

# Route to add medicine info
@app.route('/add_info', methods=['POST'])
def add_info():
    if 'username' in session:
        name = request.form['medicineName']
        expiry_date = request.form['expiryDate']
        installation_date = request.form['installationDate']
        status = request.form['medicineStatus']
        conn = sqlite3.connect('medicine.db')
        c = conn.cursor()
        c.execute("INSERT INTO medicines (name, expiry_date, installation_date, status) VALUES (?, ?, ?, ?)",
                  (name, expiry_date, installation_date, status))
        conn.commit()
        conn.close()

        # Update days remaining for all medicines
        update_days_remaining()

        return redirect('/landing')
    else:
        return redirect('/')

# Route to delete medicine info
@app.route('/delete_info/<int:medicine_id>', methods=['POST'])
def delete_info(medicine_id):
    if 'username' in session:
        conn = sqlite3.connect('medicine.db')
        c = conn.cursor()
        c.execute("DELETE FROM medicines WHERE id=?", (medicine_id,))
        conn.commit()
        conn.close()

        return redirect('/landing')
    else:
        return redirect('/')
    

# Route for updating medicine information
@app.route('/update_info/<int:medicine_id>', methods=['POST'])
def update_info(medicine_id):
    if request.method == 'POST':
        name = request.form['medicineName']
        expiry_date = request.form['expiryDate']
        installation_date = request.form['installationDate']
        status = request.form['medicineStatus']
        conn = sqlite3.connect('medicine.db')
        c = conn.cursor()
        c.execute("UPDATE medicines SET name=?, expiry_date=?, installation_date=?, status=? WHERE id=?",
                (name, expiry_date, installation_date, status, medicine_id))
        conn.commit()
        conn.close()

        return redirect('/landing')


# Route for logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')

if __name__ == '__main__':
    create_table()
    app.run(debug=True)
