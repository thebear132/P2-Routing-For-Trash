import socket 
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9999 
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Ipv4 & User datagram protocol = UDP

numMoloks = 5
numSends = 1

for send in range(numSends):
    for molokId in range(numMoloks):
        msg = f"{molokId}, {10*(1 + send)}, {time.time()}"
        # time.sleep(0.1)
        s.sendto(bytes(msg,'utf-8'),(SERVER_IP,SERVER_PORT)) # Noget data ,  Addresse = serverIP + serverPort
        print(f"Message sent: {msg}")

# r,a = s.recvfrom(BUFFER_SIZE)
# print("Recevied from server")
# print("a:",a)
# print("r:", r)