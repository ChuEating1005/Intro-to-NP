# Server Side (Player B), Receive Invitation
import socket

host_ips = {"linux1.cs.nycu.edu.tw": "140.113.235.151", 
            "linux2.cs.nycu.edu.tw": "140.113.235.152",
            "linux3.cs.nycu.edu.tw": "140.113.235.153",
            "linux4.cs.nycu.edu.tw": "140.113.235.154"}
ipB = "140.113.235.152"
portB = 12002


def receive_invitation(udpserver_socket):
    print("Waiting for game invitation...")

    while True:
        # Receive the invitation
        message, client_address = udpserver_socket.recvfrom(1024)
        host = host_ips.keys()[host_ips.values().index(client_address)]
        print(f"Received invitation:\n### {message.decode()} ###\nfrom {host} on {client_address}")

        # Accept the invitation
        response = input("Do you accept the invitation? (Y/N): ").lower()
        if response == 'y':
            response = "Accepted"
            udpserver_socket.sendto(response.encode(), client_address)
            break
        else:
            response = "Declined"
            udpserver_socket.sendto(response.encode(), client_address)
            continue

def receive_portinfo(udpserver_socket):
    message, udpclient_address = udpserver_socket.recvfrom(1024)
    ipA, portA = message.decode().split(", ")
    portA = int(portA)
    print(f"Received player A's address: {ipA}:{portA}")
    return ipA, portA

def play_game(client_socket):
    # TCP connection to play Rock-Paper-Scissors
    while True:
        playerB_move = input("Enter your move (rock/paper/scissors): ").lower()
        client_socket.send(playerB_move.encode())
        playerA_move = client_socket.recv(1024).decode()

        print(f"Player A played: {playerA_move}")

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
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((ipB, portB))

    receive_invitation(server_socket)
    ipA, portA = receive_portinfo(server_socket)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((ipA, portA))
    play_game(client_socket, ipA, portA)

