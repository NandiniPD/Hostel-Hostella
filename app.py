from flask import Flask, render_template, jsonify,request, redirect, url_for, flash, session
import mysql.connector,webbrowser
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import timedelta, datetime
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = "filesystem"
app.config['SESSION_FILE_DIR'] = "/tmp/flask_session"  # Use tmp directory for sessions

# Update database configuration to use environment variables
db_config = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'your_mysql_password_here'),
    'database': os.getenv('MYSQL_DB', 'hostel_db')
}

# Function to get MySQL Connection
def get_db_connection():
    try:
        print(f"Attempting to connect to database with host: {db_config['host']}, user: {db_config['user']}, database: {db_config['database']}")
        conn = mysql.connector.connect(**db_config)
        print("Database connection successful!")
        return conn
    except mysql.connector.Error as e:
        print(f"MySQL Connection Error: {str(e)}")
        if e.errno == 2003:
            print("Could not connect to MySQL server - check if host is correct and accessible")
        elif e.errno == 1045:
            print("Access denied - check username and password")
        elif e.errno == 1049:
            print("Database does not exist - check database name")
        raise
    except Exception as e:
        print(f"Unexpected error during database connection: {str(e)}")
        raise

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, email, password, role, name=None):
        self.id = id
        self.email = email
        self.password = password
        self.role = role
        self.name = name

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # First check registered students
        cursor.execute("SELECT * FROM registered_students WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            return User(str(user['id']), user['email'], user['password'], 'student', user['name'])
            
        # Then check admins
        cursor.execute("SELECT * FROM admins WHERE id = %s", (user_id,))
        admin = cursor.fetchone()
        if admin:
            return User(str(admin['id']), admin['email'], admin['password'], 'admin')
            
        return None
    finally:
        cursor.close()
        conn.close()



# Home Route (Welcome Page)
@app.route('/')
def home():
    return render_template('welcome.html')

#login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            print(f"Login attempt for email: {email}")
            try:
                conn = get_db_connection()
                print("Database connection established for login")
            except Exception as e:
                print(f"Failed to connect to database during login: {str(e)}")
                flash("Database connection error. Please try again later.", "danger")
                return redirect(url_for('login'))

            cursor = conn.cursor(dictionary=True)
            
            try:
                # First check registered students
                print("Checking registered_students table")
                cursor.execute("SELECT * FROM registered_students WHERE email = %s", (email,))
                user = cursor.fetchone()
                
                if not user:
                    print("User not found in students, checking admins table")
                    # Then check admins
                    cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
                    user = cursor.fetchone()
                
                if user:
                    print(f"User found with ID: {user['id']}")
                    if check_password_hash(user['password'], password):
                        print("Password verified successfully")
                        user_obj = User(str(user['id']), user['email'], user['password'], 
                                    'admin' if 'role' in user else 'student',
                                    user.get('name'))
                        login_user(user_obj)
                        print(f"Login successful for user: {email}")
                        
                        if 'role' in user:  # Admin
                            return redirect(url_for('admin_dashboard'))
                        else:  # Student
                            return redirect(url_for('student_dashboard'))
                    else:
                        print("Password verification failed")
                else:
                    print("No user found with provided email")
                
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login'))
                
            except mysql.connector.Error as e:
                print(f"MySQL error during login: {str(e)}")
                flash('Database error occurred. Please try again.', 'danger')
                return redirect(url_for('login'))
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('login'))
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
            
    return render_template('login.html')


# Welcome Page (Protected)
@app.route('/welcome')
def welcome():
    return render_template('welcome.html', user=current_user)

#register page
rooms = [{"number": i} for i in range(1, 91)]  # Example room numbers


