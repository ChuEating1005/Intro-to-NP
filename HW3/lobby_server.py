import signal
import sys
import socket
import threading
import time
import csv

lock = threading.Lock()
invited_list_lock = threading.Lock()
condition = threading.Condition()

host_ips = {"linux1": "140.113.235.151", 
            "linux3": "140.113.235.153",
            "linux2": "140.113.235.152",
            "linux4": "140.113.235.154"}

welcome = """\033[34;1m
 __      __       .__                             ._.
/  \    /  \ ____ |  |   ____  ____   _____   ____| |
\   \/\/   // __ \|  | _/ ___\/  _ \ /     \_/ __ \ |
 \        /\  ___/|  |_\  \__(  <_> )  Y Y  \  ___/\|
  \__/\  /  \___  >____/\___  >____/|__|_|  /\___  >_
       \/       \/          \/            \/     \/\/
\033[0m"""

online_cmd = {
    1: "list",
    2: "create",
    3: "join",
    4: "show invitations",
    5: "logout",
    6: "exit"
}
default_cmd = {
    1: "register",
    2: "login",
    3: "exit"
}
private_cmd = {
    1: "invite",
    2: "list_idle",
    3: "back_to_lobby",
    4: "start_game"
}
game_types = {
    1: "Battleship",
    2: "Gomoku"
}
show = "\033[33;1m= List =============================================\n\033[0m"
success = "\033[33;1m= Success ==========================================\n\033[0m"
failed = "\033[33;1m= Error ============================================\n\033[0m"
br = "\033[33;1m====================================================\n\033[0m"
# Data structures to hold user data and online players
active_connections = []  # Track active client connections
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
game_rooms = {}  
"""
game_rooms = {
    "room_name": {
        "type": "game_type", 
        "public": True/False, 
        "status": "waiting/playing", 
        "owner": "username", 
        "guest": "username",
        "ip": "ip",
        "port": "port"
    }
}
"""
invited_list = {}
"""
invited_list = {
    "username": [
        {
            "room_name": "room1", 
            "owner": "player1", 
            "type": "game_type", 
            "status": "accepted/declined"
        }
    ]
}
"""
def signal_handler(sig, frame):
    """
    Handle Ctrl+C signal and gracefully shut down the server.
    Notify all connected clients before shutting down.
    """
    print("\nCaught Ctrl+C. Notifying clients and shutting down server...")
    
    with lock:
        for conn in active_connections:
            try:
                conn.send("Server is shutting down. Goodbye.\n".encode())
                conn.close()
            except Exception as e:
                print(f"Error notifying client: {e}")
        active_connections.clear()
    
    print("All clients notified. Exiting.")
    sys.exit(0)

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

def broadcast_message(message, exclude_conn=None):
    """
    Broadcast a message to all connected clients except the excluded one
    """
    def send_to_client(conn, message):
        try:
            conn.send(message.encode())
        except Exception as e:
            print(f"Error broadcasting to client: {e}")

    with lock:
        for conn in active_connections:
            if conn != exclude_conn:
                # 為每個客戶端創建一個新線程來發送消息
                threading.Thread(target=send_to_client, 
                              args=(conn, message), 
                              daemon=True).start()

def login(conn, addr):
    conn.send("Enter username: ".encode())
    username = conn.recv(1024).decode().strip()
    if username not in users:
        conn.send((failed + bold_red("Username does not exist. Please register first.\n") + br).encode())
    else:
        conn.send("Enter password: ".encode())
        password = conn.recv(1024).decode().strip()
        if users[username] == password:
            with lock:
                online_players[username] = (conn, addr, "idle")
            conn.send((success + bold_green(f"Login successful. Welcome {username}.\n") + br + '\n').encode())
            # Broadcast login message
            broadcast_message(f"{bold_blue(f'[System] {username} has joined the lobby.')}", conn)
            list_rooms(conn, username)
        else:
            conn.send((failed + bold_red("Incorrect password. Try again.\n") + br).encode())

def logout(conn):
    for username in list(online_players.keys()):
        conn_obj, _, _ = online_players[username]
        if conn_obj == conn:
            del online_players[username]
            conn.send((success + bold_green("Logout successful.\n") + br).encode())
            # Broadcast logout message
            broadcast_message(f"{bold_blue(f'[System] {username} has left the lobby.')}", conn)

