from time import sleep
import numpy as np
from socket import *
import pickle
from tqdm import tqdm


class Simulation:   
    def __init__(self, PORT = 50050, start_listen = True):
        """
        Client protocol UDP use for communicating with data storage  
        Port is set to 50050 
        """
        if start_listen != True:    #Dont start the server if start_listen == False
            return
        
        # TCP SOCKET
        HOST = ''                   # Symbolic name meaning all available interfaces
        BUFFER_SIZE = 1024          # Receive Buffer size (power of 2)
        
        while True:                          # KEEP SERVICE LISTENING FOREVER
            """INITIAL HANDSHAKE PART (TCP)"""
            s = socket(AF_INET, SOCK_STREAM) # IPv4, TCP
            s.bind((HOST, PORT))             # Bind(listen) sockect to the address
            s.listen(1)                      # Listen for connections on the socket (0-5)
            print('\n\n____TCP server running...____')
            print('Listening for incoming connections in port '+str(PORT))
            
            # ____ TCP HANDSHAKE ____
            tcpSock, tcpADDR = s.accept()                           # Accepts a TCP connection. c = SOCKET to client. a = ADDRESS of client
            print('* Connection received from {}'.format(tcpADDR))
            
            try:
                msg = b""
                packetData = tcpSock.recv(BUFFER_SIZE)              # receive message, convert to string
                numberOfPackets = 0
                while packetData != b"end":                         # If not "end", continue recieving
                    numberOfPackets += 1
                    msg = msg + packetData
                    packetData = tcpSock.recv(BUFFER_SIZE)
                print(f"{numberOfPackets}: Packets recieved")

            except Exception as e:
                print("Client closed TCP socket. Assuming its done?")
                print("SOMETHING MIGHT HAVE GONE WRONG?", e)

            initData = pickle.loads(msg)      # Decode received data
            
            #Split receive data into variables
            seed = initData[0]
            fill_pct = initData[1]
            sendHyp = initData[2]
            time_stamps = initData[3]
            #print(initData)
            s.close()                       # Close the TCP socket after data is received


            # UDP SOCKET
            """SIMULATION PART (UDP)""" 
            s = socket(AF_INET, SOCK_DGRAM) # IPv4, UDP
            s.bind((HOST, PORT))            # Bind sockect to the address

            udpADDR = (tcpADDR[0], PORT)    # Update to send
            sleep(5)
            print("Sending UDP Sim data to", udpADDR)
            

            SIMULATED_DATA = self.simulate(seed, fill_pct, sendHyp, time_stamps)
            for sending_lap in SIMULATED_DATA:                  # Take the inner list
                for id in range(len(sending_lap)):              # Iterate for each tuple 
                    
                    fill_pct = sending_lap[id][0]               # Set their values
                    time_stamp = sending_lap[id][1]             # Set their values
                    send_list = [id, fill_pct, time_stamp]      # Collect in a tuple

                    sl = pickle.dumps(send_list)                # Convert into bytes
                    sleep(1)                                    # Checking for packet loss
                    #print(send_list)
                    print(send_list[0], end=", ")

                    s.sendto(sl, udpADDR)                       # send: [MolokID, fill_pct, sendhyp]
            
            
            end = pickle.dumps('end')                           # End session
            s.sendto(end, udpADDR)
            s.close()
            print("\n\nSESSION WITH", udpADDR, "ended")


    def simulate(self, seed, fill_pct, sendHyp, time_stamps):
        """Start the simulation 

        Args:
            seed (int): seed
            fill_pct (list): list of filling procent for each moloks 
            sendHyp (int): how often to simulate pr day
            time_stamps (int): time 

        Returns:
            complete_list: [new_fill, time_stamp]
        """


        np.random.seed(seed)    #Set random seed
        degreeFilling = np.random.normal(10,3) # Normal gauss distribution: centre = 10, normal distribution = 3 og Output = 1
        Completelist = []
        interval = (24*(60*60))/sendHyp
        
        for x in range(sendHyp):
            Now = max(time_stamps) + interval
            sendingsListe = []  #[(13,12), (15,12), (14,12)] fill_pct, time_stamp
            for i in range(len(fill_pct)):
                sendingsBehind = (Now-time_stamps[i])/interval
                
                for _ in range(int(sendingsBehind)):             # Simulate equal to how many sendings each molok is behind NOW
                    degreeFillingFreq = degreeFilling[i]/sendHyp # Degree filling is divided with sendHyp, to divide the sendHyp over 1 day
                    Deviation = np.random.random()*0.2+0.9       # Generates a number between 0.9 and 1.1 to create a deviation
                    new_fill = round(float(fill_pct[i] + degreeFillingFreq*Deviation), 2)
                    fill_pct[i] = new_fill
                    time_stamps[i] += interval

                sendingsListe.append((fill_pct[i],  time_stamps[i]))

            Completelist.append(sendingsListe[:])
            
        return Completelist


if __name__ == "__main__":
    sim = Simulation(start_listen=False)
    