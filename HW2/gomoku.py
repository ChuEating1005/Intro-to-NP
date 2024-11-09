import socket
BOARD_SIZE = 10

def bold_green(text):
    return "\033[32;1m" + text + "\033[0m"

def bold_red(text):
    return "\033[31;1m" + text + "\033[0m"

def display_board(board):
    """
    Display the Gomoku board with proper alignment.
    """
    # Print column headers
    board_str = "     " + " ".join(f"{i}" for i in range(BOARD_SIZE)) + "\n"
    # Print rows with row headers
    for i, row in enumerate(board):
        board_str += f"{i:2} | " + " ".join(row) + "\n"
    return board_str


def is_valid_move(board, row, col):
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE and board[row][col] == "."

def check_winner(board, row, col, symbol):
    """
    Check if a player has won the game.
    """
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    for dr, dc in directions:
        count = 1
        for step in range(1, 5):
            r, c = row + step * dr, col + step * dc
            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and board[r][c] == symbol:
                count += 1
            else:
                break
        for step in range(1, 5):
            r, c = row - step * dr, col - step * dc
            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and board[r][c] == symbol:
                count += 1
            else:
                break
        if count >= 5:
            return True
    return False

def start_game(conn, player):
    board = [["." for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    symbol = 'X' if player == "server" else 'O'
    turn = symbol == "X"  # Player X always starts

    while True:
        if turn:  # Player's turn
            print(f"\nYour turn!")
            print(display_board(board))
            while True:
                try:
                    move = input("Enter row and column (e.g., 7 8): ")
                    row, col = map(int, move.split())
                    if is_valid_move(board, row, col):
                        board[row][col] = symbol
                        conn.send(f"{row} {col}".encode())
                        break
                    else:
                        print("Invalid move. Try again.")
                except ValueError:
                    print("Invalid input. Enter row and column as numbers separated by a space.")
        else:  # Opponent's turn
            print(f"\nWaiting for opponent's move...")
            move = conn.recv(1024).decode().strip()
            if not move:  # Connection closed
                print("Connection lost with opponent.")
                break
            row, col = map(int, move.split())
            board[row][col] = "O" if symbol == "X" else "X"
            print(f"Opponent moved at ({row}, {col}).")

        # Check for a win or draw
        if check_winner(board, row, col, board[row][col]):
            if turn:
                print(bold_green("You win!"))
            else:
                print(bold_red("You lose!"))
            break
        if all(board[r][c] != "." for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)):
            print("\nThe game is a draw!")
            break

        turn = not turn  # Toggle turn