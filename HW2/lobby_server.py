import socket
import threading

host_ips = {"linux1.cs.nctu.edu.tw": "140.113.235.151", 
            "linux2.cs.nctu.edu.tw": "140.113.235.152",
            "linux3.cs.nctu.edu.tw": "140.113.235.153",
            "linux4.cs.nctu.edu.tw": "140.113.235.154"}

# Data structures to hold user data and online players
users = {}  # Format: {"username": "password"}
online_players = {}  # Format: {"username": (conn, address, status)}

def handle_client(conn, addr):
    global users, online_players
    conn.send("Welcome to the Lobby Server. Please register or login.\n".encode())

    while True:
        try:
            conn.send("Enter command (register/login/logout/create/join/exit): ".encode())
            command = conn.recv(1024).decode().strip()

            if command == "register":
                conn.send("Enter username: ".encode())
                username = conn.recv(1024).decode().strip()
                if username in users:
                    conn.send("Username already exists. Try another.\n".encode())
                else:
                    conn.send("Enter password: ".encode())
                    password = conn.recv(1024).decode().strip()
                    users[username] = password
                    conn.send("Registration successful. You can now login.\n".encode())

            elif command == "login":
                conn.send("Enter username: ".encode())
                username = conn.recv(1024).decode().strip()
                if username not in users:
                    conn.send("User does not exist. Please register first.\n".encode())
                else:
                    conn.send("Enter password: ".encode())
                    password = conn.recv(1024).decode().strip()
                    if users[username] == password:
                        online_players[username] = (conn, addr, "idle")
                        conn.send(f"Login successful. Welcome {username}.\n".encode())
                    else:
                        conn.send("Incorrect password. Try again.\n".encode())

            elif command == "logout":
                for username, (c, _, _) in online_players.items():
                    if c == conn:
                        del online_players[username]
                        conn.send("Logout successful.\n".encode())
                        break

            elif command == "create":
                conn.send("Room creation is not implemented yet.\n".encode())

            elif command == "join":
                conn.send("Joining a room is not implemented yet.\n".encode())

            elif command == "exit":
                conn.send("Goodbye.\n".encode())
                break
            else:
                conn.send("Invalid command. Try again.\n".encode())
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            break

    conn.close()

def start_server():
    # Get the host IP and port number
    # host = host_ips[socket.gethostname()]
    host = '0.0.0.0'
    port = int(input("Please enter port number: "))
    # Create a server TCP socket
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((host, port))
        server.listen(5)
        print(f"Lobby Server running on {host}:{port}")
    except socket.error as e:
        print(f"Error creating or binding server socket: {e}")
        server = None

    while True:
        conn, addr = server.accept()
        print(f"New connection from {addr}")
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()