def list_rooms(conn, user):
    # List online players
    player_list = "Online Players:\n"
    if len(online_players) == 1:
        player_list += "No other online player.\n"
    else:
        for username, (_, _, status) in online_players.items():
            if username != user:
                player_list += f"- {username}: {status}\n"
    
    # List game rooms
    room_list = "\nGame Rooms:\n"
    if game_rooms:
        check = False
        for room_name, details in game_rooms.items():
            if details['public']:
                room_list += (f"- Room Name: {room_name}"
                                f"\n  ├── Game Type: {details['type']}"
                                f"\n  ├── Status: {details['status']}"
                                f"\n  └── Owner: {details['owner']}\n")
                check = True
        if not check:
            room_list += "No rooms available.\n"
    else:
        room_list += "No rooms available.\n"
    
    conn.send((show + bold_blue(player_list) + bold_blue(room_list) + br).encode())

def recv_with_timeout(conn, connect_event):
    """非阻塞方式接收用戶輸入"""
    conn.settimeout(0.1)  # 設置短暫的超時
    data = ""
    while not connect_event.is_set():
        try:
            data = conn.recv(1024).decode().strip()
            break
        except socket.timeout:
            if connect_event.is_set():  # 檢查是否需要退出
                break
            continue
        except Exception as e:
            print(f"Error receiving data: {e}")
            break
    conn.settimeout(None)  # 恢復阻塞模式
    return data

def private_room(conn, user, room_name="", game_type=""):
    invited_player_list = []
    # connect_event = threading.Event()
    # monitor_thread = threading.Thread(
    #     target=monitor_invitations,
    #     args=(room_name, invited_player_list, connect_event, conn),
    #     daemon=True
    # )
    # monitor_thread.start()
    while True:
        # print(game_rooms[room_name]["status"])
        
        if user == game_rooms[room_name]["owner"]:
            role = "host"
        elif user == game_rooms[room_name]["guest"]:
            role = "guest"
        idle_players = [username for username, (_, _, status) in online_players.items() if status == "idle" and username != user]
        if role == "host":
            conn.send(f"{bold_blue('[Gaming room: Host]')}\nChoose a option to do: \n1. Send invitation\n2. List idle users\n3. Back to lobby\n4. Start game\nEnter: ".encode())
        elif role == "guest":
            conn.send(f"{bold_blue('[Gaming room: Guest]')}\nChoose a option to do: \n1. Back to lobby\nEnter: ".encode())
        option = conn.recv(1024).decode().strip()
        # if connect_event.is_set():
        #     break
        if role == "host":
            if option.isspace() or not option.isdigit() or int(option) < 1 or int(option) > 4:
                command = "invalid"
                # conn.send("\nChoose a option to do: \n1. Send invitation\n2. List idle users\n3. Back to lobby\n4. Start game\nEnter: ".encode())
                # option = conn.recv(1024).decode().strip()
            else:
                option = int(option)
                command = private_cmd[option]
        else:
            if option.isspace() or not option.isdigit() or int(option) != 1:
                command = "invalid"
            else:
                option = int(option) + 2
                command = private_cmd[option]
       
        # List idle players
        if command == "list_idle":
            player_list = "Idle users:\n"
            if idle_players:   
                for idx, username in enumerate(idle_players, start=1):
                    player_list += f"{idx}. {username}\n"
            else:
                player_list += f"No idle user available to invite.\n"

            conn.send((show + bold_blue(player_list) + br).encode())

        # Send invitation
        elif command == "invite":
            player_list = ""
            if idle_players:   
                for idx, username in enumerate(idle_players, start=1):
                    player_list += f"{idx}. {username}\n"
            else:
                conn.send(bold_red("No idle user available to invite.\n").encode())
                continue

            conn.send((bold_blue(player_list)).encode())
            conn.send(("Enter the number of player to invite: ").encode())
            option = conn.recv(1024).decode().strip()

            while option.isspace() or not option.isdigit() or int(option) < 1 or int(option) > len(idle_players):
                invalid(conn)
                conn.send((bold_blue(player_list)).encode())
                conn.send(("Enter the number of player to invite: ").encode())
                option = conn.recv(1024).decode().strip()

            invited_player = idle_players[int(option) - 1]
            invited_conn, _, status = online_players[invited_player]
            if status != "idle":
                conn.send(f"{br}User is not idle. Please choose another user to invite.\n{br}".encode())
                continue

            if invited_player in invited_player_list:
                conn.send(bold_red(f"{invited_player} already has an invitation.\n").encode())
                continue

            # Add to the invited list
            invite_player(user, invited_player, room_name, game_type)
            invited_player_list.append(invited_player)
            conn.send((success + bold_green(f"Invitation sent to {invited_player}.\n") + br).encode())
            invited_conn.send((bold_blue(f"\nYou have been invited to join a private room by {user}. Game type: {game_type}. Check invitations to join.\n\n")).encode())

        elif command == "back_to_lobby":
            if role == "host":
                if game_rooms[room_name]["guest"] != "":
                    new_owner = game_rooms[room_name]["guest"]
                    with lock:
                        game_rooms[room_name]["status"] = "Waiting"
                        game_rooms[room_name]["owner"] = new_owner
                        game_rooms[room_name]["guest"] = ""
                    invited_conn = online_players[new_owner][0]
                    invited_conn.send((bold_blue(f"The host of room {room_name} has returned to lobby.\nYou become the new host.\n")).encode())
                elif room_name in game_rooms:
                    del game_rooms[room_name]
            conn.send((br + bold_blue("Returning to lobby...\n") + br).encode())
            return False
        
        elif command == "start_game":
            if game_rooms[room_name]["guest"] == "":
                conn.send((failed + bold_red("No player joined the room.\n") + br).encode())
                continue
            return True
                
        elif game_rooms[room_name]["status"] == "Playing":
            _ = conn.recv(1024).decode().strip()
            conn.send("join room".encode())
            conn.send(f"{game_rooms[room_name]['ip']}, {game_rooms[room_name]['port']}, {game_rooms[room_name]['type']}".encode())
            return True

        else:
            invalid(conn)
    # monitor_thread.join()
        
