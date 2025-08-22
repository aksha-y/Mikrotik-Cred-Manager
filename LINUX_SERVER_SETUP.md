# 🐧 Linux Server Setup Guide - MikroTik Credential Manager

Complete step-by-step guide for deploying on cloud-based Linux servers (Ubuntu/Debian/CentOS).

## 🚀 Prerequisites Installation

### Step 1: Update System
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL/Rocky Linux
sudo yum update -y
# OR for newer versions
sudo dnf update -y
```

### Step 2: Install Required Packages
```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git mysql-server curl wget

# CentOS/RHEL/Rocky Linux
sudo yum install -y python3 python3-pip git mysql-server curl wget
# OR for newer versions
sudo dnf install -y python3 python3-pip git mysql-server curl wget
```

### Step 3: Start and Enable MySQL
```bash
# Start MySQL service
sudo systemctl start mysql
# OR for MariaDB
sudo systemctl start mariadb

# Enable MySQL to start on boot
sudo systemctl enable mysql
# OR for MariaDB
sudo systemctl enable mariadb

# Check MySQL status
sudo systemctl status mysql
```

### Step 4: Secure MySQL Installation
```bash
sudo mysql_secure_installation
```
**Follow the prompts:**
- Set root password: `Yes` (choose a strong password)
- Remove anonymous users: `Yes`
- Disallow root login remotely: `Yes`
- Remove test database: `Yes`
- Reload privilege tables: `Yes`

## 📥 Application Installation

### Step 5: Clone Repository
```bash
# Navigate to desired directory (e.g., /opt or /home/username)
cd /opt

# Clone the repository
sudo git clone https://github.com/aksha-y/Mikrotik-Cred-Manager.git

# Change ownership to current user (replace 'username' with your username)
sudo chown -R $USER:$USER Mikrotik-Cred-Manager

# Navigate to project directory
cd Mikrotik-Cred-Manager

# Verify files are present
ls -la
```

### Step 6: Run Automated Installation
```bash
# Make installation script executable
chmod +x install.sh

# Run the installation script
./install.sh
```

**The script will:**
- ✅ Check Python installation
- ✅ Create virtual environment
- ✅ Install Python dependencies
- ✅ Create .env file from template

## 🗄️ Database Setup

### Step 7: Create MySQL Database
```bash
# Login to MySQL as root
sudo mysql -u root -p

# Create database and user (run these commands in MySQL prompt)
CREATE DATABASE mikrotik_cred_manager;
CREATE USER 'mikrotik_user'@'localhost' IDENTIFIED BY 'your_secure_password_here';
GRANT ALL PRIVILEGES ON mikrotik_cred_manager.* TO 'mikrotik_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 8: Configure Environment
```bash
# Edit the .env file
nano .env
# OR use vim
vim .env
```

**Update these critical settings:**
```env
# Database settings
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mikrotik_cred_manager
DB_USER=mikrotik_user
DB_PASSWORD=your_secure_password_here

# Security settings
SECRET_KEY=generate-a-long-random-secret-key-here
HOST=0.0.0.0
PORT=8000
DEBUG=false
SECURE_COOKIES=true

# MikroTik settings (update with your actual credentials)
MIKROTIK_SERVICE_USER=your_mikrotik_service_user
MIKROTIK_SERVICE_PASSWORD=your_mikrotik_service_password
MIKROTIK_API_PORT=20786
```

**Generate a secure secret key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 9: Initialize Application
```bash
# Activate virtual environment
source .venv/bin/activate

# Initialize database
python init_db.py

# Setup admin user
python fix_admin_password.py

# Verify admin account
python check_admin.py
```

## 🔥 Firewall Configuration

### Step 10: Configure Firewall
```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 8000/tcp
sudo ufw allow ssh
sudo ufw --force enable

# CentOS/RHEL/Rocky Linux (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload

# Verify firewall status
sudo ufw status
# OR
sudo firewall-cmd --list-all
```

## 🚀 Application Deployment

### Step 11: Test Application
```bash
# Activate virtual environment
source .venv/bin/activate

# Start application in test mode
python run.py
```

**Test access:**
- Open browser: `http://your-server-ip:8000`
- Login: `admin` / `admin123`

**Stop test server:** Press `Ctrl+C`

### Step 12: Production Deployment with Systemd

Create systemd service file:
```bash
sudo nano /etc/systemd/system/mikrotik-cred-manager.service
```

**Service file content:**
```ini
[Unit]
Description=MikroTik Credential Manager
After=network.target mysql.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/Mikrotik-Cred-Manager
Environment=PATH=/opt/Mikrotik-Cred-Manager/.venv/bin
ExecStart=/opt/Mikrotik-Cred-Manager/.venv/bin/python run.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**Replace `your-username` with your actual username:**
```bash
whoami
```

**Enable and start service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable mikrotik-cred-manager

# Start service
sudo systemctl start mikrotik-cred-manager

# Check status
sudo systemctl status mikrotik-cred-manager

# View logs
sudo journalctl -u mikrotik-cred-manager -f
```

## 🔒 SSL/HTTPS Setup (Optional but Recommended)

### Step 13: Install Nginx and SSL
```bash
# Install Nginx
sudo apt install nginx -y  # Ubuntu/Debian
sudo yum install nginx -y  # CentOS/RHEL

# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y  # Ubuntu/Debian
sudo yum install certbot python3-certbot-nginx -y  # CentOS/RHEL

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/mikrotik-cred-manager
```

**Nginx configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable site and get SSL:**
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/mikrotik-cred-manager /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Get SSL certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com

# Test SSL renewal
sudo certbot renew --dry-run
```

## ✅ Verification Checklist

### Step 14: Final Verification
```bash
# Check service status
sudo systemctl status mikrotik-cred-manager

# Check if port is listening
sudo netstat -tlnp | grep :8000

# Check application logs
tail -f /opt/Mikrotik-Cred-Manager/app.log

# Test database connection
mysql -u mikrotik_user -p mikrotik_cred_manager -e "SHOW TABLES;"
```

**Access application:**
- **HTTP:** `http://your-server-ip:8000`
- **HTTPS:** `https://your-domain.com` (if SSL configured)
- **Login:** `admin` / `admin123`

## 🔧 Maintenance Commands

### Useful Commands for Management
```bash
# View service logs
sudo journalctl -u mikrotik-cred-manager -f

# Restart service
sudo systemctl restart mikrotik-cred-manager

# Stop service
sudo systemctl stop mikrotik-cred-manager

# Update application
cd /opt/Mikrotik-Cred-Manager
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart mikrotik-cred-manager

# Backup database
mysqldump -u mikrotik_user -p mikrotik_cred_manager > backup_$(date +%Y%m%d_%H%M%S).sql
```

## 🆘 Troubleshooting

### Common Issues and Solutions

**Service won't start:**
```bash
sudo journalctl -u mikrotik-cred-manager -n 50
```

**Database connection issues:**
```bash
mysql -u mikrotik_user -p
```

**Port already in use:**
```bash
sudo netstat -tlnp | grep :8000
sudo kill -9 <PID>
```

**Permission issues:**
```bash
sudo chown -R $USER:$USER /opt/Mikrotik-Cred-Manager
```

## 📞 Support

- **GitHub Issues:** https://github.com/aksha-y/Mikrotik-Cred-Manager/issues
- **Email:** akshayvankariant@gmail.com

---

**🎉 Your MikroTik Credential Manager is now running on your Linux server!**