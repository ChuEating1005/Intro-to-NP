import socket
import random
import threading

BOARD_SIZE = 5
NUM_SHIPS = 3


def create_board():
    """Create an empty game board."""
    return [["~" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def bold_green(text):
    return "\033[32;1m" + text + "\033[0m"

def bold_red(text):
    return "\033[31;1m" + text + "\033[0m"

def place_ships(board):
    """Randomly place ships on the board."""
    ships = []
    while len(ships) < NUM_SHIPS:
        row = random.randint(0, BOARD_SIZE - 1)
        col = random.randint(0, BOARD_SIZE - 1)
        if board[row][col] == "~":
            board[row][col] = "S"
            ships.append((row, col))
    return ships


def print_board(board, hide_ships=True):
    """Display the game board."""
    print("  " + " ".join(str(i) for i in range(BOARD_SIZE)))
    for i, row in enumerate(board):
        if hide_ships:
            print(f"{i} " + " ".join("~" if cell == "S" else cell for cell in row))
        else:
            print(f"{i} " + " ".join(row))


def is_hit(ships, row, col):
    """Check if the attack hits a ship."""
    return (row, col) in ships


def server_game(conn, board, ships):
    """Server-side game logic."""
    print("Game started! Waiting for client moves.")
    while True:
        # Wait for the client's attack
        attack = conn.recv(1024).decode()
        if attack == "exit":
            print("Client disconnected. Game over.")
            break

        row, col = map(int, attack.split(","))
        print(f"Client attacked: ({row}, {col})")
        board[row][col] = "*"

        # Check if the attack hits
        if is_hit(ships, row, col):
            ships.remove((row, col))
            # Check if all ships are sunk
            if not ships:
                print(bold_red("All your ships are sunk! You lose."))
                conn.send("win".encode())
                break
            else:
                print(bold_green("Hit!"))
                conn.send("hit".encode())
        else:
            print(bold_red("Miss."))
            conn.send("miss".encode())        

        # Server's turn to attack
        print("Current state:")
        print_board(board, hide_ships=False)
        row = input("Enter row to attack: ")
        while not row.isdigit() or int(row) < 0 or int(row) >= BOARD_SIZE:
            row = input("Input out of range. Pleae enter again: ")
        row = int(row)
        col = input("Enter column to attack: ")
        while not col.isdigit() or int(col) < 0 or int(col) >= BOARD_SIZE:
            col = input("Input out of range. Pleae enter again: ")
        col = int(col)
        conn.send(f"{row},{col}".encode())
        result = conn.recv(1024).decode()
        print(f"Client reported: {result}")
            
        if result == "win":
            print(bold_green("You win! All client ships are sunk."))
            break


def client_game(client, board, ships):
    """Client-side game logic."""
    while True:
        # Client's turn to attack
        print("Current state:")
        print_board(board, hide_ships=False)
        row = input("Enter row to attack: ")
        while not row.isdigit() or int(row) < 0 or int(row) >= BOARD_SIZE:
            row = input("Input out of range. Pleae enter again: ")
        row = int(row)
        col = input("Enter column to attack: ")
        while not col.isdigit() or int(col) < 0 or int(col) >= BOARD_SIZE:
            col = input("Input out of range. Pleae enter again: ")
        col = int(col)
        client.send(f"{row},{col}".encode())
        result = client.recv(1024).decode()
        print(f"Server reported: {result}")

        if result == "win":
            print(bold_green("You win! All server ships are sunk."))
            break

        # Wait for the server's attack
        print("Waiting for server's attack...")
        attack = client.recv(1024).decode()
        row, col = map(int, attack.split(","))
        print(f"Server attacked: ({row}, {col})")
        board[row][col] = "*"

        # Check if the attack hits
        if is_hit(ships, row, col):
            ships.remove((row, col))
            # Check if all ships are sunk
            if not ships:
                print(bold_red("All your ships are sunk! You lose."))
                client.send("win".encode())
                break
            else:
                print(bold_green("Hit!"))
                client.send("hit".encode())
        else:
            print(bold_red("Miss."))
            client.send("miss".encode())
            

        

def start_game(conn, player):
    board = create_board()
    ships = place_ships(board)
    print("Your board:")
    print_board(board, hide_ships=False)

    if player == 'server':
        server_game(conn, board, ships)
    else:
        client_game(conn, board, ships)