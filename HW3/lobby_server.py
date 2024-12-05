import signal
import sys
import socket
import threading
from utils.messaging import *
from utils.gameroom import *
from utils.game_dev import *
from utils.user import *

connection_lock = threading.Lock()
lock = threading.Lock()

host_ips = {"linux1": "140.113.235.151", 
            "linux3": "140.113.235.153",
            "linux2": "140.113.235.152",
            "linux4": "140.113.235.154",
            "itingchu": "127.0.0.1"}

online_cmd = {
    1: "list",
    2: "create",
    3: "join",
    4: "show invitations",
    5: "game dev",
    6: "logout",
    7: "exit"
}
online_cmd_t = """
1. List rooms & players
2. Create room
3. Join room
4. Show invitations
5. Game developer menu
6. Logout
7. Exit
"""
default_cmd = {
    1: "register",
    2: "login",
    3: "exit"
}
default_cmd_t = """
1. Register
2. Login
3. Exit
"""

active_connections = []  # Track active client connections
def signal_handler(sig, frame):
    """
    Handle Ctrl+C signal and gracefully shut down the server.
    Notify all connected clients before shutting down.
    """
    print("\nCaught Ctrl+C. Notifying clients and shutting down server...")
    
    with connection_lock:
        for conn in active_connections:
            try:
                conn.send("Server is shutting down. Goodbye.\n".encode())
                conn.close()
            except Exception as e:
                print(f"Error notifying client: {e}")
        active_connections.clear()
    
    print("All clients notified. Exiting.")
    sys.exit(0)

def handle_client(conn, addr):
    """
    Handle individual client connections.
    """
    global active_connections, users, online_players

    # Add connection to the active list
    with connection_lock:
        active_connections.append(conn)

    try:
        welcome_msg(conn)
        conn.send(bold_blue("Welcome to the Lobby Server. Please register or login.\n").encode())
        while True:
            logined = False
            user = ""
            for username in list(online_players.keys()):
                conn_obj, _, _ = online_players[username]
                if conn_obj == conn:
                    user = username 
                    logined = True
                    break
            if logined:
                conn.send(f"\nChoose a option to do: {online_cmd_t}Enter: ".encode())
                option = conn.recv(1024).decode().strip()
                if option == "" or not option.isdigit() or int(option) < 1 or int(option) > 7:
                    command = "invalid"
                else:
                    option = int(option)
                    command = online_cmd[option]
            else:
                conn.send(f"\nChoose a option to do: {default_cmd_t}Enter: ".encode())
                option = conn.recv(1024).decode().strip()
                if option == "" or not option.isdigit() or int(option) < 1 or int(option) > 3:
                    command = "invalid"
                else:
                    option = int(option)
                    command = default_cmd[option]
            if command == "register":
                register(conn)
            elif command == "login":
                login(conn, addr)
            elif command == "logout":
                logout(conn)
            elif command == "list":
                list_rooms(conn, user)
            elif command == "create":
                create_room(conn, user)
            elif command == "join":
                join_room(conn, user)
            elif command == "show invitations":
                show_invitations(conn, user)
            elif command == "game dev":
                game_management_interface(conn, user)
            elif command == "exit":
                if logined:
                    logout(conn)
                conn.send("Goodbye.\n".encode())
                break
            else:
                invalid(conn)
    except BrokenPipeError:
        print(bold_red(f"Client {addr} disconnected (Broken pipe)."))
    except ConnectionResetError:
        print(f"Client {addr} forcibly closed the connection.")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        # Broadcast disconnect message if user was logged in
        for username in list(online_players.keys()):  
            conn_obj, _, _ = online_players[username]
            if conn_obj == conn:
                broadcast_message(f'[System] {username} has disconnected.', conn)
                del online_players[username]
        
        with connection_lock:
            if conn in active_connections:
                active_connections.remove(conn)
        conn.close()
        print(bold_red(f"Connection with {addr} closed."))


def start_server():
    load_accounts()
    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get the host IP
    try:
        host = host_ips[socket.gethostname()]
    except KeyError:
        print("Error: Hostname not found in the host_ips dictionary.")
        sys.exit(1)

    lobby_server = None

    # Create and bind server socket
    while lobby_server is None:
        try:
            port = int(input("Please enter port number: "))
            lobby_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            lobby_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reusing the same port
            lobby_server.bind((host, port))
            lobby_server.listen(5)
            print(bold_green(f"Lobby Server running on {host}:{port}"))
        except ValueError:
            print(bold_red("Invalid port number. Please enter a valid integer."))
        except socket.error as e:
            print(bold_red("Error creating or binding server socket:"))
            print("---------------------------------------")
            print(e)
            print("---------------------------------------")
            lobby_server = None

    # Accept incoming connections
    try:
        while lobby_server:
            try:
                conn, addr = lobby_server.accept()
                print(bold_green(f"New connection from {addr}"))
                threading.Thread(target=handle_client, args=(conn, addr)).start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
    except KeyboardInterrupt:
        print(bold_red("\nServer shutting down."))
    finally:
        if lobby_server:
            lobby_server.close()
        print(bold_red("Server socket closed."))

if __name__ == "__main__":
    start_server()
