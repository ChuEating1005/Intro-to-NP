# Server Side (Player B), Receive Invitation
import socket

host_ips = {"linux1.cs.nycu.edu.tw": "140.113.235.151", 
            "linux2.cs.nycu.edu.tw": "140.113.235.152",
            "linux3.cs.nycu.edu.tw": "140.113.235.153",
            "linux4.cs.nycu.edu.tw": "140.113.235.154"}
ip_host = {"140.113.235.151": "linux1.cs.nycu.edu.tw",
            "140.113.235.152": "linux2.cs.nycu.edu.tw",
            "140.113.235.153": "linux3.cs.nycu.edu.tw",
            "140.113.235.154": "linux4.cs.nycu.edu.tw"}
ipB = "140.113.235.152"
portB = 12003


def receive_invitation(udpserver_socket):
    print("Waiting for game invitation...")

    while True:
        # Receive the invitation
        message, udpclient_address = udpserver_socket.recvfrom(1024)
        ipA = udpclient_address[0]
        print(f"Received invitation:\n### {message.decode()} ###\nfrom {ip_host[ipA]} on {ipA}")

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
    message, udpclient_address = udpserver_socket.recvfrom(1024)
    ipA, portA = message.decode().split(", ")
    portA = int(portA)
    print(f"Received player A's address: {ipA}:{portA}")
    return ipA, portA

def play_game(tcpclient_socket):
    # TCP connection to play Rock-Paper-Scissors
    while True:
        playerB_move = input("Enter your move (rock/paper/scissors): ").lower()
        tcpclient_socket.send(playerB_move.encode())
        playerA_move = tcpclient_socket.recv(1024).decode()

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
    udpserver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpserver_socket.bind((ipB, portB))

    receive_invitation(udpserver_socket)
    ipA, portA = receive_portinfo(udpserver_socket)
    udpserver_socket.close()

    tcpclient_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpclient_socket.connect((ipA, portA))
    play_game(tcpclient_socket)
    tcpclient_socket.close()

if __name__ == "__main__":
    main()