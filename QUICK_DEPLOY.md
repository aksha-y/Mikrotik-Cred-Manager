# ⚡ Quick Deploy Commands - Linux Server

## 🚀 One-Command Complete Setup

```bash
# Complete server setup (Ubuntu/Debian/CentOS/RHEL)
git clone https://github.com/aksha-y/Mikrotik-Cred-Manager.git
cd Mikrotik-Cred-Manager
chmod +x setup_server.sh
./setup_server.sh
```

**This single script does EVERYTHING:**
- ✅ Updates system packages
- ✅ Installs Python, MySQL, Git, and all dependencies
- ✅ Creates virtual environment
- ✅ Installs Python packages
- ✅ Configures firewall (port 8000)
- ✅ Guides database setup
- ✅ Initializes application
- ✅ Sets up production systemd service (optional)

## 📋 Manual Step-by-Step (If you prefer control)

### 1. System Preparation
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git mysql-server

# CentOS/RHEL/Rocky Linux
sudo dnf update -y  # or: sudo yum update -y
sudo dnf install -y python3 python3-pip git mysql-server  # or: sudo yum install -y
```

### 2. MySQL Setup
```bash
sudo systemctl start mysql
sudo systemctl enable mysql
sudo mysql_secure_installation
```

### 3. Application Setup
```bash
git clone https://github.com/aksha-y/Mikrotik-Cred-Manager.git
cd Mikrotik-Cred-Manager
chmod +x install.sh
./install.sh
```

### 4. Database Creation
```bash
sudo mysql -u root -p
```
```sql
CREATE DATABASE mikrotik_cred_manager;
CREATE USER 'mikrotik_user'@'localhost' IDENTIFIED BY 'YourSecurePassword123!';
GRANT ALL PRIVILEGES ON mikrotik_cred_manager.* TO 'mikrotik_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. Environment Configuration
```bash
nano .env
```
Update:
```env
DB_PASSWORD=YourSecurePassword123!
SECRET_KEY=your-super-secret-key-here
```

### 6. Application Initialization
```bash
source .venv/bin/activate
python init_db.py
python fix_admin_password.py
```

### 7. Firewall Configuration
```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp
sudo ufw --force enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 8. Start Application
```bash
# Test mode
python run.py

# Production mode (systemd service)
chmod +x deploy_production.sh
./deploy_production.sh
```

## 🌐 Access Your Application

- **URL:** `http://your-server-ip:8000`
- **Username:** `admin`
- **Password:** `admin123`

## 🔧 Production Management Commands

```bash
# Service management
sudo systemctl start mikrotik-cred-manager
sudo systemctl stop mikrotik-cred-manager
sudo systemctl restart mikrotik-cred-manager
sudo systemctl status mikrotik-cred-manager

# View logs
sudo journalctl -u mikrotik-cred-manager -f
tail -f app.log

# Update application
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart mikrotik-cred-manager
```

## 🆘 Troubleshooting

### Service won't start:
```bash
sudo journalctl -u mikrotik-cred-manager -n 50
```

### Database connection issues:
```bash
mysql -u mikrotik_user -p mikrotik_cred_manager
```

### Port already in use:
```bash
sudo netstat -tlnp | grep :8000
```

### Check if MySQL is running:
```bash
sudo systemctl status mysql
```

## 🔒 Security Checklist

- [ ] Changed default admin password
- [ ] Used strong database password
- [ ] Generated secure SECRET_KEY
- [ ] Configured firewall properly
- [ ] Set up SSL/HTTPS (for production)
- [ ] Regular backups configured

---

**🎉 Your MikroTik Credential Manager is now running on your Linux server!**