from utils.messaging import *
from utils.user import *
from utils.game_dev import send_game_to_client, list_all_games
import threading
import time

invited_list_lock = threading.Lock()
game_rooms_lock = threading.Lock()
private_cmd = {
    1: "invite",
    2: "list_idle",
    3: "back_to_lobby",
    4: "start_game"
}
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

def enter_room(conn, user, room_name, game_type):
    update_user_status(user, "in_room")
    send_game_to_client(conn, user, game_type)
    invited_player_list = []
    while True:        
        if user == game_rooms[room_name]["owner"]:
            role = "host"
        elif user == game_rooms[room_name]["guest"]:
            role = "guest"
        
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
            if (game_rooms[room_name]["status"] == "Full"):
                failed_msg(conn, "The room is full. Please start the game or leave the room.")
            idle_players = [username for username, (_, _, status) in online_players.items() if status == "idle" and username != user]
            player_list = "Idle users:\n"
            if idle_players:   
                for idx, username in enumerate(idle_players, start=1):
                    player_list += f"{idx}. {username}\n"
            else:
                player_list += f"No idle user available to invite.\n"

            list_msg(conn, player_list)

        # Send invitation
        elif command == "invite":
            idle_players = [username for username, (_, _, status) in online_players.items() if status == "idle" and username != user]
            player_list = ""
            if idle_players:   
                for idx, username in enumerate(idle_players, start=1):
                    player_list += f"{idx}. {username}\n"
            else:
                failed_msg(conn, "No idle user available to invite.")
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
                failed_msg(conn, f"{invited_player} is not idle. Please choose another user to invite.")
                continue

            if invited_player in invited_player_list:
                failed_msg(conn, f"{invited_player} already has an invitation.")
                continue

            # Add to the invited list
            invite_player(user, invited_player, room_name, game_type)
            invited_player_list.append(invited_player)
            success_msg(conn, f"Invitation sent to {invited_player}.")
            system_msg(invited_conn, f"{user} invited you to join a gaming room. Game type: {game_type}. Check invitations to join.")

        elif command == "back_to_lobby":
            if role == "host":
                if game_rooms[room_name]["guest"] != "":
                    new_owner = game_rooms[room_name]["guest"]
                    update_room_host(room_name, new_owner)
                    invited_conn = online_players[new_owner][0]
                    invited_conn.send((bold_blue(f"The host of room {room_name} has returned to lobby.\nYou become the new host.\n")).encode())
                elif room_name in game_rooms:
                    del game_rooms[room_name]
            else:
                host = game_rooms[room_name]["owner"]
                host_conn = online_players[host][0]
                host_conn.send((bold_blue(f"The guest has returned to lobby.\nWaiting for other players to join.\n")).encode())
            if room_name in game_rooms: 
                update_room_status(room_name, "Waiting")
                update_room_guest(room_name, "")
            update_user_status(user, "idle")
            success_msg(conn, "Returning to lobby...")
            return False
        
        elif command == "start_game":
            with game_rooms_lock:
                if game_rooms[room_name]["guest"] == "":
                    failed_msg(conn, "No player joined the room.")
                    continue
            start_game(conn, user, room_name)
            return False
        
        elif game_rooms[room_name]["status"] == "Playing":
            # _ = conn.recv(1024).decode().strip()
            conn.send("join room".encode())
            time.sleep(0.3)
            conn.send(f"{game_rooms[room_name]['ip']}, {game_rooms[room_name]['port']}, {game_rooms[room_name]['type']}".encode())
            return True

        else:
            invalid(conn)
        
def create_room(conn, user):
    conn.send("Enter room name: ".encode())
    room_name = conn.recv(1024).decode().strip()
    while room_name in game_rooms:
        conn.send(bold_red("Room name already exists. Try another.\n").encode())
        conn.send("Enter room name: ".encode())
        room_name = conn.recv(1024).decode().strip()
    
    game_types = list_all_games(conn)
    if game_types == None:
        return
    conn.send("Choose a game you like: ".encode())
    option = conn.recv(1024).decode().strip()
    while option.isspace() or not option.isdigit() or int(option) < 1 or int(option) > 2:
        invalid(conn)
        conn.send("Choose a game you like: \n1. Battleship\n2. Gomoku\nEnter: ".encode())
        option = conn.recv(1024).decode().strip()
    game_type = game_types[int(option)-1]

    conn.send("Is the room public? (Y/N): ".encode())
    public = conn.recv(1024).decode().strip().lower()
    while public not in ['y', 'n']:
        invalid(conn)
        conn.send("Is the room public? (Y/N): ".encode())
        public = conn.recv(1024).decode().strip().lower()
    public = (public == 'y')

    with game_rooms_lock:
        game_rooms[room_name] = {
            "type": game_type,
            "public": public,
            "status": "Waiting",
            "owner": user,
            "guest": ""
        }      

    if public:
        broadcast_message(f'{user} created a new public room: {room_name} ({game_type})', conn)
    
    enter_room(conn, user, room_name, game_type)

        

