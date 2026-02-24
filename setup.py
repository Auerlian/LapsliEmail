#!/usr/bin/env python3
"""
Complete setup script for the Bulk Email Platform
Handles database migration and initial configuration
"""

import os
import sys
import subprocess

def check_dependencies():
    """Check if required packages are installed"""
    print("Checking dependencies...")
    try:
        import flask
        import flask_sqlalchemy
        import flask_login
        import flask_migrate
        print("✓ All dependencies installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("\nInstalling dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        return True

def setup_database():
    """Set up database with proper migrations"""
    print("\n" + "="*60)
    print("  DATABASE SETUP")
    print("="*60 + "\n")
    
    # Check if database exists
    db_exists = os.path.exists('instance/platform.db')
    
    if db_exists:
        print("Existing database found.")
        print("Applying manual migration to add missing columns...")
        
        # Run manual migration
        from manual_migration import migrate_database
        try:
            migrate_database()
            print("\n✓ Database updated successfully")
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            return False
    else:
        print("No existing database found.")
        print("Creating new database with Flask-Migrate...")
        
        os.makedirs('instance', exist_ok=True)
        
        # Set Flask app environment variable
        os.environ['FLASK_APP'] = 'app_production.py'
        
        # Initialize migrations
        if not os.path.exists('migrations'):
            print("\nInitializing Flask-Migrate...")
            result = subprocess.run(['flask', 'db', 'init'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"✗ Failed to initialize migrations: {result.stderr}")
                return False
            print("✓ Migrations initialized")
        
        # Generate migration
        print("\nGenerating migration...")
        result = subprocess.run(
            ['flask', 'db', 'migrate', '-m', 'Initial migration'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"✗ Failed to generate migration: {result.stderr}")
            return False
        print("✓ Migration generated")
        
        # Apply migration
        print("\nApplying migration...")
        result = subprocess.run(['flask', 'db', 'upgrade'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"✗ Failed to apply migration: {result.stderr}")
            return False
        print("✓ Migration applied")
    
    return True

def setup_env_file():
    """Create .env file if it doesn't exist"""
    print("\n" + "="*60)
    print("  ENVIRONMENT CONFIGURATION")
    print("="*60 + "\n")
    
    if os.path.exists('.env'):
        print("✓ .env file already exists")
        return True
    
    if os.path.exists('.env.example'):
        print("Creating .env from .env.example...")
        with open('.env.example', 'r') as src:
            with open('.env', 'w') as dst:
                dst.write(src.read())
        print("✓ .env file created")
        print("\n⚠ Please edit .env and add your API keys")
    else:
        print("⚠ No .env.example found")
        print("Please create .env manually with required configuration")
    
    return True

def main():
    print("="*60)
    print("  BULK EMAIL PLATFORM - SETUP")
    print("="*60 + "\n")
    
    # Check dependencies
    if not check_dependencies():
        print("\n✗ Setup failed: Missing dependencies")
        return 1
    
    # Setup environment
    setup_env_file()
    
    # Setup database
    if not setup_database():
        print("\n✗ Setup failed: Database setup error")
        return 1
    
    print("\n" + "="*60)
    print("  SETUP COMPLETE")
    print("="*60)
    print("\nYou can now start the application:")
    print("  python app_production.py")
    print("\nOr for development:")
    print("  export FLASK_APP=app_production.py")
    print("  flask run")
    print("\n" + "="*60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
