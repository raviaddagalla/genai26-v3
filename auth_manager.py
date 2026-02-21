import json
import uuid
import os
from datetime import datetime

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def register_user(username, password):
    users = load_users()
    
    if username in users:
        return {"error": "Username already exists"}
    
    users[username] = {
        "password": password,
        "session_id": str(uuid.uuid4()),  # Auth session ID
        "brand_session_id": None,  # Will be set during intake
        "created_at": datetime.now().isoformat(),
        "last_login": None
    }
    
    save_users(users)
    return {"success": True, "session_id": users[username]["session_id"]}

def login_user(username, password):
    users = load_users()
    
    if username not in users:
        return {"error": "User not found"}
    
    if users[username]["password"] != password:
        return {"error": "Invalid password"}
    
    users[username]["last_login"] = datetime.now().isoformat()
    save_users(users)
    
    return {"success": True, "session_id": users[username]["session_id"]}