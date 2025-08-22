#!/bin/bash

echo "========================================"
echo "MikroTik Credential Manager Installer"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ first"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to create virtual environment"
    exit 1
fi

echo "✅ Virtual environment created"
echo

# Activate virtual environment and install dependencies
echo "Installing dependencies..."
source .venv/bin/activate
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo
    echo "⚠️  IMPORTANT: Please edit .env file with your database credentials"
    echo "   before running the application."
    echo
fi

# Make scripts executable
chmod +x install.sh

echo "========================================"
echo "Installation completed successfully!"
echo "========================================"
echo
echo "Next steps:"
echo "1. Edit .env file with your database credentials"
echo "2. Create MySQL database: mikrotik_cred_manager"
echo "3. Run: python init_db.py"
echo "4. Run: python fix_admin_password.py"
echo "5. Run: python run.py"
echo
echo "Default login: admin / admin123"
echo "URL: http://127.0.0.1:8000"
echo