# Clinet Side (Player A), Send Invitation
import socket

host_ips = {"linux1.cs.nycu.edu.tw": "140.113.235.151", 
            "linux2.cs.nycu.edu.tw": "140.113.235.152",
            "linux3.cs.nycu.edu.tw": "140.113.235.153",
            "linux4.cs.nycu.edu.tw": "140.113.235.154"}

ip_host = {"140.113.235.151": "linux1.cs.nycu.edu.tw",
            "140.113.235.152": "linux2.cs.nycu.edu.tw",
            "140.113.235.153": "linux3.cs.nycu.edu.tw",
            "140.113.235.154": "linux4.cs.nycu.edu.tw"}
search_port = [18000, 18005]
ipA = "140.113.235.151"
portA = 12000

def send_invitation(udpclient_socket):
    
    print("Search for waiting players...")
    
    message = "Game Invitation: Rock-Paper-Scissors"
    available_servers = []

    for ip in host_ips.values():
        for port in range(search_port[0], search_port[1]+1):
            udpclient_socket.sendto(message.encode(), (ip, port))
            try:
                response, udpserver_addr = udpclient_socket.recvfrom(1024)
                if response.decode() == "Accepted":
                    print(f"{ip_host[ip]} accept the invitation, player address: {ip}:{port}")
                    available_servers.append((ip_host[ip], ip, port))
            except socket.timeout:
                pass

    return available_servers

def choose_server(available_servers):
    if not available_servers:
        print("No available players found.")
        return None
    else:
        print("Choose a player to play the game.")
        for i, server in enumerate(available_servers):
            print(f"{i+1}. {server[0]} on {server[1]}:{server[2]}")
        choice = int(input("Enter the number of the player: "))
        return available_servers[choice-1]
    
def send_portinfo(udpclient_socket, ipB, portB):
    message = ipA + ', ' + str(portA)
    print(f"Send address to Player B: {message}")
    udpclient_socket.sendto(message.encode(), (ipB, portB))

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

    udpclient_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpclient_socket.settimeout(1)

    available_udpservers = send_invitation(udpclient_socket)
    playerB_server = choose_server(available_udpservers)

    send_portinfo(udpclient_socket, playerB_server[1], playerB_server[2])

    tcpserver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpserver_socket.bind((ipA, portA))
    tcpserver_socket.listen(1)
    print("Waiting for player B to join the game...")

    conn, addr = tcpserver_socket.accept()
    print(f"Player B has joined the game!")

    start_game(conn)
    conn.close()
    udpclient_socket.close()
    tcpserver_socket.close()

if __name__ == "__main__":
    main()