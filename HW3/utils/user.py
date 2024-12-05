import csv
import threading
from utils.messaging import *


online_lock = threading.Lock()
users = {}
"""
users = {
    "username": "password"
}
"""
online_players = {}
"""
online_players = {
    "username": (conn, address, status)
}
"""
def load_accounts():
    """Load user accounts from CSV file"""
    global users
    try:
        with open('accounts.csv', 'r', newline='') as f:
            reader = csv.reader(f)
            users = {row[0]: row[1] for row in reader}
    except FileNotFoundError:
        users = {}
    except Exception as e:
        print(bold_red(f"Error reading accounts file: {e}. Starting with empty accounts."))
        users = {}

def save_accounts():
    """Save user accounts to CSV file"""
    try:
        with open('accounts.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            for username, password in users.items():
                writer.writerow([username, password])
    except Exception as e:
        print(bold_red(f"Error saving accounts: {e}"))
        
def register(conn):
    conn.send("Enter username: ".encode())
    username = conn.recv(1024).decode().strip()
    if username in users:
        conn.send((failed + bold_red("Username already exists. Try another.\n") + br).encode())
    else:
        conn.send("Enter password: ".encode())
        password = conn.recv(1024).decode().strip()
        users[username] = password
        save_accounts()
        conn.send((success + bold_green("Registration successful. You can now login.\n") + br).encode())


def login(conn, addr):
    from utils.gameroom import list_rooms

    conn.send("Enter username: ".encode())
    username = conn.recv(1024).decode().strip()
    if username not in users:
        conn.send((failed + bold_red("Username does not exist. Please register first.\n") + br).encode())
    else:
        conn.send("Enter password: ".encode())
        password = conn.recv(1024).decode().strip()
        if users[username] == password:
            with online_lock:
                online_players[username] = (conn, addr, "idle")
            conn.send((success + bold_green(f"Login successful. Welcome {username}.\n") + br + '\n').encode())
            # Broadcast login message
            broadcast_message(f'{username} has joined the lobby.', conn)
            list_rooms(conn, username)
        else:
            conn.send((failed + bold_red("Incorrect password. Try again.\n") + br).encode())

def logout(conn):
    for username in list(online_players.keys()):
        conn_obj, _, _ = online_players[username]
        if conn_obj == conn:
            with online_lock:
                del online_players[username]
            conn.send((success + bold_green("Logout successful.\n") + br).encode())
            # Broadcast logout message
            broadcast_message(f"{bold_blue(f'[System] {username} has left the lobby.')}", conn)


def update_user_status(username, new_status):
    if username in online_players:
        conn, address, _ = online_players[username]  # Extract existing connection and address
        with online_lock:
            online_players[username] = (conn, address, new_status)  # Update the status
    else:
        print(f"Player {username} not found in online_players.")