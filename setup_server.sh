#!/bin/bash

echo "=========================================="
echo "MikroTik Credential Manager - Server Setup"
echo "Complete Linux Server Installation Script"
echo "=========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root!"
    echo "Run as a regular user with sudo privileges."
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    print_error "Cannot detect OS version"
    exit 1
fi

print_info "Detected OS: $OS $VER"
echo

# Update system
print_info "Updating system packages..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo apt update && sudo apt upgrade -y
    INSTALL_CMD="sudo apt install -y"
    MYSQL_SERVICE="mysql"
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
    if command -v dnf &> /dev/null; then
        sudo dnf update -y
        INSTALL_CMD="sudo dnf install -y"
    else
        sudo yum update -y
        INSTALL_CMD="sudo yum install -y"
    fi
    MYSQL_SERVICE="mysqld"
else
    print_warning "Unsupported OS. Trying with apt..."
    sudo apt update && sudo apt upgrade -y
    INSTALL_CMD="sudo apt install -y"
    MYSQL_SERVICE="mysql"
fi

print_status "System updated"

# Install prerequisites
print_info "Installing prerequisites..."
$INSTALL_CMD python3 python3-pip python3-venv git mysql-server curl wget nano

print_status "Prerequisites installed"

# Start and enable MySQL
print_info "Starting MySQL service..."
sudo systemctl start $MYSQL_SERVICE
sudo systemctl enable $MYSQL_SERVICE

if sudo systemctl is-active --quiet $MYSQL_SERVICE; then
    print_status "MySQL service started"
else
    print_error "Failed to start MySQL service"
    exit 1
fi

# Check if this script is run from the project directory
if [ ! -f "requirements.txt" ] || [ ! -f "main.py" ]; then
    print_error "This script must be run from the project directory!"
    echo "Please run:"
    echo "  git clone https://github.com/aksha-y/Mikrotik-Cred-Manager.git"
    echo "  cd Mikrotik-Cred-Manager"
    echo "  chmod +x setup_server.sh"
    echo "  ./setup_server.sh"
    exit 1
fi

# Run the application installer
print_info "Running application installer..."
chmod +x install.sh
./install.sh

if [ $? -eq 0 ]; then
    print_status "Application installed successfully"
else
    print_error "Application installation failed"
    exit 1
fi

# Configure firewall
print_info "Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 8000/tcp
    sudo ufw allow ssh
    echo "y" | sudo ufw enable
    print_status "UFW firewall configured"
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=8000/tcp
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --reload
    print_status "Firewalld configured"
else
    print_warning "No firewall detected. Please configure manually."
fi

# Database setup instructions
echo
echo "=========================================="
echo "🗄️  DATABASE SETUP REQUIRED"
echo "=========================================="
echo
print_warning "You need to create the MySQL database manually."
echo
echo "Run the following commands:"
echo
echo -e "${BLUE}sudo mysql -u root -p${NC}"
echo
echo "Then in the MySQL prompt, run:"
echo -e "${BLUE}CREATE DATABASE mikrotik_cred_manager;${NC}"
echo -e "${BLUE}CREATE USER 'mikrotik_user'@'localhost' IDENTIFIED BY 'your_secure_password';${NC}"
echo -e "${BLUE}GRANT ALL PRIVILEGES ON mikrotik_cred_manager.* TO 'mikrotik_user'@'localhost';${NC}"
echo -e "${BLUE}FLUSH PRIVILEGES;${NC}"
echo -e "${BLUE}EXIT;${NC}"
echo

read -p "Press Enter after you have created the database..."

# Environment configuration
print_info "Please configure your .env file..."
echo
echo "Edit the .env file with your database credentials:"
echo -e "${BLUE}nano .env${NC}"
echo
echo "Update these settings:"
echo "  DB_PASSWORD=your_secure_password"
echo "  SECRET_KEY=generate-a-random-key"
echo "  MIKROTIK_SERVICE_USER=your_mikrotik_user"
echo "  MIKROTIK_SERVICE_PASSWORD=your_mikrotik_password"
echo

read -p "Press Enter after you have configured the .env file..."

# Initialize application
print_info "Initializing application..."
source .venv/bin/activate

python init_db.py
if [ $? -eq 0 ]; then
    print_status "Database initialized"
else
    print_error "Database initialization failed"
    exit 1
fi

python fix_admin_password.py
if [ $? -eq 0 ]; then
    print_status "Admin user configured"
else
    print_error "Admin user configuration failed"
    exit 1
fi

# Ask about production deployment
echo
read -p "Do you want to set up production deployment with systemd? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    chmod +x deploy_production.sh
    ./deploy_production.sh
else
    print_info "Skipping production deployment"
    echo
    echo "To start the application manually:"
    echo -e "${BLUE}source .venv/bin/activate${NC}"
    echo -e "${BLUE}python run.py${NC}"
fi

# Final instructions
echo
echo "=========================================="
echo "🎉 SETUP COMPLETED!"
echo "=========================================="
echo
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Your MikroTik Credential Manager is ready!"
echo
echo "Access URLs:"
echo "  Local: http://localhost:8000"
echo "  Network: http://$SERVER_IP:8000"
echo
echo "Default Login:"
echo "  Username: admin"
echo "  Password: admin123"
echo
print_warning "IMPORTANT: Change the default password after first login!"
echo
echo "Useful commands:"
echo "  View logs: tail -f app.log"
echo "  Check service: sudo systemctl status mikrotik-cred-manager"
echo "  Restart service: sudo systemctl restart mikrotik-cred-manager"
echo