# Add this function after the DB_CONFIG
def initialize_rooms():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Drop existing rooms table to start fresh
        cursor.execute("DROP TABLE IF EXISTS rooms")
        
        # Create rooms table
        cursor.execute("""
            CREATE TABLE rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                room_number VARCHAR(10) NOT NULL UNIQUE,
                room_type ENUM('Single', 'Double', 'Shared') NOT NULL,
                status ENUM('Available', 'Occupied', 'Under Maintenance') NOT NULL DEFAULT 'Available',
                student_id INT DEFAULT NULL
            )
        """)
        
        # Insert 90 rooms (1-90) with different types
        for i in range(1, 91):
            if i <= 30:
                room_type = 'Single'
            elif i <= 60:
                room_type = 'Double'
            else:
                room_type = 'Shared'
            
            cursor.execute("""
                INSERT INTO rooms (room_number, room_type, status) 
                VALUES (%s, %s, 'Available')
            """, (str(i), room_type))
        
        conn.commit()
        print("Rooms initialized successfully")
    except Exception as e:
        print(f"Error initializing rooms: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

@app.route('/get_available_rooms')
def get_available_rooms():
    room_type = request.args.get('room_type')
    if not room_type:
        return jsonify([])
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get room range based on type
        if room_type == 'Single':
            room_range = (1, 30)  # Single rooms are 1-30
        elif room_type == 'Double':
            room_range = (31, 60)  # Double rooms are 31-60
        else:  # Shared
            room_range = (61, 90)  # Shared rooms are 61-90

        # First get all rooms in the range
        cursor.execute("""
            SELECT 
                r.room_number,
                r.room_type,
                r.status,
                (SELECT COUNT(*) FROM registered_students rs WHERE rs.room_number = r.room_number) as current_occupants,
                CASE 
                    WHEN r.room_type = 'Single' THEN 1
                    WHEN r.room_type = 'Double' THEN 2
                    WHEN r.room_type = 'Shared' THEN 5
                END as max_occupants
            FROM rooms r
            WHERE r.room_type = %s
            AND r.room_number BETWEEN %s AND %s
            GROUP BY r.room_number, r.room_type, r.status
            ORDER BY CAST(r.room_number AS UNSIGNED)
        """, (room_type, room_range[0], room_range[1]))
        
        rooms = cursor.fetchall()

        # Get list of occupied rooms
        cursor.execute("""
            SELECT DISTINCT room_number 
            FROM registered_students 
            WHERE room_number IS NOT NULL
            AND room_number BETWEEN %s AND %s
        """, (room_range[0], room_range[1]))
        occupied_rooms = {str(row['room_number']) for row in cursor.fetchall()}
        
        # Format room information
        available_rooms = []
        for room in rooms:
            room_number = str(room['room_number'])
            is_occupied = room_number in occupied_rooms
            
            # Create room status text
            if room_type == 'Single':
                status_text = "Occupied" if is_occupied else "Empty"
            else:
                current_occupants = room['current_occupants'] or 0
                if current_occupants >= room['max_occupants']:
                    status_text = "Occupied"
                elif current_occupants == 0:
                    status_text = "Empty"
                else:
                    status_text = f"{current_occupants}/{room['max_occupants']} occupied"
            
            display_text = f"Room {room_number} ({status_text})"
            
            available_rooms.append({
                'room_number': room_number,
                'display_text': display_text,
                'current_occupants': room['current_occupants'] or 0,
                'max_occupants': room['max_occupants'],
                'is_available': not is_occupied if room_type == 'Single' else (room['current_occupants'] or 0) < room['max_occupants'],
                'status': status_text
            })
        
        return jsonify(available_rooms)
        
    except Exception as e:
        print(f"Error getting available rooms: {e}")
        return jsonify([])
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            phone = request.form['phone']
            dob = request.form['dob']
            guardian_name = request.form['guardian_name']
            guardian_contact = request.form['guardian_contact']
            room_preference = request.form['room_preference']
            room_number = request.form.get('room_number')
            
            # Validate required fields
            if not all([name, email, password, phone, dob, guardian_name, guardian_contact, room_preference, room_number]):
                flash("All fields are required!", "danger")
                return render_template('register.html')
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            try:
                # Check if email already exists
                cursor.execute("SELECT * FROM registered_students WHERE email = %s", (email,))
                existing_student = cursor.fetchone()
                
                if existing_student:
                    flash("Email already registered. Please use a different email.", "danger")
                    return render_template('register.html')
                
                # Check if room is still available
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM registered_students 
                    WHERE room_number = %s
                """, (room_number,))
                room_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT room_type FROM rooms WHERE room_number = %s", (room_number,))
                room = cursor.fetchone()
                
                if not room:
                    flash("Invalid room number selected.", "danger")
                    return render_template('register.html')
                
                max_occupants = 1 if room['room_type'] == 'Single' else (2 if room['room_type'] == 'Double' else 5)
                
                if room_count >= max_occupants:
                    flash("Selected room is already full. Please choose another room.", "danger")
                    return render_template('register.html')
                
                # Hash the password
                hashed_password = generate_password_hash(password)
                
                # Insert student data with room number
                cursor.execute("""
                    INSERT INTO registered_students 
                    (name, email, password, phone, dob, room_preference, guardian_name, guardian_contact, room_number) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (name, email, hashed_password, phone, dob, room_preference, guardian_name, guardian_contact, room_number))
                
                # Update room status if it becomes full
                if room_count + 1 >= max_occupants:
                    cursor.execute("UPDATE rooms SET status = 'Occupied' WHERE room_number = %s", (room_number,))
                
                conn.commit()
                flash("Registration successful! You can now log in.", "success")
                return redirect(url_for('login'))
                
            except Exception as e:
                conn.rollback()
                print(f"Database error during registration: {e}")
                flash("An error occurred during registration. Please try again.", "danger")
                return render_template('register.html')
                
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            print(f"Error during registration: {e}")
            flash("An error occurred during registration. Please try again.", "danger")
            return render_template('register.html')
    
    # For GET request, show registration form
    return render_template('register.html')




