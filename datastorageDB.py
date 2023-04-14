import socket
import sqlite3 as lite
import numpy as np
import time
import threading
import pickle


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
        self.mainCon = lite.connect(self.DB_NAME) # creates connection to DB from main thread
        self.mainCur = self.mainCon.cursor() # creates cursor for main thread

        self.seed = seed
        self.rng = np.random.default_rng(seed=seed) # creates a np.random generator-object with specified seed. Use self.rng for randomness
        self.num_moloks = num_moloks
        self.center_coords = center_coordinates
        self.scale = scale

        self.TableName = f"seed{self.seed}_NumM{self.num_moloks}"

        # create new table if TableName not in DBTables
        if not self.TableName in self.getTableNames():
            print(f"{self.TableName} not found in table names. Creating it now")
            self.createTable(self.TableName)

        # --- socket vars ---
        if type(ADDR) == tuple: # checks that user wants to create socket for UDP comms with simulation
            self.simADDR = ADDR
            self.BUFFER_SIZE = 1024 * 8
            self.END_MSG = "end"
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP

            # self.socket.connect(self.simADDR) # connecting to simulation address
            self.socket.connect(self.simADDR)

            self.simThread = None # creating simThread variable
            
            print('Provided ADDR indicates simulation is to be run. UDP client ready...')
        
        # --- sigfox vars ---
        else: # if not simulation, then sigfox comms
            """
            Sigfox: når vi ved hvordan det virker
            """
            pass

    def getTableNames(self):
        """returns table names from DB"""
        self.mainCur.execute("SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        return [i[0] for i in list(self.mainCur)]

    def createTable(self, tableName):
        """creates new table in DB with tableName"""
        self.mainCur.execute(f"CREATE TABLE {tableName}(ID INTEGER PRIMARY KEY, molokID INTEGER, molokPos TUPLE, fillPct REAL, timestamp REAL)")
        self.generate_init_data(tableName)
        return True

    def showTableByName(self, TableName):
        """shows Table with TableName from DB"""
        self.mainCur.execute(f"SELECT * FROM '{TableName}'")

        return np.array(list(self.mainCur))
    
    def showColumnNamesByTableName(self, TableName):
        """Shows columns of specified table with TableName"""
        self.mainCur.execute(f"PRAGMA table_info('{TableName}')")

        return np.array(self.mainCur.fetchall())

    def fetchDataByMolokId(self,TableName, Id):
        """Returns all rows with specified Id"""
        self.mainCur.execute(f"SELECT * FROM '{TableName}' WHERE molokID = '{Id}'")

        return np.array(self.mainCur.fetchall()) 
    
    def fetchColumn(self, TableName, ColumnName):
        """Returns a specified column as a Numpy array"""
        self.mainCur.execute(f"SELECT {ColumnName} FROM '{TableName}'")

        return np.array(self.mainCur.fetchall())
    
    def fetchLatestRows(self, TableName, cursor: str):
        """returns array containing a row for each molokId with its latest ID"""
        if cursor == "main":
            self.mainCur.execute(f"SELECT MAX(ID), molokID, molokPos, fillPct, timestamp FROM '{TableName}' GROUP BY molokID")
            return np.array(self.mainCur.fetchall())
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
        self.mainCur.execute(f"DROP TABLE IF EXISTS '{tableName}'")
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
            self.mainCur.execute(f"INSERT INTO {tableName}(molokID, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (i, str(molok_coords[i]), init_fill_pcts[i], timestamp))
        self.mainCon.commit()

        return True

    def handleSigfox(self):
        """handles comms with sigfox. Only call if using measuring devices"""
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
        lastRowList = self.fetchLatestRows(self.TableName, "sim")
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
        hash_value = hash(str(initData)) # hash cannot handle a list!
        print(f"hash of first msg as a string: {hash_value}")

        # recieving hash from sim
        hash_request = self.socket.recv(self.BUFFER_SIZE)
        hash_request = hash_request.decode()
        print(f"recieved hash request: {hash_request}")

        # confirming that sim got correct information by comparing hashes
        if hash_value == hash_request or hash_request == "123": # ---- remove later
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
        self.socket.settimeout(15) # socket now has n second to receive information before raising an error and ending the thread as intended

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
                self.simCur.execute(f"SELECT molokPos FROM '{self.TableName}' WHERE molokID = '{molokId}'")
                molokPos = self.simCur.fetchone() # Getting molokPos. Returns None if empty
                try: molokPos = molokPos[0] # molokPos is either None or ((),) , so this tries to get the inner tuple
                except Exception as e:
                    pass


                # writing sim msg to DB
                self.simCur.execute(f"INSERT INTO {self.TableName} (molokId, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (molokId, str(molokPos), fillPct, timestamp))
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
        if not self.simThread in activeThreads:
            print("starting thread as there was no self.simThread")
            self.simThread = threading.Thread(target=self.handshake, args=[sendFreq], name='writeToDBThread')
            self.simThread.start()

            return True # meaning thread started succesfully

        else: return False # meaning thread already running


if __name__ == "__main__":
    
    def testOfSimThread(DS: DataStorage, sendFreq = 1):
        """Run this func to test DS. Must be run with simulation
        Check that all communication occurs correctly and remember that the first sent msg is a pickle."""

        while True:
            print(DS.startSim(sendFreq=sendFreq))
            time.sleep(10)
            print(myDS.showTableByName(myDS.TableName))
            time.sleep(10)
   

    myDS = DataStorage(20, 10, ADDR=("192.168.137.104", 12345))
   

    # print(myDS.showTableByName(myDS.TableName))

    testOfSimThread(myDS)


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

