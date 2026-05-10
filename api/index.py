"""
api/index.py — Vercel Serverless Function entrypoint for Flask backend
"""
import sys
import os

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(project_root, 'backend')

# Add backend directory to Python path
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app import create_app

# Create the Flask app instance
app = create_app()

# Vercel expects the app to be named 'app' or 'handler'
# The app is already a WSGI application that Vercel can use
