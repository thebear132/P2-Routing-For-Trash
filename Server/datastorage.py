import socket
import pandas as pd
import numpy as np
import time

class DataStorage:
    """
    Handles data from sigfox or simulation.

    Logs data in pd.dataframe

    Stores data in CSV as "cold storage" - works!

    Loads CSV if simulation continues at later time - works!

    Manipulates data and presents it to 'Route Planner' or 'GUI'

    """

    def __init__(self, seed: any, molok_Ids = [], molok_positions = [], loadCSV_fileName = "", ADDR = ('127.0.0.1', 9999)) -> None:
        """
        There are two different ways to initialize DataStorage:
        1. with ADDR = '(IP, PORT)' -> creates server socket for communication with simulation
        ADDR must be server address.
        2. with ADDR = "sigfox" -> creates client socket/ comm link with sigfox
        """

        if len(molok_Ids) != len(molok_positions):
            print(f"length of molokIds ({len(molok_Ids)}) is NOT equal to length of molok_positions ({len(molok_positions)}). They must be equal")
            exit()


        # --- config vars ---
        if loadCSV_fileName: # var is string of file name to be opened
            self.df = self.loadCSV(loadCSV_fileName)
            """work in progress"""
            self.seed = int(loadCSV_fileName[4:6]) # used for naming purposes

        else:
            self.seed = seed
            self.rng = np.random.default_rng(seed=seed) # creates a np.random generator-object with specified seed. Use self.rng for randomness
            self.df = self.create_df(molok_Ids, molok_positions)

        # --- socket vars ---
        if type(ADDR) == tuple: # checks that user wants to create socket for UDP comms with simulation
            self.ADDR = ADDR
            self.BUFFER_SIZE = 1024
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP

            self.socket.bind(self.ADDR)

            print('Provided ADDR indicates simulation is to be run. UDP server running...')
            print(f'Listening for incoming connections on address '+str(self.ADDR))
        
        # --- sigfox vars ---
        else: # if not simulation, then sigfox comms
            """
            Sigfox: når vi ved hvordan det virker
            """
            pass

    
    def create_df(self, molokIds, molokPos):
        """creates the dataframe with vars from __init__()"""
        df_dict = {
            'Id': molokIds,
            'pos': molokPos,
            'fillPct': self.rng.normal(loc=30, scale=10, size=len(molokIds)), # random starting fill% for each molok
            'datetime': np.array(len(molokIds) * [time.time()]) # starting time of 'first measurement'
        }

        return pd.DataFrame.from_dict(df_dict)


    def loadCSV(self, fileName):
        """loads data from CSV with fileName into self.df"""
        
        dataframe = pd.read_csv(f"Server/CSVFolder/{fileName}", sep=';')
        
        return dataframe


    def saveCSV(self):
        """saves data from self.df to CSV based on self.seed and len(self.molok_Ids)"""

        # --- naming convention --- creates full filename based on config vars
        fileName = f"seed{self.seed}_NumMoloks{len(self.df['Id'])}.csv"

        self.df.to_csv(f"Server/CSVFolder/{fileName}", sep=';', index=False) # saves CSV to CSVFolder.
        print("Succesfully saved CSV to CSVFolder. Its name is:" + fileName)

        return fileName
    
    
    def handleSimThread(self):
        """handles comms with simulation. Only call if simulating.
        Runs handleSim() in a thread."""

        pass

    def handleSim(self):
        """Called by handleSimThread(). Handles comms with sim"""

        msg, clientADDR = self.socket.recvfrom(self.BUFFER_SIZE) # socket.recvfrom() also returns senders ADDR.

        pass


    def handleSigfox(self):
        """handles comms with sigfox. Only call if using measuring devices"""
        pass

    
    def log(self, molokId, fillPct, datetime):
        """logs data from comms handling functions 'handleSigfox' or 'handleSim' into self.df"""

    

if __name__ == "__main__":
    
    molok_Ids = [0, 1, 2, 3]
    molok_pos = [(22, 10), (67, 24), (76, 54), (80, 100)]

    myDS = DataStorage(69, molok_Ids, molok_pos)
    print(myDS.df)
    file_name = myDS.saveCSV()


    print("Opening new DS and loading file")
    myDS2 = DataStorage(69, ADDR='sigfox' , loadCSV_fileName=file_name)

    print(myDS2.df)

