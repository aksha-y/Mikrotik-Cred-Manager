#!/bin/bash

echo "=========================================="
echo "MikroTik Credential Manager - Production Deployment"
echo "=========================================="
echo

# Get current user and working directory
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

echo "Current user: $CURRENT_USER"
echo "Installation directory: $CURRENT_DIR"
echo

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ ERROR: Do not run this script as root!"
    echo "Run as a regular user with sudo privileges."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please run the installation script first: ./install.sh"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d .venv ]; then
    echo "❌ ERROR: Virtual environment not found!"
    echo "Please run the installation script first: ./install.sh"
    exit 1
fi

echo "Creating systemd service file..."

# Create systemd service file
sudo tee /etc/systemd/system/mikrotik-cred-manager.service > /dev/null <<EOF
[Unit]
Description=MikroTik Credential Manager
After=network.target mysql.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/.venv/bin
ExecStart=$CURRENT_DIR/.venv/bin/python run.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd service file created"

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
echo "Enabling service..."
sudo systemctl enable mikrotik-cred-manager

# Start service
echo "Starting service..."
sudo systemctl start mikrotik-cred-manager

# Wait a moment for service to start
sleep 3

# Check service status
echo "Checking service status..."
if sudo systemctl is-active --quiet mikrotik-cred-manager; then
    echo "✅ Service is running successfully!"
    
    # Show service status
    sudo systemctl status mikrotik-cred-manager --no-pager -l
    
    echo
    echo "=========================================="
    echo "🎉 Production deployment completed!"
    echo "=========================================="
    echo
    echo "Service management commands:"
    echo "  Start:   sudo systemctl start mikrotik-cred-manager"
    echo "  Stop:    sudo systemctl stop mikrotik-cred-manager"
    echo "  Restart: sudo systemctl restart mikrotik-cred-manager"
    echo "  Status:  sudo systemctl status mikrotik-cred-manager"
    echo "  Logs:    sudo journalctl -u mikrotik-cred-manager -f"
    echo
    echo "Application should be accessible at:"
    echo "  Local: http://localhost:8000"
    echo "  Network: http://$(hostname -I | awk '{print $1}'):8000"
    echo
    echo "Default login: admin / admin123"
    echo "⚠️  Remember to change the default password!"
    echo
else
    echo "❌ ERROR: Service failed to start!"
    echo "Check the logs with: sudo journalctl -u mikrotik-cred-manager -n 50"
    exit 1
fi