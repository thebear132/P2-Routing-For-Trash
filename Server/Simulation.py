from time import sleep
import numpy as np
from socket import *
import pickle

class Simulation:   
    def __init__(self, PORT = 12445, start_listen = True):
        """
        Creates sockets as servers on both TCP and UDP using the C22-Sim Protocol
        """
        if start_listen != True:    #If start_listen == False -> simulate() debug mode
            return
        
        HOST = ''                   # All available interfaces. local/online DataStorage.py
        BUFFER_SIZE = 1024
        END_MESSAGE = b"stop"

        # TCP SOCKET
        TCP_handshake_socket = socket(AF_INET, SOCK_STREAM) # IPv4, TCP
        TCP_handshake_socket.bind((HOST, PORT))             # Bind(listen) sockect to the address
        TCP_handshake_socket.listen(1)                      # Listen for connections on the socket (0-5)

        while True:
            # Start both sockets for listening, as the protocol (to not lose messages in UDP as they are put into a buffer)
            UDP_data_socket = socket(AF_INET, SOCK_DGRAM)       # IPv4, UDP    

            """INITIAL HANDSHAKE PART (TCP)"""
            print('-----        TCP SERVER RUNNING        -----')
            print(f"Listening for incoming connections on {(HOST, PORT)}")
            
            # TCP handshake. c = SOCKET to client. a = ADDRESS of client
            TCP_connected_sock, tcpADDR = TCP_handshake_socket.accept()        
            print('[1] Connection received from {}'.format(tcpADDR))
            
            print(f"    Connecting UDP socket {(tcpADDR[0], PORT)}")
            UDP_data_socket.connect((tcpADDR[0], PORT))                  # Bind sockect to the address

            try:
                numberOfPackets = 0
                msg = b""
                print("[2] Receiving packets -> ", end="")
                while msg[-len(END_MESSAGE):] != END_MESSAGE:   # Check if END_MESSAGE is in a message yet
                    if len(msg) > len(END_MESSAGE): numberOfPackets += 1       # Only count message if more than END_MESSAGE
                    packetData = TCP_connected_sock.recv(BUFFER_SIZE)
                    msg = msg + packetData
                    print(".", end="")
                print(f"\n{numberOfPackets}: Packets recieved. Bytes:", len(msg))
            except Exception as e:  print("\nClient closed TCP socket. Assuming its done?", e)

            initData = pickle.loads(msg[:-len(END_MESSAGE)])      # Load msg but exclude END_MESSAGE
            #Split pickle object into variables
            seed = initData[0]
            fill_pct = initData[1]
            sendHyp = initData[2]
            time_stamps = initData[3]
            
            
            """SIMULATION PART (UDP)"""
            SIMULATED_DATA = self.simulate(seed, fill_pct, sendHyp, time_stamps)
            print(f"[5] Sending {len(SIMULATED_DATA)*len(SIMULATED_DATA[0])} UDP Sim data packets to DS")
            for sending_lap in SIMULATED_DATA:                  # For each sendings hyppighed
                for id in range(len(sending_lap)):              # for each molok in sending -> [(fillPct, timestamp)]
                    fill_pct = sending_lap[id][0]               # Grab fillPct
                    time_stamp = sending_lap[id][1]             # Grab timestamp
                    send_list = [id, fill_pct, time_stamp]      # Collect the values in a tuple with molokID

                    sl = pickle.dumps(send_list)                # dumps: (MolokID, fill_pct, sendhyp)
                    #sleep(0.01)
                    #print(send_list[0], end=", ")
                    UDP_data_socket.send(sl)
            
            
            end = pickle.dumps(END_MESSAGE.decode())                           # End session
            UDP_data_socket.send(end)
            
            """END SESSION"""
            # Close all sockets, ready for a new session
            TCP_connected_sock.close()
            #TCP_handshake_socket.close()
            UDP_data_socket.close()
            sleep(1)
            print("\n[6] SESSION WITH data storage ended")




    def simulate(self, seed, fill_pct, sendHyp, time_stamps):
        """Start simulation

        Args:
            seed (int): seed
            fill_pct (list): filling percentages for each molok
            sendHyp (int): how many times to simulate with the given values
            time_stamps (int): time stamps for each molok

        Returns:
            complete_list: [(new_fill, time_stamp), ...]
        """


        np.random.seed(seed)    #Set random seed
        # Normal gauss distribution: centre = 10, normal distribution = 3 og Output = 1
        degreeFilling = np.random.normal(10,3,len(fill_pct)) 
        Completelist = []
        interval = (24*(60*60))/sendHyp             # How many hours (in seconds) 
        
        for x in range(sendHyp):
            Now = max(time_stamps) + interval
            sendingsListe = []  #[(13,12), (15,12), (14,12)] fill_pct, time_stamp
            for i in range(len(fill_pct)):
                sendingsBehind = (Now-time_stamps[i])/interval
                
                for _ in range(int(sendingsBehind)):             # Simulate equal to how many sendings each molok is behind NOW
                    degreeFillingFreq = degreeFilling[i]/sendHyp # Degree filling is divided with sendHyp, to divide the sendHyp over 1 day
                    Deviation = np.random.normal(1, 0.1)       # Generates a number between 0.9 and 1.1 to create a deviation
                    new_fill = round(float(fill_pct[i] + degreeFillingFreq*Deviation), 2)
                    fill_pct[i] = new_fill
                    time_stamps[i] += interval

                sendingsListe.append((fill_pct[i],  time_stamps[i]))

            Completelist.append(sendingsListe[:])

        return Completelist


sim = Simulation(start_listen=True)
#print(sim.simulate(2, [2, 2, 2], 2, [1, 1, 1]))