@app.route('/room_alloc')
@login_required
def room_alloc():
    if not current_user.is_authenticated:
        flash("Please login first!", "warning")
        return redirect(url_for('login'))
    
    if current_user.role != 'student':
        flash("Access denied! Please login as student.", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get the student's details including room number
        cursor.execute("""
            SELECT rs.*, r.room_type, r.status
            FROM registered_students rs
            LEFT JOIN rooms r ON rs.room_number = r.room_number
            WHERE rs.email = %s
        """, (current_user.email,))
        student = cursor.fetchone()
        
        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for('student_dashboard'))
            
        if student.get('room_number'):
            # Get roommates if room is assigned
            cursor.execute("""
                SELECT name
                FROM registered_students
                WHERE room_number = %s AND email != %s
            """, (student['room_number'], current_user.email))
            roommates = cursor.fetchall()
            
            # Get room occupancy details
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM registered_students
                WHERE room_number = %s
            """, (student['room_number'],))
            occupancy = cursor.fetchone()
            
            room_info = {
                'room_number': student['room_number'],
                'room_type': student['room_type'],
                'status': student['status'],
                'current_occupants': occupancy['count'],
                'max_occupants': 1 if student['room_type'] == 'Single' else (2 if student['room_type'] == 'Double' else 5),
                'roommate_names': [r['name'] for r in roommates] if roommates else []
            }
            
            # Update room display text
            room_info['display_status'] = f"{room_info['current_occupants']}/{room_info['max_occupants']} occupied"
                
            return render_template('room_alloc.html', room=room_info, student=student)
        else:
            flash("No room assigned yet.", "info")
            return render_template('room_alloc.html', room=None, student=student)
            
    except Exception as e:
        print(f"Error fetching room details: {e}")
        flash("Error fetching room information", "danger")
        return redirect(url_for('student_dashboard'))
        
    finally:
        cursor.close()
        conn.close()




@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != "student":
        flash("Access denied! Please login as student.", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student's details
        cursor.execute("""
            SELECT * FROM registered_students 
            WHERE id = %s
        """, (current_user.id,))
        student = cursor.fetchone()
        
        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for('login'))

        # Check if attendance is marked for today
        today = datetime.now().date()
        cursor.execute("""
            SELECT DATE(date) as marked_date 
            FROM attendance 
            WHERE student_id = %s AND DATE(date) = %s
        """, (current_user.id, today))
        
        attendance_marked = cursor.fetchone() is not None

        # Get student's complaints - handle error separately
        try:
            cursor.execute("""
                SELECT c.*, c.created_at as created_at 
                FROM complaints c
                WHERE c.student_id = %s 
                ORDER BY c.created_at DESC
            """, (current_user.id,))
            complaints = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching complaints: {e}")
            complaints = []
        
        # Get unread notifications
        try:
            cursor.execute("""
                SELECT * FROM notifications 
                WHERE student_id = %s AND is_read = FALSE
                ORDER BY created_at DESC
            """, (current_user.id,))
            notifications = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            notifications = []
            
    except Exception as e:
        print(f"Error in student dashboard: {e}")
        complaints = []
        notifications = []
        attendance_marked = False
    finally:
        cursor.close()
        conn.close()
    
    return render_template('student_dashboard.html', 
                         student=student,
                         complaints=complaints,
                         notifications=notifications,
                         attendance_marked=attendance_marked)



@app.route('/vacate_room/<room_number>', methods=['POST'])
@login_required
def vacate_room(room_number):
    if current_user.role != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Mark the room as Available
    cursor.execute("UPDATE rooms SET status = 'Available' WHERE room_number = %s", (room_number,))
    conn.commit()

    cursor.close()
    conn.close()

    flash(f"Room {room_number} is now available.", "success")
    return redirect(url_for('check_rooms'))



@app.route('/submit_complaint', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    if request.method == 'POST':
        category = request.form.get('category')
        description = request.form.get('complaint_text')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO complaints (student_id, category, description)
                VALUES (%s, %s, %s)
            """, (current_user.id, category, description))
            
            conn.commit()
            flash('Complaint submitted successfully!', 'success')
            return redirect(url_for('view_student_complaints'))
            
        except Exception as e:
            print(f"Error submitting complaint: {e}")
            flash('Error submitting complaint. Please try again.', 'danger')
            
        finally:
            cursor.close()
            conn.close()
            
    return render_template('submit_complaint.html')

