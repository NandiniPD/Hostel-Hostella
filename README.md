# Hostel Management System

A Flask-based web application for managing hostel operations including room allocation, student registration, and complaint management.

## Features

- Student Registration and Login
- Room Allocation System
- Complaint Management
- Attendance Tracking
- Admin Dashboard
- Mess Menu Management

## Setup Instructions

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up MySQL database and update the database configuration in `app.py`
4. Run the application:
   ```bash
   python app.py
   ```

## CI/CD Pipeline

This project uses GitHub Actions for Continuous Integration and Continuous Deployment. The pipeline:

1. Runs on every push to main branch and pull requests
2. Sets up Python environment
3. Installs dependencies
4. Runs tests with pytest
5. Generates and uploads coverage reports

## Testing

Run tests using:
```bash
pytest test_app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 