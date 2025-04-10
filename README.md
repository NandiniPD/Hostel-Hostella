# Hostella - Hostel Management System

A Flask-based web application for managing hostel operations including room allocation, student registration, and complaint management.

## Features

- Student Registration and Login
- Room Allocation System
- Complaint Management
- Attendance Tracking
- Admin Dashboard
- Mess Menu Management

## CI/CD Pipeline Implementation

This project implements a complete CI/CD pipeline using GitHub Actions and Render.

### Continuous Integration (CI)
- Automated testing on every push and pull request
- Code linting with flake8
- Unit tests with pytest
- Code coverage reporting
- Dependency caching for faster builds

### Continuous Deployment (CD)
- Automatic deployment to Render on successful merge to main branch
- Environment variable management
- Database configuration management
- Zero-downtime deployments

### Pipeline Stages
1. **Test Stage**
   - Install dependencies
   - Run linting checks
   - Execute unit tests
   - Generate coverage reports

2. **Deploy Stage**
   - Triggered on main branch
   - Deploys to Render
   - Verifies deployment success

### Environment Variables
Required secrets in GitHub:
- `RENDER_API_KEY`
- `RENDER_SERVICE_ID`

Required environment variables in Render:
- `MYSQL_HOST`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DB`
- `PORT`

## Development

### Local Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest`
4. Start server: `python app.py`

### Making Changes
1. Create a new branch
2. Make changes
3. Run tests locally
4. Create pull request
5. Wait for CI checks to pass
6. Merge to main for automatic deployment

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