def create_room(conn, user, addr):
    conn.send("Enter room name: ".encode())
    room_name = conn.recv(1024).decode().strip()
    while room_name in game_rooms:
        conn.send(bold_red("Room name already exists. Try another.\n").encode())
        conn.send("Enter room name: ".encode())
        room_name = conn.recv(1024).decode().strip()
    
    conn.send("Choose a game you like: \n1. Battleship\n2. Gomoku\nEnter: ".encode())
    option = conn.recv(1024).decode().strip()
    while option.isspace() or not option.isdigit() or int(option) < 1 or int(option) > 2:
        invalid(conn)
        conn.send("Choose a game you like: \n1. Battleship\n2. Gomoku\nEnter: ".encode())
        option = conn.recv(1024).decode().strip()
    game_type = game_types[int(option)]

    conn.send("Is the room public? (Y/N): ".encode())
    public = conn.recv(1024).decode().strip().lower()
    while public not in ['y', 'n']:
        invalid(conn)
        conn.send("Is the room public? (Y/N): ".encode())
        public = conn.recv(1024).decode().strip().lower()
    public = (public == 'y')

    with lock:
        game_rooms[room_name] = {
            "type": game_type,
            "public": public,
            "status": "Waiting",
            "owner": user,
            "guest": ""
        }      

    if public:
        # Broadcast room creation for public rooms  
        broadcast_message(f"{bold_blue(f'[System] {user} created a new public room: {room_name} ({game_type})')}", conn)
        conn.send("wait for join".encode())
        with condition:
            while game_rooms[room_name]['status'] == "Waiting":
                condition.wait()  # Wait until notified
        invited_player = game_rooms[room_name]["guest"]
        invited_conn, _, _ = online_players[invited_player]
        conn.send(f"{br}Player joined! Starting the game in room: {room_name}\n{br}".encode())
    else:
        if not private_room(conn, user, room_name, game_type):
            return
        invited_player = game_rooms[room_name]["guest"]
        invited_conn = online_players[invited_player][0]

    room_created = False
    while not room_created:
        conn.send("\nPlease enter the port number to bind (10000 - 65535): ".encode())
        
        port = conn.recv(1024).decode().strip()
        while not port.isdigit() or int(port) < 10000 or int(port) > 65535:
            conn.send(bold_red("Invalid port number. Please choose in range (10000-65535): ").encode())
            port = conn.recv(1024).decode().strip()
        port = int(port)

        conn.send("create room".encode())
        ready = conn.recv(1024).decode().strip()
        if ready == 'ready':
            conn.send(f"{port}, {game_type}".encode())
        
        respond = conn.recv(1024).decode().strip()
        if respond == "room created successfully":
            room_created = True
    with lock:
        game_rooms[room_name]["status"] = "Playing"
        game_rooms[room_name]["ip"] = addr[0]
        game_rooms[room_name]["port"] = port

    invited_conn.send("break input".encode())

    if user in online_players:
        update_status(user, "playing")
    if invited_player in online_players:
        update_status(invited_player, "playing")
    close = conn.recv(1024).decode().strip()
    if user in online_players:
        update_status(user, "idle")
    if invited_player in online_players:
        update_status(invited_player, "idle")
    del game_rooms[room_name]

