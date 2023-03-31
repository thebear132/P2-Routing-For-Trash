import socket 
import time

SERVER_IP = "192.168.137.1"
SERVER_PORT = 9999 
BUFFER_SIZE = 1024
timestamp = time.time()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Ipv4 & User datagram protocol = UDP
while True: 
    List = [(1, 30, timestamp), (1, 30, timestamp), (1, 30, timestamp), (1, 30, timestamp), (1, 30, timestamp), (1, 30, timestamp)]
    for i in range(len(list)):
        msg = f"{i}"
        s.sendto(bytes(msg,'utf-8'),(SERVER_IP,SERVER_PORT)) # Noget data ,  Addresse = serverIP + serverPort
        print("Data sent.")
    
    r,a = s.recvfrom(BUFFER_SIZE)
    print("Recevied from server")
    print("a:",a)
    print("r:", r)