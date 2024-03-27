from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

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
def landing():
    if 'username' in session:
        conn = sqlite3.connect('medicine.db')
        c = conn.cursor()
        c.execute("SELECT * FROM medicines")
        medicines = c.fetchall()
        conn.close()
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
    return medicines

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
        
        # Update global variable with latest medicines
        global medicines
        medicines = fetch_medicines()
        
        return redirect('/landing')
    else:
        return redirect('/')

# Route for logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')

if __name__ == '__main__':
    create_table()
    app.run(debug=True)
