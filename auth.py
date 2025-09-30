import sqlite3
import bcrypt
import streamlit as st
from typing import Optional, Tuple
import os


def init_database():
    """Initialize SQLite database with users table if it doesn't exist."""
    db_path = "users.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_user(username: str, password: str) -> Tuple[bool, str]:
    """Create a new user with hashed password. Returns (success, message)."""
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return False, "Username already exists"
        
        # Create new user
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        
        conn.commit()
        conn.close()
        return True, "User created successfully"
        
    except Exception as e:
        return False, f"Error creating user: {str(e)}"


def authenticate_user(username: str, password: str) -> Tuple[bool, str]:
    """Authenticate user credentials. Returns (success, message)."""
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False, "Invalid username or password"
        
        password_hash = result[0]
        if verify_password(password, password_hash):
            return True, "Login successful"
        else:
            return False, "Invalid username or password"
            
    except Exception as e:
        return False, f"Error authenticating user: {str(e)}"


def is_logged_in() -> bool:
    """Check if user is logged in based on session state."""
    return "user" in st.session_state and st.session_state["user"] is not None


def get_current_user() -> Optional[str]:
    """Get current logged-in username."""
    return st.session_state.get("user")


def login_user(username: str):
    """Set user as logged in."""
    st.session_state["user"] = username


def logout_user():
    """Clear user session."""
    if "user" in st.session_state:
        del st.session_state["user"]


def show_auth_forms():
    """Display login and signup forms."""
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            login_submitted = st.form_submit_button("Login")
            
            if login_submitted:
                if username and password:
                    success, message = authenticate_user(username, password)
                    if success:
                        login_user(username)
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please enter both username and password")
    
    with tab2:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            username = st.text_input("Username", key="signup_username")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
            signup_submitted = st.form_submit_button("Sign Up")
            
            if signup_submitted:
                if username and password and confirm_password:
                    if password != confirm_password:
                        st.error("Passwords do not match")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters long")
                    else:
                        success, message = create_user(username, password)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.error("Please fill in all fields")


