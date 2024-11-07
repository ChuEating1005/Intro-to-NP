import socket

def client_program():
    host = input("Enter server IP: ")  # e.g., 127.0.0.1
    port = int(input("Enter server port: "))  # e.g., 5000

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))

    try:
        while True:
            server_message = client.recv(1024).decode()
            print(server_message, end="")  # Display server message to the user
            if "Goodbye" in server_message:
                break
            client_message = input()  # Take user input
            client.send(client_message.encode())
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    client_program()
