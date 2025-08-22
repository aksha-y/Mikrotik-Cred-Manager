#!/usr/bin/env python3
"""
Startup script for Mikrotik-Manager
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Main function to start the application"""
    
    # Configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print("🚀 Starting Mikrotik-Manager...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"🔧 Debug mode: {'Enabled' if debug else 'Disabled'}")
    print("=" * 60)
    
    # Start the server
    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=debug,
            log_level="info" if not debug else "debug",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()