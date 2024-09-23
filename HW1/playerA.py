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
search_port = [18001, 18005]
ipA = "140.113.235.151"
portA = 1800
pA_image = {
    "rock" : """
    _______
---'   ____)
      (_____)
      (_____)
      (____)
---.__(___)
    """,
    "paper" : """
     _______
---'    ____)____
           ______)
          _______)
         _______)
---.__________)
    """,
    "scissors" : """
    _______
---'   ____)____
          ______)
       __________)
      (____)
---.__(___)
    """}
pB_image = {
    "rock" : """
        _______
     (____   '---
    (_____)
    (_____)
     (____)
      (___)__.---
    """,
    "paper" : """
        _______
  ____)____    '---
 (______
(_______
 (_______
      (__________.---
    """,
    "scissors" : """
        _______
  ____)____    '---
 (______
(__________
      (____)
       (___)__.---
    """}

def search_waiting_server(udpclient_socket):
    print("Search for waiting players...")

    message = "ping"
    available_servers = []

    for ip in host_ips.values():
        for port in range(search_port[0], search_port[1]+1):
            udpclient_socket.sendto(message.encode(), (ip, port))
        try:
            response, udpserver_addr = udpclient_socket.recvfrom(1024)
            ipB, portB = udpserver_addr[0], udpserver_addr[1]
            if response.decode() == "pong":
                available_servers.append((ip_host[ipB], ipB, portB))
        except socket.timeout:
            pass
    return available_servers

def choose_server(available_servers):
    if not available_servers:
        print("No available players found... Keep searching.")
        return None
    else:
        print("Choose a player to send invitation:")
        for i, server in enumerate(available_servers):
            print(f"{i+1}. {server[0]} on {server[1]}:{server[2]}")
        choice = int(input("Enter the number of the player: "))
        return available_servers[choice-1]
    
def send_invitation(udpclient_socket, ipB, portB):
    print("Send game invitation to other players...")

    message = "Game Invitation: Rock-Paper-Scissors"
    available_servers = []

    udpclient_socket.sendto(message.encode(), (ipB, portB))
    try:
        response, addr = udpclient_socket.recvfrom(1024)
        if response.decode() == "Accepted":
            print(f"{ip_host[ipB]} accept the invitation, player address: {ipB}:{portB}")
            return True
        elif response.decode() == "Declined":
            print(f"{ip_host[ipB]} declined the invitation... Keep searching.")
            return False
    except socket.timeout:
        pass
    
    print(f"{ip_host[ipB]} does not respond... Keep searching.")
    return False


    
def send_portinfo(udpclient_socket, ipB, portB):
    message = ipA + ', ' + str(portA)
    print(f"Send address to Player B")
    udpclient_socket.sendto(message.encode(), (ipB, portB))

def start_game(conn):
    # TCP connection to play Rock-Paper-Scissors
    move = ["rock", "paper", "scissors"]
    while True:
        select = int(input("Enter your move (1. rock / 2. paper / 3. scissors): ").lower())
        playerA_move = move[select-1]
        print(f"You played: \n{pA_image[playerA_move]}\n")
        
        playerB_move = conn.recv(1024).decode()
        conn.send(playerA_move.encode())
        print(f"Opponent played: \n{pB_image[playerB_move]}\n")

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
    udpclient_socket.settimeout(5)

    while True:
        available_udpservers = []
        available_udpservers = search_waiting_server(udpclient_socket)
        playerB_server = choose_server(available_udpservers)
        if send_invitation(udpclient_socket, playerB_server[1], playerB_server[2]):
            break

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