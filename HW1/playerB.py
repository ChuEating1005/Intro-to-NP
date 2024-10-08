# Server Side (Player B), Receive Invitation
import socket

host_ips = {"linux1.cs.nctu.edu.tw": "140.113.235.151", 
            "linux2.cs.nctu.edu.tw": "140.113.235.152",
            "linux3.cs.nctu.edu.tw": "140.113.235.153",
            "linux4.cs.nctu.edu.tw": "140.113.235.154"}
ip_host = {"140.113.235.151": "linux1.cs.nycu.edu.tw",
            "140.113.235.152": "linux2.cs.nycu.edu.tw",
            "140.113.235.153": "linux3.cs.nycu.edu.tw",
            "140.113.235.154": "linux4.cs.nycu.edu.tw"}
ipB = host_ips[socket.gethostname()]
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
  ____(____    '---
 (______
(_______
 (_______
      (__________.---
    """,
    "scissors" : """
        _______
  ____(____    '---
 (______
(__________
      (____)
       (___)__.---
    """}

def select_port():
    available_ports = []
    # Select an available port
    for port in range(18001, 18005):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind((ipB, port))
            s.close()
            available_ports.append(port)
        except OSError:
            continue
    for i, port in enumerate(available_ports):
        print(f"{i+1}. Port {port}")
    select = int(input("Select a port: "))
    return available_ports[select-1]

def waiting_invitation(udpserver_socket):
    print("Waiting for game invitation...")

    while True:
        # Receive the invitation
        message, udpclient_address = udpserver_socket.recvfrom(1024)

        if message.decode() == "ping":
            response = "pong"
            udpserver_socket.sendto(response.encode(), udpclient_address)
            continue
        elif message.decode() == "Game Invitation: Rock-Paper-Scissors":
            ipA = udpclient_address[0]
            print(f"Received invitation from {ip_host[ipA]} on {ipA}: ")
            print(f"\n### {message.decode()} ###\n")

            # Accept the invitation
            response = input("Do you accept the invitation? (Y/N): ").lower()
            if response == 'y':
                response = "Accepted"
                udpserver_socket.sendto(response.encode(), udpclient_address)
                break
            else:
                response = "Declined"
                udpserver_socket.sendto(response.encode(), udpclient_address)
                continue

def receive_portinfo(udpserver_socket):
    while True:
        message, udpclient_address = udpserver_socket.recvfrom(1024)
        addr = message.decode().split(", ")
        if len(addr) != 2:
            print("Invalid address format. Please try again.")
            continue
        else:
            ipA, portA = addr
            break
    portA = int(portA)
    print(f"Received player A's address: {ipA}:{portA}")
    return ipA, portA

def play_game(tcpclient_socket):
    # TCP connection to play Rock-Paper-Scissors
    move = ["rock", "paper", "scissors"]
    while True:
        select = int(input("Enter your move (1. rock / 2. paper / 3. scissors): ").lower())
        playerB_move = move[select-1]
        print(f"You played: \n{pB_image[playerB_move]}\n")
        tcpclient_socket.send(playerB_move.encode())
        playerA_move = tcpclient_socket.recv(1024).decode()
        print(f"Opponent played: \n{pA_image[playerA_move]}\n")

        if playerA_move == playerB_move:
            print("It's a tie!, play again")
            continue
        elif (playerB_move == 'rock' and playerA_move == 'scissors') or \
            (playerB_move == 'scissors' and playerA_move == 'paper') or \
            (playerB_move == 'paper' and playerA_move == 'rock'):
            print("You win! Congratulations!")
        else:
            print("You lose! Game over!")
        
        contB = input("Do you want to play again? (Y/N): ").lower()
        if contB == 'n':
            tcpclient_socket.send("leave".encode())
            break
        
        tcpclient_socket.send("continue".encode())
        contA = tcpclient_socket.recv(1024).decode()
        if contA == 'continue':
            continue
        else:
            print("PlayerA has left the game...")
            break

def main():
    portB = select_port()
    udpserver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpserver_socket.bind((ipB, portB))

    waiting_invitation(udpserver_socket)
    ipA, portA = receive_portinfo(udpserver_socket)
    udpserver_socket.close()

    tcpclient_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpclient_socket.connect((ipA, portA))
    play_game(tcpclient_socket)
    tcpclient_socket.close()

if __name__ == "__main__":
    main()