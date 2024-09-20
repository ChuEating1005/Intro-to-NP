# Clinet Side (Player A), Send Invitation
import socket

host_ips = {"linux1.cs.nycu.edu.tw": "140.113.235.151", 
            "linux2.cs.nycu.edu.tw": "140.113.235.152",
            "linux3.cs.nycu.edu.tw": "140.113.235.153",
            "linux4.cs.nycu.edu.tw": "140.113.235.154"}
search_port = [12000, 12020]
ipA = "140.113.235.151"
portA = 12001

def send_invitation(client_socket):
    
    print("Search for waiting players...")
    
    message = "Game Invitation: Rock-Paper-Scissors"
    available_servers = []

    for ip in host_ips:
        for port in range(search_port[0], search_port[1]+1):
            client_socket.sendto(message.encode(), (ip, port))
            try:
                response, addr = client_socket.recvfrom(1024)
                if response.decode() == "Accepted":
                    host = list(host_ips.keys())[list(host_ips.values()).index(ip)]
                    print(f"{host} accept the invitation, player address: {ip}:{port}")
                    available_servers.append((host, ip, port))
            except socket.timeout:
                pass

    return available_servers

def choose_server(available_servers):
    if not available_servers:
        print("No available players found.")
        return None
    else:
        print("Choose a player to play the game.")
        for i, host, ip, port in enumerate(available_servers):
            print(f"{i+1}. {host} on {ip}:{port}")
        choice = int(input("Enter the number of the player: "))
        return available_servers[choice-1]
    
def send_portinfo(client_socket, ipB, portB):
    client_socket.sendto(f"{ipA}, {portA}".encode(), (ipB, portB))

def start_game(conn):
    # TCP connection to play Rock-Paper-Scissors
    while True:
        
        playerB_move = conn.recv(1024).decode()
        playerA_move = input("Enter your move (rock/paper/scissors): ").lower()
        conn.send(playerA_move.encode())

        print(f"Player B played: {playerB_move}")

        if playerA_move == playerB_move:
            print("It's a tie!, play again")
            continue
        elif (playerA_move == 'rock' and playerB_move == 'scissors') or \
            (playerA_move == 'scissors' and playerB_move == 'paper') or \
            (playerA_move == 'paper' and playerB_move == 'rock'):
            print("You win! Congratulations!")
            break
        else:
            print("You lose! Game over!")
            break

def main():

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(1)

    available_servers = send_invitation(client_socket)
    server = choose_server(available_servers)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((ipA, portA))
    server_socket.listen(1)
    print("Waiting for player B to join the game...")

    conn, addr = server_socket.accept()
    print(f"Player B has joined the game!")

    start_game(conn, server[1], server[2])
    conn.close()
    server_socket.close()

if __name__ == "__main__":
    main()