def join_room(conn, user):
    if not game_rooms:
        conn.send((failed + bold_red("No rooms available to join.\n") + br).encode())
        return

    # List available rooms for the user to join
    room_list = "Available Rooms:\n"
    room_options = []
    for idx, (room_name, details) in enumerate(game_rooms.items()):
        if details['public']:
            room_list += (f"{idx + 1}. Room Name: {room_name}. Type: {details['type']}\n")
            room_options.append((idx + 1, room_name))

    if not room_options:
        conn.send((br + bold_red("No rooms available to join.\n") + br).encode())
        return

    
    conn.send((br + bold_blue(room_list) + br + "Enter the room number to join: ").encode())
    choice = conn.recv(1024).decode().strip()
    while choice.isspace() or not choice.isdigit() or int(choice) < 1 or int(choice) > len(room_options):
        invalid(conn)
        conn.send("Enter the room number to join: ".encode())
        choice = conn.recv(1024).decode().strip()
    choice = int(choice)
    selected_room = room_options[choice - 1][1]  # Retrieve room name

    # Join the selected room
    with lock:
        room_details = game_rooms[selected_room]
        if room_details['status'] == "Waiting":
            room_details['status'] = "Playing"
            room_details['guest'] = user

            # Notify the condition that the room status has changed
            with condition:
                condition.notify_all()

            conn.send("join room".encode())
        else:
            conn.send((br + bold_red("Room is not available for joining now. Choose another.\n") + br).encode())
    
    close = conn.recv(1024).decode().strip()

def show_invitations(conn, user):
    global invited_list
    if user not in invited_list or not invited_list[user]:
        conn.send((failed + bold_red("No pending invitations.\n") + br).encode())
        return

    # Display the list of invitations
    invitation_list = "Pending Invitations:\n"
    for idx, invite in enumerate(invited_list[user], start=1):
        invitation_list += (f"{idx}. Room: {invite['room_name']}, "
                            f"Game: {invite['type']}, "
                            f"Inviter: {invite['owner']}\n")
    
    conn.send((show + bold_blue(invitation_list) + br + "Enter the number of the invitation to reply or 0 to exit: ").encode())

    choice = conn.recv(1024).decode().strip()
    while choice.isspace() or not choice.isdigit() or int(choice) < 0 or int(choice) > len(invited_list):
        invalid(conn)
        conn.send((bold_blue(invitation_list)).encode())
        conn.send(("Enter the number of the invitation to reply or 0 to cancel: ").encode())
        choice = conn.recv(1024).decode().strip()

    choice = int(choice)
    if choice == 0:
        return
    
    # Process the selected invitation
    selected_invite = invited_list[user][choice - 1]
    room_name = selected_invite['room_name']
    owner = selected_invite['owner']
    
    # 檢查房間是否還存在且可用
    if room_name not in game_rooms:
        conn.send((failed + bold_red("Room no longer exists.\n") + br).encode())
        invited_list[user].remove(selected_invite)
        return
    
    if game_rooms[room_name]["status"] != "Waiting":
        conn.send((failed + bold_red("Room is no longer available.\n") + br).encode())
        invited_list[user].remove(selected_invite)
        return
    
    # 檢查邀請者是否還在線
    if owner not in online_players:
        conn.send((failed + bold_red("Inviter is no longer online.\n") + br).encode())
        invited_list[user].remove(selected_invite)
        return
        
    owner_conn, _, _ = online_players[owner]
    conn.send(f"Do you want to join this room? (Y/N): ".encode())
    while(True):
        try:
            response = conn.recv(1024).decode().strip().lower()
            if response == 'y':
                with lock:  
                    game_rooms[room_name]["guest"] = user
                    game_rooms[room_name]["status"] = "Full"
                # Attempt to join the room
                conn.send((success + bold_green(f"Joining room '{room_name}' invited by {owner}.\n") + br).encode())
                # conn.send("join room".encode())
                if not private_room(conn, user, room_name):
                    break
                close = conn.recv(1024).decode().strip()
                break
            elif response == 'n':
                conn.send((failed + bold_red(f"Declined invitation from {owner}.\n") + br).encode())
                owner_conn.send((failed + bold_red(f"{user} declined your invitation.\n") + br).encode())
                break
            else:
                invalid(conn)
        except Exception as e:
            conn.send(f"{br}Error sending invitation: {e}\n{br}".encode())
    
    # Remove the processed invitation
    invited_list[user].remove(selected_invite)