def start_game(conn, user, room_name):
    addr = online_players[user][1]
    game_type = game_rooms[room_name]["type"]
    invited_player = game_rooms[room_name]["guest"]
    invited_conn = online_players[invited_player][0]

    update_room_status(room_name, "Playing")
    if user in online_players:
        update_user_status(user, "playing")
    if invited_player in online_players:
        update_user_status(invited_player, "playing")

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
    with game_rooms_lock:
        game_rooms[room_name]["ip"] = addr[0]
        game_rooms[room_name]["port"] = port

    invited_conn.send("break input".encode())
    
    close = conn.recv(1024).decode().strip()
    if user in online_players:
        update_user_status(user, "idle")
    if invited_player in online_players:
        update_user_status(invited_player, "idle")
    del game_rooms[room_name]

def join_room(conn, user):
    if not game_rooms:
        failed_msg(conn, "No rooms available to join.")
        return

    # List available rooms for the user to join
    room_list = "Available Rooms:\n"
    room_options = []
    for idx, (room_name, details) in enumerate(game_rooms.items()):
        if details['public'] and details['status'] == "Waiting":
            room_list += (f"{idx + 1}. Room Name: {room_name}. Type: {details['type']}\n")
            room_options.append((idx + 1, room_name))

    if not room_options:
        failed_msg(conn, "No rooms available to join.")
        return

    list_msg(conn, room_list)
    conn.send("Enter the room number to join: ".encode())
    choice = conn.recv(1024).decode().strip()
    while choice.isspace() or not choice.isdigit() or int(choice) < 1 or int(choice) > len(room_options):
        invalid(conn)
        conn.send("Enter the room number to join: ".encode())
        choice = conn.recv(1024).decode().strip()
    choice = int(choice)
    selected_room = room_options[choice - 1][1]  # Retrieve room name
    
    # Join the selected room
    update_room_status(selected_room, "Full")
    with game_rooms_lock:
        game_rooms[selected_room]['guest'] = user
    enter_room(conn, user, selected_room, game_rooms[selected_room]['type'])
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
    
    list_msg(conn, invitation_list)
    conn.send("Enter the number of the invitation to reply or 0 to exit: ".encode())

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
                update_room_guest(room_name, user)
                update_room_status(room_name, "Full")
                success_msg(conn, f"Joining room '{room_name}' invited by {owner}.")
                game_type = game_rooms[room_name]["type"]
                if not enter_room(conn, user, room_name, game_type):
                    break
                close = conn.recv(1024).decode().strip()
                break
            elif response == 'n':
                failed_msg(conn, f"Declined invitation from {owner}.")
                failed_msg(owner_conn, f"{user} declined your invitation.")
                break
            else:
                invalid(conn)
        except Exception as e:
            conn.send(f"{br}Error sending invitation: {e}\n{br}".encode())
    
    # Remove the processed invitation
    invited_list[user].remove(selected_invite)

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

def list_rooms(conn, user):
    # List online players
    player_list = "Online Players:\n"
    if len(online_players) == 1:
        player_list += "No other online player.\n"
    else:
        for username, (_, _, status) in online_players.items():
            if username != user:
                player_list += f"- {username}: {status if status != 'in_room' else 'In room'}\n"
    
    # List game rooms
    room_list = "\nGame Rooms:\n"
    if game_rooms:
        check = False
        for room_name, details in game_rooms.items():
            if details['public']:
                room_list += (f"- Room Name: {room_name}"
                                f"\n  ├── Game Type: {details['type']}"
                                f"\n  ├── Status: {details['status']}"
                                f"\n  └── Host: {details['owner']}\n")
                check = True
        if not check:
            room_list += "No rooms available.\n"
    else:
        room_list += "No rooms available.\n"
    
    list_msg(conn, player_list + room_list)

def update_room_status(room_name, status):
    with game_rooms_lock:
        game_rooms[room_name]["status"] = status

def update_room_guest(room_name, guest):
    with game_rooms_lock:
        game_rooms[room_name]["guest"] = guest

def update_room_host(room_name, host):
    with game_rooms_lock:
        game_rooms[room_name]["owner"] = host