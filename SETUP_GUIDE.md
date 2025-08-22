# 🚀 Quick Setup Guide for MikroTik Credential Manager

This guide will help you get the MikroTik Credential Manager up and running quickly.

## ⚡ Quick Start (5 minutes)

### Step 1: Prerequisites Check
Ensure you have:
- ✅ Python 3.8+ installed
- ✅ MySQL/MariaDB running
- ✅ Git installed

### Step 2: Clone and Setup
```bash
# Clone the repository
git clone https://github.com/aksha-y/Mikrotik-Cred-Manager.git
cd Mikrotik-Cred-Manager

# Create virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Database Setup
```sql
-- Connect to MySQL and run:
CREATE DATABASE mikrotik_cred_manager;
CREATE USER 'mikrotik_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON mikrotik_cred_manager.* TO 'mikrotik_user'@'localhost';
FLUSH PRIVILEGES;
```

### Step 4: Environment Configuration
Copy `.env.example` to `.env` and update:
```bash
cp .env.example .env
```

Edit `.env` with your database credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mikrotik_cred_manager
DB_USER=mikrotik_user
DB_PASSWORD=your_secure_password
```

### Step 5: Initialize Application
```bash
# Initialize database
python init_db.py

# Setup admin user
python fix_admin_password.py

# Start the application
python run.py
```

### Step 6: Access Application
- **URL:** http://127.0.0.1:8000
- **Username:** admin
- **Password:** admin123

## 🔧 MikroTik Device Configuration

Configure each MikroTik device:
```routeros
# Create service user group
/user group add name=api_service policy=api,read,write,policy,test

# Create service user
/user add name=your_service_user password=your_strong_service_password group=api_service

# Enable API service
/ip service enable api
/ip service set api port=20786
```

## 🆘 Troubleshooting

### Admin Login Issues
```bash
python check_admin.py
```

### Database Connection Issues
- Check MySQL is running: `systemctl status mysql` (Linux) or check services (Windows)
- Verify credentials in `.env` file
- Test connection: `mysql -u mikrotik_user -p mikrotik_cred_manager`

### Port Already in Use
Change port in `.env`:
```env
PORT=8001
```

## 📋 Post-Installation Checklist

- [ ] Application starts without errors
- [ ] Can login with admin credentials
- [ ] Dashboard loads correctly
- [ ] Can create test user
- [ ] MikroTik devices configured
- [ ] Test credential request works
- [ ] Changed default admin password

## 🔒 Security Recommendations

1. **Change default admin password immediately**
2. **Use strong database passwords**
3. **Enable HTTPS in production**
4. **Restrict network access**
5. **Regular security updates**

## 📞 Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review logs: `tail -f app.log`
- Create an issue on GitHub
- Contact: akshayvankariant@gmail.com