def monitor_invitations(room_name, invited_player_list, connect_event, conn):
    """監控邀請回應的線程函數"""
    while not connect_event.is_set():
        for invited_player in invited_player_list:
            if invited_player not in invited_list:
                continue
            for invite in invited_list[invited_player]:
                if invite["room_name"] != room_name:
                    continue
                if invite["status"] == "accepted":
                    conn.send((br + bold_green(f"{invited_player} accepted your invitation. Room is starting...\n") + br).encode())
                    with lock:
                        game_rooms[room_name]["status"] = "Playing"
                        game_rooms[room_name]["guest"] = invited_player
                    connect_event.set()
                    return
                elif invite["status"] == "declined":
                    conn.send((failed + bold_red(f"{invited_player} declined your invitation.\nPlease choose another user to invite.\n") + br).encode())
                    
        time.sleep(0.1)  # 避免過度佔用 CPU

def invalid(conn):
    conn.send((failed + bold_red("Invalid option. Try again.\n") + br).encode())

def bold_green(text):
    return "\033[32;1m" + text + "\033[0m"

def bold_red(text):
    return "\033[31;1m" + text + "\033[0m"

def bold_blue(text):
    return "\033[34;1m" + text + "\033[0m"

def invite_player(inviter, invited_player, room_name, game_type):
    global invited_list
    if invited_player not in invited_list:
        invited_list[invited_player] = []

    # Add the invitation to the invited player's list
    invitation = {
        "room_name": room_name,
        "owner": inviter,
        "type": game_type
    }
    with invited_list_lock:
        invited_list[invited_player].append(invitation)


def update_status(username, new_status):
    global online_players
    if username in online_players:
        conn, address, _ = online_players[username]  # Extract existing connection and address
        online_players[username] = (conn, address, new_status)  # Update the status
    else:
        print(f"Player {username} not found in online_players.")

def handle_client(conn, addr):
    """
    Handle individual client connections.
    """
    global active_connections, users, online_players

    # Add connection to the active list
    with lock:
        active_connections.append(conn)

    try:
        conn.send(welcome.encode())
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
                conn.send("\nChoose a option to do: \n1. List rooms\n2. Create room\n3. Join room\n4. Show invitations\n5. Logout\n6. Exit\nEnter: ".encode())
                option = conn.recv(1024).decode().strip()
                if option == "" or not option.isdigit() or int(option) < 1 or int(option) > 6:
                    command = "invalid"
                else:
                    option = int(option)
                    command = online_cmd[option]
            else:
                conn.send("\nChoose a option to do: \n1. Register\n2. Login\n3. Exit\nEnter: ".encode())
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
                create_room(conn, user, addr)
            elif command == "join":
                join_room(conn, user)
            elif command == "show invitations":
                show_invitations(conn, user)
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
                broadcast_message(f"{bold_blue(f'[System] {username} has disconnected.')}", conn)
                del online_players[username]
        
        with lock:
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
        # host = "127.0.0.1"
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
