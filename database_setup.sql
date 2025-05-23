-- Create database if not exists
CREATE DATABASE IF NOT EXISTS hostel_db;
USE hostel_db;

-- Create registered_students table
CREATE TABLE IF NOT EXISTS registered_students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(15),
    dob DATE NOT NULL,
    room_preference ENUM('Single', 'Double', 'Shared') NOT NULL,
    room_number VARCHAR(10),
    guardian_name VARCHAR(100) NOT NULL,
    guardian_contact VARCHAR(15) NOT NULL,
    password VARCHAR(255) NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create admins table
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Create mess_menu table
CREATE TABLE IF NOT EXISTS mess_menu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    day VARCHAR(20) NOT NULL UNIQUE,
    breakfast TEXT NOT NULL,
    lunch TEXT NOT NULL,
    dinner TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create complaints table
CREATE TABLE complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    category ENUM('Academic', 'Facility', 'Discipline', 'Other') NOT NULL,
    description TEXT NOT NULL,
    status ENUM('Pending', 'Resolved') DEFAULT 'Pending',
    response TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES registered_students(id) ON DELETE CASCADE
);

-- Create rooms table
CREATE TABLE IF NOT EXISTS rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_number VARCHAR(10) NOT NULL UNIQUE,
    room_type ENUM('Single', 'Double', 'Shared') NOT NULL,
    status ENUM('Available', 'Occupied', 'Under Maintenance') NOT NULL DEFAULT 'Available',
    student_id INT DEFAULT NULL
);

-- Create attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    date DATE NOT NULL DEFAULT (CURRENT_DATE),
    status ENUM('Present', 'Absent') NOT NULL,
    FOREIGN KEY (student_id) REFERENCES registered_students(id) ON DELETE CASCADE
);

-- Create notifications table

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    complaint_id INT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES registered_students(id) ON DELETE CASCADE
);

-- Insert default admin
INSERT IGNORE INTO admins (email, password) VALUES ('admin@gmail.com', 'admin123');

-- Insert sample mess menu
INSERT IGNORE INTO mess_menu (day, breakfast, lunch, dinner) VALUES
('Monday', 'Idli & Sambar', 'Rice & Dal', 'Chapati & Curry'),
('Tuesday', 'Poha', 'Rajma Chawal', 'Paratha'),
('Wednesday', 'Dosa', 'Paneer & Roti', 'Dal Khichdi'),
('Thursday', 'Upma', 'Aloo Gobhi & Rice', 'Noodles'),
('Friday', 'Puri & Bhaji', 'Biryani', 'Dal & Chapati'),
('Saturday', 'Bread & Omelette', 'Chole Bhature', 'Fried Rice'),
('Sunday', 'Pancakes', 'Vegetable Pulao', 'Daal & Roti'); 


CREATE TABLE fee_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    semester VARCHAR(20) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    amount_paid DECIMAL(10,2) DEFAULT 0.00,
    due_date DATE NOT NULL,
    status ENUM('Pending', 'Paid', 'Overdue') DEFAULT 'Pending',
    payment_date DATETIME DEFAULT NULL,
    payment_method VARCHAR(50) DEFAULT NULL,
    transaction_id VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES registered_students(id),
    UNIQUE KEY unique_student_semester (student_id, semester)
);