@app.route('/view_student_complaints')
@login_required
def view_student_complaints():
    if current_user.role != 'student':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT c.*, rs.name as student_name 
            FROM complaints c 
            JOIN registered_students rs ON c.student_id = rs.id 
            WHERE c.student_id = %s 
            ORDER BY c.created_at DESC
        """, (current_user.id,))
        complaints = cursor.fetchall()
        
    except Exception as e:
        print(f"Error fetching complaints: {e}")
        complaints = []
        flash('Error fetching complaints.', 'danger')
        
    finally:
        cursor.close()
        conn.close()
        
    return render_template('student_complaints.html', complaints=complaints)

@app.route('/delete_complaint/<int:complaint_id>', methods=['POST'])
@login_required
def delete_complaint(complaint_id):
    if current_user.role != 'student':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify the complaint belongs to the current user
        cursor.execute("SELECT student_id FROM complaints WHERE id = %s", (complaint_id,))
        complaint = cursor.fetchone()
        
        if not complaint or complaint[0] != current_user.id:
            flash('Complaint not found or access denied!', 'danger')
            return redirect(url_for('view_student_complaints'))
            
        cursor.execute("DELETE FROM complaints WHERE id = %s", (complaint_id,))
        conn.commit()
        flash('Complaint deleted successfully!', 'success')
        
    except Exception as e:
        print(f"Error deleting complaint: {e}")
        flash('Error deleting complaint.', 'danger')
        
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('view_student_complaints'))

# Admin complaint routes
@app.route('/view_complaint')
@login_required
def view_complaint():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT c.*, rs.name as student_name 
            FROM complaints c 
            JOIN registered_students rs ON c.student_id = rs.id 
            ORDER BY c.created_at DESC
        """)
        complaints = cursor.fetchall()
        
    except Exception as e:
        print(f"Error fetching complaints: {e}")
        complaints = []
        flash('Error fetching complaints.', 'danger')
        
    finally:
        cursor.close()
        conn.close()
        
    return render_template('view_complaints.html', complaints=complaints)

@app.route('/update_complaint_status', methods=['POST'])
@login_required
def update_complaint_status():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
        
    complaint_id = request.form.get('complaint_id')
    new_status = request.form.get('status')
    response = request.form.get('response')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE complaints 
            SET status = %s, response = %s 
            WHERE id = %s
        """, (new_status, response, complaint_id))
        
        # Get student_id for notification
        cursor.execute("SELECT student_id FROM complaints WHERE id = %s", (complaint_id,))
        student_id = cursor.fetchone()[0]
        
        # Create notification
        notification_message = f"Your complaint has been {new_status.lower()}."
        if response:
            notification_message += f" Admin response: {response}"
            
        cursor.execute("""
            INSERT INTO notifications (student_id, complaint_id, message)
            VALUES (%s, %s, %s)
        """, (student_id, complaint_id, notification_message))
        
        conn.commit()
        flash('Complaint status updated successfully!', 'success')
        
    except Exception as e:
        print(f"Error updating complaint: {e}")
        flash('Error updating complaint status.', 'danger')
        conn.rollback()
        
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('view_complaint'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_authenticated:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))
        
    if current_user.role != "admin":
        flash("Access denied! Please login as admin.", "danger")
        return redirect(url_for('login'))
    
    # Get complaints data for the dashboard
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT complaints.id, registered_students.name AS student_name, 
                   complaints.complaint_text, complaints.status 
            FROM complaints 
            JOIN registered_students ON complaints.student_id = registered_students.id
        """)
        complaints = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching complaints: {e}")
        complaints = []
    finally:
        cursor.close()
        connection.close()
    
    return render_template('admin_dashboard.html', complaints=complaints)



