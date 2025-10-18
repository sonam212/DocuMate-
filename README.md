# DocuMate - Document Management System

A comprehensive Flask-based web application for managing personal and family documents with automated expiration reminders via email.

## Features

### Core Functionality
- **User Authentication**: Secure login/registration with password hashing
- **Document Upload**: Upload PDF documents with metadata (title, description, expiry date)
- **Document Management**: View, search, preview, and delete documents
- **Expiration Tracking**: Automatic status tracking (active, expiring, expired)
- **Email Reminders**: Automated email notifications for document expirations
- **Family Mode**: Manage documents for multiple family members
- **Dashboard**: Overview of document counts, recent uploads, and upcoming reminders
- **Calendar View**: Visual calendar showing document expiry dates

### Technical Features
- **Database**: MySQL with user-scoped data
- **Email Integration**: SMTP-based email sending for reminders
- **Background Scheduling**: APScheduler for daily reminder checks
- **File Security**: Ownership checks and secure file serving
- **Responsive UI**: Bootstrap-based interface
- **Error Handling**: Custom 404/500 error pages

## Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL Server
- Git

### 1. Clone Repository
```bash
git clone <repository-url>
cd documate
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Create a `.env` file in the root directory:
```env
# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=documate

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Flask Configuration
SECRET_KEY=your_secret_key_here
```

### 5. Setup MySQL Database
1. Start MySQL server
2. Create database: `CREATE DATABASE documate;`
3. Run the SQL scripts in order:
   ```bash
   mysql -u root -p documate < create_tables.sql
   mysql -u root -p documate < alter_tables.sql
   ```

### 6. Run the Application
```bash
python app.py
```
Access at: http://127.0.0.1:5000

## Usage

### First Time Setup
1. Register a new account at `/register` (includes email OTP verification)
2. Login at `/login`
3. Upload your first document at `/upload`

### Key Routes
- `/` - Home page
- `/upload` - Upload and manage documents
- `/dashboard` - View statistics and recent activity
- `/calendar` - Calendar view of expirations
- `/family_mode` - Manage family members
- `/profile` - Update profile and notification preferences
- `/test-reminders` - Manually trigger reminder check (for testing)

### Email Setup
For Gmail:
1. Enable 2-factor authentication
2. Generate an App Password
3. Use the App Password in `.env` EMAIL_PASSWORD

## Project Structure

```
documate/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── static/
│   ├── style.css         # CSS styles
│   └── uploads/          # Uploaded documents
├── templates/            # Jinja2 templates
│   ├── layout.html       # Base template
│   ├── home.html         # Home page
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   ├── upload.html       # Upload/manage documents
│   ├── dashboard.html    # Dashboard
│   ├── calendar.html     # Calendar view
│   ├── family_mode.html  # Family management
│   ├── profile.html      # User profile
│   ├── preview.html      # Document preview
│   ├── 404.html          # Error page
│   └── 500.html          # Error page
└── SQL Scripts/
    ├── create_tables.sql # Database schema
    ├── alter_tables.sql  # Schema updates
    └── recreate_tables.sql # Full recreate
```

## Database Schema

### Tables
- `users` - User accounts
- `documents` - Uploaded documents
- `reminders` - Scheduled reminders
- `user_notification_preferences` - User email preferences
- `family_members` - Family member profiles

## Security Features

- Password hashing with Werkzeug
- Session-based authentication
- File ownership validation
- SQL injection prevention with parameterized queries
- CSRF protection via Flask-WTF (if extended)
- File type and size restrictions

## Development

### Running in Debug Mode
Set `app.run(debug=True)` in app.py for development features.

### Testing Email
Use `/test-reminders` route to manually trigger reminder checks.

### Adding New Features
1. Add routes in app.py
2. Create corresponding templates in templates/
3. Update database schema if needed
4. Test thoroughly

## Troubleshooting

### Common Issues
1. **Email not sending**: Check SMTP credentials and Gmail app password
2. **Database connection**: Verify MySQL is running and credentials are correct
3. **File upload fails**: Check file size (max 16MB) and type (PDF only)
4. **Reminders not working**: Ensure APScheduler is running (check console logs)

### Logs
Application logs are printed to console. Set logging level in app.py for more details.

## Future Enhancements

- [ ] Document categories/tags
- [ ] Bulk upload functionality
- [ ] Document sharing between users
- [ ] Mobile app companion
- [ ] Advanced search and filtering
- [ ] Document OCR for text search
- [ ] Backup and restore functionality
- [ ] Multi-language support

## License

This project is for educational purposes. Modify and distribute as needed.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Submit a pull request

## Support

For issues or questions, please check the troubleshooting section or create an issue in the repository.
