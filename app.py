from flask import Flask, render_template, request, redirect, session, send_from_directory
import sqlite3
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import schedule
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)

# For images
@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

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
        update_days_remaining()
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

        c.execute("SELECT * FROM medicines WHERE days_remaining > 0 ORDER BY " + order_by)  # Exclude expired medicines
        medicines = c.fetchall()
        conn.close()

        # Calculate number of days until expiry for each medicine
        today = datetime.now().date()

        # Initialize variables to store details of expiring medicines
        expiring_medicines = []
        expired_medicines = []

        for med in medicines:
            expiry_date = datetime.strptime(med[2], '%Y-%m-%d').date()
            med_days_until_expiry = (expiry_date - today).days
            med = med[:4] + (med_days_until_expiry,) + med[4:]

            # Check if medicine's expiry is within specified range
            if med_days_until_expiry in [10, 5, 4, 3, 2, 1]:
                expiring_medicines.append(med)

            # Check if medicine has already expired
            if med[4] < 0:
                expired_medicines.append(med)

        # Prepare message body for expiring medicines
        expiring_message = ""
        for med in expiring_medicines:
            expiring_message += f"- {med[1]} is expiring in {med[4]} days.\n"

        # Prepare message body for expired medicines
        expired_message = ""
        for med in expired_medicines:
            expired_message += f"- {med[1]} has already expired.\n"

        # Concatenate expiring and expired messages
        message_body = ""
        if expiring_message:
            message_body += "Medicines Expiring Soon:\n" + expiring_message + "\n"
        if expired_message:
            message_body += "Expired Medicines:\n" + expired_message + "\n"

        # Send email with concatenated message body
        current_time = datetime.now()
        if current_time.hour == 11 and current_time.minute == 21:
            if message_body:
                send_mail("Medicine Expiry Alert", message_body, ['ashishjoshi2021.it@mmcoe.edu.in', 'atharvaphadke2021.it@mmcoe.edu.in', 'soahammohaadkar2021.it@mmcoe.edu.in'])

        return render_template('landing.html', medicines=medicines, username=session['username'])

    else:
        return redirect('/')

# Route for expired medicines page
@app.route('/expired_medicines')
def expired_medicines():
    if 'username' in session:
        conn = sqlite3.connect('medicine.db')
        c = conn.cursor()
        c.execute("SELECT * FROM medicines WHERE days_remaining < 0")
        expired_medicines = c.fetchall()
        conn.close()
        return render_template('expired_medicines.html', expired_medicines=expired_medicines, username=session['username'])
    else:
        return redirect('/')

# Route to add medicine info    
@app.route('/add_info', methods=['POST'])
def add_info():
    if 'username' in session:
        name = request.form['medicineName']
        expiry_date = request.form['expiryDate']
        installation_date = request.form['installationDate']
        quantity = request.form['medicineQuantity']
        conn = sqlite3.connect('medicine.db')
        c = conn.cursor()
        c.execute("INSERT INTO medicines (name, expiry_date, installation_date, quantity) VALUES (?, ?, ?, ?)",
                  (name, expiry_date, installation_date, quantity))
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


# Route to update medicine info
@app.route('/update_info/<int:medicine_id>', methods=['POST'])
def update_info(medicine_id):
    if 'username' in session:
        if request.method == 'POST':
            name = request.form['medicineName']
            expiry_date = request.form['expiryDate']
            installation_date = request.form['installationDate']
            quantity = request.form['medicineQuantity']
            conn = sqlite3.connect('medicine.db')
            c = conn.cursor()
            c.execute("UPDATE medicines SET name=?, expiry_date=?, installation_date=?, quantity=? WHERE id=?",
                      (name, expiry_date, installation_date, quantity, medicine_id))
            conn.commit()
            conn.close()

            # Update days remaining for all medicines
            update_days_remaining()

            return redirect('/landing')
    else:
        return redirect('/')

# Route for logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')    

# Function to create database table
def create_table():
    conn = sqlite3.connect('medicine.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS medicines
                 (id INTEGER PRIMARY KEY, name TEXT, expiry_date TEXT, installation_date TEXT, quantity INTEGER)''')
    conn.commit()
    conn.close()

# Fetch all medicines from the database
def fetch_medicines():
    conn = sqlite3.connect('medicine.db')
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    medicines = c.fetchall()
    conn.close()

# Update Days to Expiry
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

# Function to send email
def send_mail(subject, message, to_email):
    from_email = 'itfakms@gmail.com'
    password = 'mlnk pftp ejui jznw'

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = ', '.join(to_email)
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print("Error sending email:", str(e))

# Function to check and send email at 11 PM
def check_and_send_email():
    current_time = datetime.now().time()
    if current_time.hour == 11   and current_time.minute == 21:
        print("Checking medicines and sending email...")
        # Update days remaining for all medicines
        update_days_remaining()

        # Fetch all medicines
        conn = sqlite3.connect('medicine.db')
        c = conn.cursor()
        c.execute("SELECT * FROM medicines")
        medicines = c.fetchall()
        conn.close()

        # Calculate number of days until expiry for each medicine
        today = datetime.now().date()

        # Initialize variables to store details of expiring medicines
        expiring_medicines = []
        expired_medicines = []

        for med in medicines:
            expiry_date = datetime.strptime(med[2], '%Y-%m-%d').date()
            med_days_until_expiry = (expiry_date - today).days
            med = med[:4] + (med_days_until_expiry,) + med[4:]

            # Check if medicine's expiry is within specified range
            if med_days_until_expiry in [10, 5, 4, 3, 2, 1]:
                expiring_medicines.append(med)

            # Check if medicine has already expired
            if med[4] < 0:
                expired_medicines.append(med)

        # Prepare message body for expiring medicines
        expiring_message = ""
        for med in expiring_medicines:
            expiring_message += f"- {med[1]} is expiring in {med[4]} days.\n"

        # Prepare message body for expired medicines
        expired_message = ""
        for med in expired_medicines:
            expired_message += f"- {med[1]} has already expired.\n"

        # Concatenate expiring and expired messages
        message_body = ""
        if expiring_message:
            message_body += "Medicines Expiring Soon:\n" + expiring_message + "\n"
        if expired_message:
            message_body += "Expired Medicines:\n" + expired_message + "\n"

        # Send email with concatenated message body
        if message_body:
            send_mail("Medicine Expiry Alert", message_body, ['ashishjoshi2021.it@mmcoe.edu.in', 'atharvaphadke2021.it@mmcoe.edu.in', 'soahammohaadkar2021.it@mmcoe.edu.in'])

        print("Email sent.")

# Schedule email check every minute
schedule.every().day.at("11:21").do(check_and_send_email)

# Run the scheduler in a separate thread
def scheduler_thread():
    while True:
        schedule.run_pending()
        time.sleep(1)

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

if __name__ == '__main__':
    create_table()
    # Start scheduler thread
    import threading
    threading.Thread(target=scheduler_thread, daemon=True).start()
    app.run(debug=True)