@app.route('/view_registration')
@login_required
def view_registration():
    if current_user.role != "admin":
        flash("Access denied! Please login as admin.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all registered students with their room information
        query = """
            SELECT rs.*, r.room_type, r.status
            FROM registered_students rs
            LEFT JOIN rooms r ON rs.room_number = r.room_number
            ORDER BY rs.id DESC
        """
        cursor.execute(query)
        students = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching registered students: {e}")
        students = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('view_registration.html', students=students)



@app.route('/mark_attendance', methods=['POST'])
@login_required
def mark_attendance():
    if current_user.role != "student":
        flash("Access denied!", "danger")
        return redirect(url_for('student_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        student_id = current_user.id
        current_time = datetime.now()
        today = current_time.date()
        
        # Check if attendance is already marked for today
        cursor.execute("""
            SELECT DATE(date) as marked_date 
            FROM attendance 
            WHERE student_id = %s AND DATE(date) = %s
        """, (student_id, today))
        
        existing_attendance = cursor.fetchone()
        
        if existing_attendance:
            flash(f"You have already marked your attendance for today ({today.strftime('%Y-%m-%d')})!", "warning")
        else:
            # Try to insert attendance
            cursor.execute("""
                INSERT INTO attendance (student_id, status, date) 
                VALUES (%s, %s, %s)
            """, (student_id, 'Present', current_time))
            conn.commit()
            flash(f"Attendance marked successfully for {today.strftime('%Y-%m-%d')}!", "success")
            
    except mysql.connector.IntegrityError as e:
        conn.rollback()
        flash(f"You have already marked your attendance for today ({today.strftime('%Y-%m-%d')})!", "warning")
    except Exception as e:
        conn.rollback()
        print(f"Error marking attendance: {e}")
        flash("Error marking attendance. Please try again.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('student_dashboard'))


@app.route('/view_attendance')
@login_required
def view_attendance():
    if current_user.role != "student":
        flash("Access denied! Please login as student.", "danger")
        return redirect(url_for('login'))

    student_id = current_user.id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get the last 30 days of attendance records
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Get all attendance records for the last 30 days
        cursor.execute("""
            SELECT DATE(date) as date, status
            FROM attendance 
            WHERE student_id = %s 
            AND date >= %s
        """, (student_id, thirty_days_ago))
        
        # Create a dictionary of dates and their status
        attendance_dict = {}
        for record in cursor.fetchall():
            attendance_dict[record['date']] = record['status']
        
        # Generate all dates in the last 30 days
        all_dates = []
        current_date = datetime.now().date()
        
        # Generate dates from oldest to newest (ascending order)
        for i in range(29, -1, -1):
            date = current_date - timedelta(days=i)
            status = attendance_dict.get(date, 'Absent')
            all_dates.append({
                'date': date,
                'status': status
            })
        
    except Exception as e:
        print(f"Error fetching attendance: {e}")
        all_dates = []
    finally:
        cursor.close()
        conn.close()

    return render_template('view_attendance.html', attendance=all_dates)


@app.route('/admin/view_attendance')
@login_required
def admin_view_attendance():
    if current_user.role != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Assuming attendance table has student_id and status (Present/Absent)
    query = """
        SELECT rs.id, rs.name, COUNT(a.status) AS total_present, 
               (COUNT(a.status) / (180)) * 100 AS attendance_percentage
        FROM registered_students rs
        LEFT JOIN attendance a ON rs.id = a.student_id AND a.status = 'Present'
        GROUP BY rs.id, rs.name
        ORDER BY attendance_percentage DESC
    """
    cursor.execute(query)
    attendance_records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_view_attendence.html', attendance=attendance_records)




@app.route('/view_fee_status')
@login_required
def view_fee_status():
    if current_user.role != "admin":
        flash("Access denied! Please login as admin.", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all students with their fee status
        cursor.execute("""
            SELECT 
                rs.id,
                rs.name,
                rs.email,
                fs.semester,
                fs.total_amount,
                fs.amount_paid,
                (fs.total_amount - fs.amount_paid) as amount_due,
                fs.status as fee_status,
                fs.payment_date as last_payment_date
            FROM registered_students rs
            LEFT JOIN fee_status fs ON rs.id = fs.student_id
            ORDER BY rs.name, fs.semester
        """)
        fee_status = cursor.fetchall()

        # Get list of all students for the add fee record form
        cursor.execute("""
            SELECT DISTINCT rs.id, rs.name 
            FROM registered_students rs 
            LEFT JOIN fee_status fs ON rs.id = fs.student_id
            ORDER BY rs.name
        """)
        students = cursor.fetchall()
        
        return render_template('view_fee_status.html', 
                             fee_status=fee_status,
                             students=students)
        
    except Exception as e:
        print(f"Error fetching fee status: {e}")
        flash("Error fetching fee records", "danger")
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/add_fee_record', methods=['POST'])
@login_required
def add_fee_record():
    if current_user.role != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for('admin_dashboard'))
    
    student_id = request.form.get('student_id')
    semester = request.form.get('semester')
    total_amount = request.form.get('total_amount')
    due_date = request.form.get('due_date')
    
    if not all([student_id, semester, total_amount, due_date]):
        flash("All fields are required!", "danger")
        return redirect(url_for('view_fee_status'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if fee record already exists for this student and semester
        cursor.execute("""
            SELECT id FROM fee_status 
            WHERE student_id = %s AND semester = %s
        """, (student_id, semester))
        
        if cursor.fetchone():
            flash(f"Fee record already exists for this student in {semester}", "warning")
            return redirect(url_for('view_fee_status'))
        
        # Add new fee record
        cursor.execute("""
            INSERT INTO fee_status 
            (student_id, semester, total_amount, amount_paid, due_date, status) 
            VALUES (%s, %s, %s, 0, %s, 'Pending')
        """, (student_id, semester, total_amount, due_date))
        
        conn.commit()
        flash("Fee record added successfully!", "success")
        
    except Exception as e:
        conn.rollback()
        print(f"Error adding fee record: {e}")
        flash("Error adding fee record", "danger")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('view_fee_status'))

@app.route('/submit_fee_payment', methods=['POST'])
@login_required
def submit_fee_payment():
    if current_user.role != "student":
        flash("Access denied! Please login as student.", "danger")
        return redirect(url_for('login'))
    
    try:
        semester = request.form.get('semester')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        transaction_id = request.form.get('transaction_id', '')  # Accept any transaction ID
        
        # Basic validation
        if not all([semester, amount, payment_method]):
            flash("Please fill all required fields!", "danger")
            return redirect(url_for('fee_structure'))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash("Payment amount must be greater than 0!", "danger")
                return redirect(url_for('fee_structure'))
        except ValueError:
            flash("Invalid amount format!", "danger")
            return redirect(url_for('fee_structure'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get current fee status
            cursor.execute("""
                SELECT total_amount, amount_paid, status
                FROM fee_status 
                WHERE student_id = %s AND semester = %s
            """, (current_user.id, semester))
            
            fee_record = cursor.fetchone()
            
            if not fee_record:
                # Create new fee record if it doesn't exist
                due_date = '2024-07-15' if semester == 'Semester 1' else '2024-12-15'
                cursor.execute("""
                    INSERT INTO fee_status 
                    (student_id, semester, total_amount, amount_paid, due_date, status) 
                    VALUES (%s, %s, 50000.00, 0.00, %s, 'Pending')
                """, (current_user.id, semester, due_date))
                conn.commit()
                
                cursor.execute("""
                    SELECT total_amount, amount_paid, status
                    FROM fee_status 
                    WHERE student_id = %s AND semester = %s
                """, (current_user.id, semester))
                fee_record = cursor.fetchone()
            
            if fee_record['status'] == 'Paid':
                flash(f"Fees for {semester} are already fully paid!", "success")
                return redirect(url_for('fee_structure'))
            
            # Calculate new amount paid
            new_amount_paid = float(fee_record['amount_paid']) + amount
            if new_amount_paid > float(fee_record['total_amount']):
                remaining_fee = float(fee_record['total_amount']) - float(fee_record['amount_paid'])
                flash(f"Payment amount (₹{amount}) exceeds the remaining fee (₹{remaining_fee})", "danger")
                return redirect(url_for('fee_structure'))
            
            # Update fee status
            new_status = 'Paid' if new_amount_paid >= float(fee_record['total_amount']) else 'Pending'
            
            # Update the payment record
            cursor.execute("""
                UPDATE fee_status 
                SET amount_paid = %s,
                    status = %s,
                    payment_date = NOW(),
                    payment_method = %s,
                    transaction_id = %s
                WHERE student_id = %s AND semester = %s
            """, (new_amount_paid, new_status, payment_method, transaction_id, current_user.id, semester))
            
            # Create success notification
            success_message = f"Payment of ₹{amount} received for {semester}"
            if transaction_id:
                success_message += f" (Transaction ID: {transaction_id})"
            
            cursor.execute("""
                INSERT INTO notifications 
                (student_id, message, is_read, created_at) 
                VALUES (%s, %s, FALSE, NOW())
            """, (current_user.id, success_message))
            
            conn.commit()
            
            # Show success message with transaction details
            success_msg = f"Payment of ₹{amount} successful!"
            if payment_method != 'Cash':
                success_msg += f" Transaction ID: {transaction_id}"
            flash(success_msg, "success")
            
        except mysql.connector.Error as e:
            conn.rollback()
            print(f"Database error: {e}")
            flash("Database error occurred. Please try again.", "danger")
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error: {e}")
        flash("An error occurred. Please try again.", "danger")
    
    return redirect(url_for('fee_structure'))

@app.route('/view_room_aval')
@login_required
def view_room_aval():
    if not current_user.is_authenticated:
        flash("Please login first!", "warning")
        return redirect(url_for('login'))
    
    if current_user.role != 'admin':
        flash("Access denied! Please login as admin.", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all rooms with their occupancy details
        cursor.execute("""
            SELECT r.room_number, r.room_type, r.status,
                   COUNT(rs.id) as current_occupants,
                   GROUP_CONCAT(rs.name) as occupant_names
            FROM rooms r
            LEFT JOIN registered_students rs ON r.room_number = rs.room_number
            GROUP BY r.room_number, r.room_type, r.status
            ORDER BY CAST(r.room_number AS UNSIGNED)
        """)
        
        rooms = cursor.fetchall()
        
        # Format room information
        formatted_rooms = []
        for room in rooms:
            max_occupants = 1 if room['room_type'] == 'Single' else (2 if room['room_type'] == 'Double' else 5)
            current_occupants = room['current_occupants'] or 0
            
            room_info = {
                'room_number': room['room_number'],
                'room_type': room['room_type'],
                'status': 'Occupied' if current_occupants >= max_occupants else room['status'],
                'current_occupants': current_occupants,
                'max_occupants': max_occupants,
                'occupant_names': [name.strip() for name in room['occupant_names'].split(',')] if room['occupant_names'] else []
            }
            
            # Update room display text
            if current_occupants == 0:
                room_info['display_status'] = 'Empty'
            else:
                room_info['display_status'] = f"{current_occupants}/{max_occupants} occupied"
            
            formatted_rooms.append(room_info)
        
        return render_template('view_room_aval.html', rooms=formatted_rooms)
        
    except Exception as e:
        print(f"Error fetching rooms: {e}")
        flash("Error fetching room information", "danger")
        return redirect(url_for('admin_dashboard'))
        
    finally:
        cursor.close()
        conn.close()



@app.route('/view_menu')
@login_required
def view_menu():
    if current_user.role != "admin":
        flash("Access denied! Please login as admin.", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM mess_menu 
            ORDER BY FIELD(day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
        """)
        menu = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching menu: {e}")
        menu = []
    finally:
        cursor.close()
        conn.close()
        
    return render_template('view_menu.html', menu=menu)

@app.route('/update_menu', methods=['POST'])
def update_menu():
    day = request.form['day']
    breakfast = request.form['breakfast']
    lunch = request.form['lunch']
    dinner = request.form['dinner']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE mess_menu 
        SET breakfast=%s, lunch=%s, dinner=%s 
        WHERE day=%s
    """, (breakfast, lunch, dinner, day))
    
    conn.commit()
    conn.close()
    return redirect(url_for('view_menu'))

# Student Mess Menu Page
@app.route('/view_menu_student')
def view_menu_student():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # dictionary=True to return results as dict
    cursor.execute("""
        SELECT * FROM mess_menu 
        ORDER BY FIELD(day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
    """)
    menu = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('view_menu_student.html', menu=menu)

# API to Get Latest Mess Menu (For Auto-Refresh)
@app.route('/get_latest_mess_menu')
def get_latest_mess_menu():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM mess_menu 
        ORDER BY FIELD(day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
    """)
    menu = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({"menu": menu})

@app.route('/attendance')
@login_required
def attendance():
    return render_template('attendance.html', user=current_user)

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Forgot Password Routes
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        
        # Check if passwords match
        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('forgot_password'))
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            if role == "admin":
                if email == "admin@gmail.com":
                    flash("Admin password cannot be reset through this interface. Please contact system administrator.", "danger")
                else:
                    flash("Admin email not found.", "danger")
            else:
                # For students, check if email exists
                cursor.execute("SELECT id FROM registered_students WHERE email = %s", (email,))
                student = cursor.fetchone()
                
                if student:
                    # Hash the new password
                    hashed_password = generate_password_hash(new_password)
                    
                    # Update the password in database
                    cursor.execute("UPDATE registered_students SET password = %s WHERE id = %s", 
                                 (hashed_password, student['id']))
                    conn.commit()
                    
                    flash("Your password has been successfully reset. You can now login with your new password.", "success")
                    return redirect(url_for('login'))
                else:
                    flash("Email not found. Please check your email or register.", "danger")
        except Exception as e:
            print(f"Error in forgot_password: {e}")
            flash("An error occurred. Please try again.", "danger")
        finally:
            cursor.close()
            conn.close()
    
    return render_template('forgot_password.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/fee_structure')
@login_required
def fee_structure():
    if current_user.role != "student":
        flash("Access denied! Please login as student.", "danger")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student's fee status for only Semester 1 and Semester 2
        cursor.execute("""
            SELECT semester, total_amount, amount_paid, status, due_date
            FROM fee_status 
            WHERE student_id = %s AND semester IN ('Semester 1', 'Semester 2')
            ORDER BY semester
        """, (current_user.id,))
        student_fees = cursor.fetchall()
        
        # If no fee records exist, create them
        if not student_fees:
            try:
                # Insert fee records for both semesters
                cursor.execute("""
                    INSERT INTO fee_status 
                    (student_id, semester, total_amount, amount_paid, due_date, status, created_at, updated_at) 
                    VALUES 
                    (%s, 'Semester 1', 50000.00, 0.00, '2024-07-15', 'Pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    (%s, 'Semester 2', 50000.00, 0.00, '2024-12-15', 'Pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (current_user.id, current_user.id))
                
                conn.commit()
                
                # Fetch the newly created records
                cursor.execute("""
                    SELECT semester, total_amount, amount_paid, status, due_date
                    FROM fee_status 
                    WHERE student_id = %s AND semester IN ('Semester 1', 'Semester 2')
                    ORDER BY semester
                """, (current_user.id,))
                student_fees = cursor.fetchall()
                flash("Your fee records have been initialized.", "info")
                
            except mysql.connector.Error as e:
                conn.rollback()
                print(f"MySQL Error creating fee records: {e}")
                flash("Error initializing fee records. Please contact admin.", "danger")
                return redirect(url_for('student_dashboard'))
        
        # Fee structure data
        fee_structure = {
            'academic_year': '2024-2025',
            'semesters': [
                {
                    'name': 'Semester 1',
                    'room_rent': 25000,
                    'mess_fees': 20000,
                    'maintenance': 5000,
                    'total': 50000,
                    'due_date': '2024-07-15'
                },
                {
                    'name': 'Semester 2',
                    'room_rent': 25000,
                    'mess_fees': 20000,
                    'maintenance': 5000,
                    'total': 50000,
                    'due_date': '2024-12-15'
                }
            ],
            'payment_methods': [
                'Bank Transfer',
                'UPI',
                'Cash',
                'Cheque'
            ],
            'bank_details': {
                'bank_name': 'State Bank of India',
                'account_name': 'Hostel Management',
                'account_number': '123456789012',
                'ifsc_code': 'SBIN0001234'
            }
        }
        
        return render_template('fee_structure.html', 
                             fee_structure=fee_structure,
                             student_fees=student_fees)
                             
    except Exception as e:
        print(f"Error in fee_structure route: {str(e)}")
        flash("Database error occurred. Please try again or contact admin.", "danger")
        return redirect(url_for('student_dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/record_payment', methods=['POST'])
@login_required
def admin_record_payment():
    if current_user.role != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for('admin_dashboard'))
    
    try:
        student_id = request.form.get('student_id')
        semester = request.form.get('semester')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        transaction_id = request.form.get('transaction_id', '')
        
        if not all([student_id, semester, amount, payment_method]):
            flash("All fields are required!", "danger")
            return redirect(url_for('admin_dashboard'))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash("Payment amount must be greater than 0!", "danger")
                return redirect(url_for('admin_dashboard'))
        except ValueError:
            flash("Invalid amount format!", "danger")
            return redirect(url_for('admin_dashboard'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Check if student exists
            cursor.execute("SELECT name FROM registered_students WHERE id = %s", (student_id,))
            student = cursor.fetchone()
            if not student:
                flash("Student not found!", "danger")
                return redirect(url_for('admin_dashboard'))
            
            # Get current fee status
            cursor.execute("""
                SELECT total_amount, amount_paid, status
                FROM fee_status 
                WHERE student_id = %s AND semester = %s
            """, (student_id, semester))
            
            fee_record = cursor.fetchone()
            
            if not fee_record:
                # Create new fee record
                due_date = '2025-07-15' if semester == 'Semester 1' else '2025-12-15'
                cursor.execute("""
                    INSERT INTO fee_status 
                    (student_id, semester, total_amount, amount_paid, due_date, status) 
                    VALUES (%s, %s, 50000.00, 0.00, %s, 'Pending')
                """, (student_id, semester, due_date))
                conn.commit()
                
                cursor.execute("""
                    SELECT total_amount, amount_paid, status
                    FROM fee_status 
                    WHERE student_id = %s AND semester = %s
                """, (student_id, semester))
                fee_record = cursor.fetchone()
            
            # Calculate new amount paid
            new_amount_paid = float(fee_record['amount_paid']) + amount
            if new_amount_paid > float(fee_record['total_amount']):
                flash(f"Payment amount (₹{amount}) exceeds the remaining fee (₹{float(fee_record['total_amount']) - float(fee_record['amount_paid'])})", "danger")
                return redirect(url_for('admin_dashboard'))
            
            # Update fee status
            new_status = 'Paid' if new_amount_paid >= float(fee_record['total_amount']) else 'Pending'
            
            cursor.execute("""
                UPDATE fee_status 
                SET amount_paid = %s,
                    status = %s,
                    payment_date = NOW(),
                    payment_method = %s,
                    transaction_id = %s
                WHERE student_id = %s AND semester = %s
            """, (new_amount_paid, new_status, payment_method, transaction_id, student_id, semester))
            
            # Create notification for student
            cursor.execute("""
                INSERT INTO notifications 
                (student_id, message, is_read, created_at) 
                VALUES (%s, %s, FALSE, NOW())
            """, (student_id, f"Admin recorded payment of ₹{amount} for {semester} via {payment_method}"))
            
            conn.commit()
            flash(f"Payment of ₹{amount} recorded successfully for {student['name']}!", "success")
            
        except mysql.connector.Error as e:
            conn.rollback()
            print(f"Database error: {e}")
            flash("Database error occurred. Please try again.", "danger")
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error: {e}")
        flash("An error occurred. Please try again.", "danger")
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/payment_history')
@login_required
def admin_payment_history():
    if current_user.role != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all payment records with student details
        cursor.execute("""
            SELECT 
                rs.name as student_name,
                fs.semester,
                fs.total_amount,
                fs.amount_paid,
                fs.payment_date,
                fs.payment_method,
                fs.transaction_id,
                fs.status
            FROM fee_status fs
            JOIN registered_students rs ON fs.student_id = rs.id
            WHERE fs.payment_date IS NOT NULL
            ORDER BY fs.payment_date DESC
        """)
        payments = cursor.fetchall()
        
        # Get all students for the payment form
        cursor.execute("SELECT id, name FROM registered_students ORDER BY name")
        students = cursor.fetchall()
        
        return render_template('admin_payment_history.html', 
                             payments=payments,
                             students=students)
        
    except Exception as e:
        print(f"Error fetching payment history: {e}")
        flash("Error fetching payment records", "danger")
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/get_payment_history/<int:student_id>')
@login_required
def get_payment_history(student_id):
    if current_user.role != "admin":
        return jsonify({"error": "Access denied"}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                fs.payment_date,
                fs.amount_paid,
                fs.payment_method,
                fs.transaction_id,
                fs.status,
                fs.semester
            FROM fee_status fs
            WHERE fs.student_id = %s 
            AND fs.payment_date IS NOT NULL
            ORDER BY fs.payment_date DESC
        """, (student_id,))
        
        payments = cursor.fetchall()
        
        # Convert datetime objects to string format
        for payment in payments:
            if payment['payment_date']:
                payment['payment_date'] = payment['payment_date'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({"payments": payments})
        
    except Exception as e:
        print(f"Error fetching payment history: {e}")
        return jsonify({"error": "Failed to fetch payment history"}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)