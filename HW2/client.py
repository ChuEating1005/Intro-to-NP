import socket
import time
import signal
import sys
from getpass import getpass 
import battleship
import gomoku

host_ips = {"linux1": "140.113.235.151", 
            "linux3": "140.113.235.153",
            "linux2": "140.113.235.152",
            "linux4": "140.113.235.154"}
ip_host = {"140.113.235.151": "linux1",
            "140.113.235.152": "linux2",
            "140.113.235.153": "linux3",
            "140.113.235.154": "linux4"}

def signal_handler(sig, frame):
    """
    Handle Ctrl+C signal and gracefully exit the client program.
    """
    print("\nCaught Ctrl+C. Exiting...")
    sys.exit(0)  # Exit the program

def bold_green(text):
    return "\033[32;1m" + text + "\033[0m"

def bold_red(text):
    return "\033[31;1m" + text + "\033[0m"

def bold_blue(text):
    return "\033[34;1m" + text + "\033[0m"

def create_room(client):
    client.send("ready".encode())

    try:
        host = host_ips[socket.gethostname()]
        (port, game_type) = client.recv(1024).decode().strip().split(', ')
        port = int(port)
        game_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        game_server.bind((host, port))
        game_server.listen(1)
        client.send("room created successfully".encode())
    except socket.error as e:
        print("Error creating or binding server socket: \n")
        print("---------------------------------------")
        print(e)
        print("---------------------------------------\n")
        game_server = None
        client.send("error".encode())
        return
    try:
        while True and game_server != None:
            conn, addr = game_server.accept()
            print(bold_green(f"Player join from {ip_host[addr[0]]}! Game start!"))
            play_game(conn, game_type, player='server')
            print(bold_blue("Game over! Back to lobby..."))
            break
    except Exception as e:
        print(bold_red("Connection closed by the opponent. Back to lobby..."))
    conn.close()
    game_server.close()
    client.send("room close".encode())
    

def join_room(client):
    (host, port, game_type) = client.recv(1024).decode().strip().split(', ')
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((host, int(port)))
    try:
        print(bold_green("Connected to the server! Game start!"))
        play_game(conn,  game_type, player='client')
        print(bold_blue("Game over! Back to lobby..."))
    except Exception as e:
        print(bold_red("Connection closed by the opponent. Back to lobby..."))
    conn.close()
    client.send("room close".encode())
    

def play_game(conn, game_type, player):
    if game_type == "Battleship":
        battleship.start_game(conn, player)
    else:
        gomoku.start_game(conn, player)


def client_program():
    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    host = "140.113.235.151"
    while True:
        try:
            port = int(input("Enter server port: "))
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((host, port))
            break
        except socket.error as e:
            print("Error creating or binding server socket: \n")
            print("---------------------------------------")
            print(e)
            print("---------------------------------------\n")
    
    time.sleep(0.1)
    try:
        while True:
            server_message = client.recv(1024).decode()
            if "Enter password:" in server_message:
                print("Enter password: ", end="", flush=True)  # Prompt user for password
                password = getpass("")  # Hide password input
                client.send(password.encode())  # Send password to the server
            elif "wait for join" in server_message:
                print(bold_green("Public room create successfully! Waiting for other players to join...\n"))
                msg = client.recv(1024).decode()
                print(msg, end="")
                select_port = client.recv(1024).decode()
                print(select_port, end="")
                client_message = input()  # Take user input
                client.send(client_message.encode())
            elif "create room" in server_message:
                create_room(client)
            elif "join room" in server_message:
                print(bold_green("Successfully joined the room!"))
                join_room(client)
            elif "Invitation sent. Waiting for acception..." in server_message:
                respond = client.recv(1024).decode()
                client.send(respond.encode())
            else:
                print(server_message, end="")  # Display server message to the user
                if "Goodbye" in server_message:
                    break
                
                client_message = input()
                client.send(client_message.encode())
            time.sleep(0.1)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        print("Connection closed.")

if __name__ == "__main__":
    client_program()
