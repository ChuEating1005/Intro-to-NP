import threading

welcome = """\033[34;1m
 __      __       .__                             ._.
/  \    /  \ ____ |  |   ____  ____   _____   ____| |
\   \/\/   // __ \|  | _/ ___\/  _ \ /     \_/ __ \ |
 \        /\  ___/|  |_\  \__(  <_> )  Y Y  \  ___/\|
  \__/\  /  \___  >____/\___  >____/|__|_|  /\___  >_
       \/       \/          \/            \/     \/\/
\033[0m"""

show = "\033[33;1m\n= List =============================================\n\033[0m"
success = "\033[33;1m\n= Success ==========================================\n\033[0m"
failed = "\033[33;1m\n= Error ============================================\n\033[0m"
br = "\033[33;1m====================================================\n\n\033[0m"

def welcome_msg(conn):
    conn.send(welcome.encode())

def invalid(conn):
    failed_msg(conn, "Invalid option. Try again.")

def bold_green(text):
    return "\033[32;1m" + text + "\033[0m"

def bold_red(text):
    return "\033[31;1m" + text + "\033[0m"

def bold_blue(text):
    return "\033[34;1m" + text + "\033[0m"

def list_msg(conn, text):
    conn.send((show + bold_blue(text) + br).encode())

def success_msg(conn, text):
    conn.send((success + bold_green(text + "\n") + br).encode())

def failed_msg(conn, text):
    conn.send((failed + bold_red(text + "\n") + br).encode())

def system_msg(conn, text):
    conn.send(bold_blue("[System] " + text).encode())

def broadcast_message(message, exclude_conn):
    from utils.user import online_lock, online_players
    """
    Broadcast a message to all connected clients except the excluded one
    """
    def send_to_client(conn, message):
        try:
            system_msg(conn, message)
        except Exception as e:
            print(f"Error broadcasting to client: {e}")

    all_conn = []
    with online_lock:
        for conn, _, _ in online_players.values():
            all_conn.append(conn)
    
    for conn in all_conn:
        if conn != exclude_conn:
            # 為每個客戶端創建一個新線程來發送消息
            threading.Thread(target=send_to_client, 
                            args=(conn, message), 
                            daemon=True).start()
