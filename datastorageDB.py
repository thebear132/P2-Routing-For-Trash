import socket
import sqlite3 as lite
import numpy as np
import time
import threading
import pickle
from scipy import stats
import hashlib
import requests
import json


class DataStorage:
    """
    Handles data from sigfox or simulation.
    Logs data in DB
    Manipulates data and presents it to 'Route Planner' or 'GUI'
    """

    def __init__(self, seed: any, num_moloks: int, center_coordinates = (57.01466, 9.987159), scale = 0.01 , ADDR = ('127.0.0.1', 9999)) -> None:
        """
        There are two different ways to initialize DataStorages comms
        1. with ADDR = '(IP, PORT)' -> creates server socket for communication with simulation
        ADDR must be server address.
        2. with ADDR = "sigfox" -> creates client socket/ comm link with sigfox

        There are two different ways to use the DB
        1. with TABLE_NAME as "" (empty string) -> creates new TABLE in DB based on config vars
        2. with TABLE_NAME as "XYZ" (actual name) -> opens TABLE in DB with TABLE_NAME
        """

        # --- config vars ---
        self.DB_NAME = "Server\MolokData.db" # fix stien senere
        self.main_con = lite.connect(self.DB_NAME) # creates connection to DB from main thread
        self.main_cur = self.main_con.cursor() # creates cursor for main thread

        self.seed = seed
        self.rng = np.random.default_rng(seed=seed) # creates a np.random generator-object with specified seed. Use self.rng for randomness
        self.num_moloks = num_moloks
        self.center_coords = center_coordinates
        self.scale = scale

        # --- socket vars ---
        if type(ADDR) == tuple: # checks that user wants to create socket for UDP comms with simulation
            
            self.table_name = f"sim_seed{self.seed}_NumM{self.num_moloks}"

            self.sim_ADDR = ADDR
            self.BUFFER_SIZE = 1024
            self.END_MSG = "end"
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP

            # self.socket.connect(self.simADDR) # connecting to simulation address
            self.socket.connect(self.sim_ADDR)

            self.sim_thread = None # creating simThread variable
            
            print('Provided ADDR indicates simulation is to be run. UDP client ready...')
        
        # --- sigfox vars ---
        elif ADDR == "sigfox":
            self.table_name = f"sigfox_seed{self.seed}_NumM{self.num_moloks}"
            print("Call 'get_sigfox_data()' to get sigfox data. The ID's are 0 or 1")


        # create new table if TableName not in DBTables
        if not self.table_name in self.getTableNames():
            print(f"{self.table_name} not found in table names. Creating it now")
            self.createTable(self.table_name)


    def getTableNames(self):
        """returns table names from DB"""
        self.main_cur.execute("SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        return [i[0] for i in list(self.main_cur)]

    def createTable(self, table_name):
        """creates new table in DB with tableName"""
        self.main_cur.execute(f"CREATE TABLE {table_name}(ID INTEGER PRIMARY KEY, molokID INTEGER, molokPos TUPLE, fillPct REAL, timestamp REAL)")
        if table_name[:3] == "sim": # only auto generate data if simulations are to be run
            self.generate_init_data(table_name)
        return True

    def showTableByName(self, TableName):
        """shows Table with TableName from DB"""
        self.main_cur.execute(f"SELECT * FROM '{TableName}'")

        return np.array(list(self.main_cur))
    
    def showColumnNamesByTableName(self, TableName):
        """Shows columns of specified table with TableName"""
        self.main_cur.execute(f"PRAGMA table_info('{TableName}')")

        return np.array(self.main_cur.fetchall())

    def fetch_data_by_molok_ID(self,table_name, Id):
        """Returns all rows with specified Id"""
        self.main_cur.execute(f"SELECT * FROM '{table_name}' WHERE molokID = '{Id}'")

        return np.array(self.main_cur.fetchall()) 
    
    def fetchColumn(self, TableName, ColumnName):
        """Returns a specified column as a Numpy array"""
        self.main_cur.execute(f"SELECT {ColumnName} FROM '{TableName}'")

        return np.array(self.main_cur.fetchall())
    
    def fetchLatestRows(self, TableName, cursor: str):
        """returns array containing a row for each molokId with its latest ID"""
        if cursor == "main":
            self.main_cur.execute(f"SELECT MAX(ID), molokID, molokPos, fillPct, timestamp FROM '{TableName}' GROUP BY molokID")
            return np.array(self.main_cur.fetchall())
        elif cursor == "sim":
            self.simCur.execute(f"SELECT MAX(ID), molokID, molokPos, fillPct, timestamp FROM '{TableName}' GROUP BY molokID")
            return np.array(self.simCur.fetchall())

    def dropTable(self, tableName):
        """
        EXTREME DANGER!!!!!
        ---
        This method deletes a table by TableName FOREVER!
        """
        # check if tableName is in DB:
        self.main_cur.execute(f"DROP TABLE IF EXISTS '{tableName}'")
        return f"You just deleted table {tableName} if it even existed"

    def generate_init_data(self, tableName):
        """Internal method. Called when creating table in order to fill it with initial data for each molok. Just a single datapoint for each"""

        # sim mollok id (the molok id's will be passed when calling this function in __main__ and if the table is empty)

        # sim molok pos 
        norm_dist_lat = self.rng.normal(self.center_coords[0], self.scale/2, size = self.num_moloks)
        norm_dist_long = self.rng.normal(self.center_coords[1], self.scale, size = self.num_moloks)
        molok_coords = np.array(list(zip(norm_dist_lat, norm_dist_long)))
        print("molok coords", molok_coords)
       # sim fillPcts - use random (not normDist)
    
        init_fill_pcts = 50 * self.rng.random(self.num_moloks)
        print("init", init_fill_pcts)
        
        # sim timestamp
        timestamp = time.time()
        
        for i in range(self.num_moloks):
            
            # insert (molokID, molokPos, fillPcts, timestamp) into DB ; where i is molok id 
            self.main_cur.execute(f"INSERT INTO {tableName}(molokID, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (i, str(molok_coords[i]), init_fill_pcts[i], timestamp))
        self.main_con.commit()

        return True

    def split_fillpcts_to_sections(self, fillpcts_array, timestamp_array):
        """split filpcts and their timestamps into sections to account for emptying moloks"""

        sections_dict = {}
        section = 0
        first_index = 0

        for cur_index in range(1, len(fillpcts_array)):
            
            # putting fillpcts from 0-100 into sections_dict by a first and current index
            if fillpcts_array[cur_index] < fillpcts_array[cur_index - 1] * 0.9: # mult by 0.9 for if measuring device is inacurate
                timestamp_section = timestamp_array[first_index:cur_index]
                fillpcts_section = fillpcts_array[first_index:cur_index]
                sections_dict[section] = np.vstack((timestamp_section, fillpcts_section))
                
                section += 1
                first_index = cur_index
            
            # putting last section into dict
            elif cur_index == len(fillpcts_array) - 1:
                timestamp_section = timestamp_array[first_index:]
                fillpcts_section = fillpcts_array[first_index:]
                sections_dict[section] = np.vstack((timestamp_section, fillpcts_section))
                
        return sections_dict

    def lin_regg_sections(self):
        """find all sections for each molok and do linear reggresion on each section. A section is between each emptying"""

        growthrates_dict = {}

        for molok_id in range(self.num_moloks):
            molok_data = self.fetch_data_by_molok_ID(self.table_name, molok_id)
            
            first_timestamp = molok_data[0][4] # epoch time

            x_array = np.zeros(len(molok_data))
            y_array = np.zeros(len(molok_data))

            for row_index in range(len(molok_data)):
                timestamp = molok_data[row_index][4] # x-axis for lin. reg. model.
                fill_pct = molok_data[row_index][3] # y-axis
                                
                # subtracting by first timestamp to make graphing since time = 0 on x-axis
                timestamp = float(timestamp) - float(first_timestamp)

                x_array[row_index] = timestamp # putting timestamps in the first array of molok_id
                y_array[row_index] = fill_pct # putting fill_pct in the second array of molok_id

            molok_sections = self.split_fillpcts_to_sections(timestamp_array=x_array, fillpcts_array=y_array)

            # lin req her
            sections = len(molok_sections)
            sections_list = []

            for section in range(sections):

                x = molok_sections[section][0] / 60 # array of timestamps. Making delta time in minutes
                y = molok_sections[section][1] # array of fillpcts
                # reg on form y = ax + b
                a, b, r, p, std_err = stats.linregress(x, y)

                # first and last timestamp of each section
                t0 = x[0] + float(first_timestamp)/60 # adding first timestamp as it was subtracted before
                t1 = x[-1] + float(first_timestamp)/60

                data = (a, b, t0, t1) # a = pcts/minute, b = pcts, t0 = minutes, t1 = minutes
                sections_list.append(data)

            growthrates_dict[molok_id] = np.array(sections_list)

        return growthrates_dict


    def get_sigfox_data(self, id: int, epoch):
        """Get msgs from sigfox network for device with id 0 or 1 that were recieved after 'epoch' epoch time
        by the network"""

        epoch = str((int(epoch) + 1) * 1000) # Do not include specified 'epoch'. Only msgs after (AKA > epoch)
        # * 1000 as sigfox needs time in ms

        authentication = ("643d0041e0b8bb55976d44fe", "ca70a8def999c45aaf1a3fd5a56f2f58") #Credentials

        if id == 0: sigID = "1D3711"
        if id == 1: sigID = "1D3712"

        url = f"https://api.sigfox.com/v2/devices/{sigID}/messages?limit={10}&since={epoch}"
        
        req_result = requests.get(url=url, auth=authentication)

        api_JSON = json.loads(req_result.text)

        # sort response
        messages = []
        for message in api_JSON["data"]:
            time = str(message["time"])[:-3]
            data = bytes.fromhex(message["data"]).decode()
            
            messages.append((sigID, time, data))
        
        return messages[::-1] # msgs originally LIFO. flipping list to be FIFO

    def calc_fillpcts_from_MD(self, distance, molok_depth):
        """Calculates the fillpct from a measuring device based on measured distance and molok depth"""
        pass

    def log_sigfox_to_DB(self, positions):
        """Log information from MD's to DB"""
        pass


    def handshake(self, sendFreq):
        """
        Internal method. Do not call manually! \n
        Contacts sim by sending required data to it, comparing hashes and sending proceed if acceptable. Uses our protocol called C22-SIM Protocol \n
        If succesfull, calls simDBLogger, if not then tells sim to abort
        """
        # --- DB vars ---
        self.simCon = lite.connect(self.DB_NAME) # creates connection to DB from sim thread
        self.simCur = self.simCon.cursor() # creates cursor for sim thread
        
        # creates list of fillPcts to send to sim and creates list of latest timestamps by molokID
        lastFillpctList = []
        latest_timestamps = []
        lastRowList = self.fetchLatestRows(self.table_name, "sim")
        for i in lastRowList:
            fillpct = float(i[3])
            timestamp = float(i[4])
            lastFillpctList.append(fillpct)
            latest_timestamps.append(timestamp)
        
        # creates message with nescessary data for sim. The list is pickled for easy use on sim-side.
        sendsPrDay = sendFreq
        initData = [self.seed, lastFillpctList, sendsPrDay, latest_timestamps]
        print(f"First message of protocol: {initData}")
        initDataPickle = pickle.dumps(initData)

        print(initDataPickle)

        # sending message to sim with socket.send. Lookup use of socket.connect and socket.send if in doubt
        self.socket.send(initDataPickle) # using socket.recv() from now on will return messages from simADDR.
        # using socket.recv() from now on will return messages from simADDR.
        print("Sent first message.")
    
        # hashing msg to compare to answer from sim. Sim hashes msg and sends it back to datastorage for validation.
        hash_value = hashlib.md5(str(initData).encode()).hexdigest() # hash cannot handle a list!
        print(f"hash of first msg as a string: {hash_value}")

        # recieving hash from sim
        hash_request = self.socket.recv(self.BUFFER_SIZE)
        hash_request = hash_request.decode()
        print(f"recieved hash request: {hash_request}")

        # confirming that sim got correct information by comparing hashes
        if hash_value == hash_request:
            print("proceed sent")
            self.socket.send("proceed".encode('utf-8'))
            # handshake done. writeToDB() handles the rest of the protocol.
            self.simDBLogger()
        else:
            print("failed")
            self.socket.send("failed".encode('utf-8'))
    
    def simDBLogger(self):
        """
        Internal method. Do not call manually! \n 
        logs data from sim into DB. This is the second part of our protocol called C22-SIM Protocol"""
        self.socket.settimeout(10) # socket now has n second to receive information before raising an error and ending the thread as intended

        try:
            while True: # loop until self.END_MSG is received or socket times out

                msg = self.socket.recv(self.BUFFER_SIZE) # socket.recvfrom() also returns senders ADDR.
                msg = pickle.loads(msg)

                if msg == self.END_MSG: # when simulation is done
                    print(f"'end' has been sent by simulation. Breaking out of loop and ending thread")
                    break

                print(f"recieved msg: {msg}")

                molokId = int(msg[0]) # part2
                fillPct = float(msg[1]) # part2
                timestamp = float(msg[2]) # part2
                
                # finding molok pos with molok ID
                self.simCur.execute(f"SELECT molokPos FROM '{self.table_name}' WHERE molokID = '{molokId}'")
                molokPos = self.simCur.fetchone() # Getting molokPos. Returns None if empty
                try: molokPos = molokPos[0] # molokPos is either None or ((),) , so this tries to get the inner tuple
                except Exception as e:
                    pass


                # writing sim msg to DB
                self.simCur.execute(f"INSERT INTO {self.table_name} (molokId, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (molokId, str(molokPos), fillPct, timestamp))
                self.simCon.commit()

        except Exception as e:
            print(f"The following error occured in simDBLogger: {e}")
            print("The thread will now be terminated")
            self.socket.settimeout(None) # now the socket will block forever, as by default. When thread runs again, timeout is set to n above

    
    def startSim(self, sendFreq: int = 3) -> bool:
        """Uses our protocol called C22-SIM Protocol to contact simulation and handle its responses in a thread. 
        
        Input
        ---
        sendFreq: int - determines how many times each simulated measuring device should report its fillPct in the simulation of a single day

        Output
        ---
        True: bool - if thread started succesfully \n
        False: bool - if thread already running"""

        # creating and starting sim thread if simThread does not yet exist
        activeThreads = threading.enumerate()
        if not self.sim_thread in activeThreads:
            print("starting thread as there was no self.simThread")
            self.sim_thread = threading.Thread(target=self.handshake, args=[sendFreq], name='writeToDBThread')
            self.sim_thread.start()

            return True # meaning thread started succesfully

        else: return False # meaning thread already running


if __name__ == "__main__":
    
    def testOfSimThread(DS: DataStorage, sendFreq = 1):
        """Run this func to test DS. Must be run with simulation
        Check that all communication occurs correctly and remember that the first sent msg is a pickle."""

        while True:
            print(DS.startSim(sendFreq=sendFreq))
            time.sleep(10)
            print(myDS.showTableByName(myDS.table_name))
            time.sleep(10)
   

    myDS = DataStorage(20, 2, ADDR='sigfox')

    print(myDS.get_sigfox_data(0, time.time()-100000))
   
    print(myDS.showTableByName(myDS.table_name))

    # regg_dict = myDS.lin_regg_sections()
    # print(regg_dict)

    # testOfSimThread(myDS)


    """Outcomment if you want to test"""
    # print(f"showing all table names in DB: {myDS.getTableNames()}")

    # print(f"{myDS.TableName} exists in DB: {myDS.TableName in myDS.getTableNames()}")

    # print(f" showing table {myDS.TableName}: \n {myDS.showTableByName(myDS.TableName)}")

    # print(f" Dropping table {'seed69_NumM5'}: {myDS.dropTable('seed69_NumM5')}")

    # print(myDS.getTableNames())

    # print(myDS.showColumnNamesByTableName(myDS.TableName))

    # print(type(myDS.fetchDataByMolokId(myDS.TableName, 2)[0][4]))

    # print(myDS.fetchColumn(myDS.TableName, 'fillPct'))

    # print(myDS.fetchLatestRows(myDS.TableName, "main"))

    # print(myDS.contactSim())   
