import socket
import sqlite3 as lite
import numpy as np
import time
import threading


class DataStorage:
    """
    Handles data from sigfox or simulation.
    Logs data in DB
    Manipulates data and presents it to 'Route Planner' or 'GUI'
    """

    def __init__(self, seed: any, molok_Ids = [], molok_positions = [], ADDR = ('127.0.0.1', 9999)) -> None:
        """
        There are two different ways to initialize DataStorages comms
        1. with ADDR = '(IP, PORT)' -> creates server socket for communication with simulation
        ADDR must be server address.
        2. with ADDR = "sigfox" -> creates client socket/ comm link with sigfox

        There are two different ways to use the DB
        1. with TABLE_NAME as "" (empty string) -> creates new TABLE in DB based on config vars
        2. with TABLE_NAME as "XYZ" (actual name) -> opens TABLE in DB with TABLE_NAME
        """

        if len(molok_Ids) != len(molok_positions):
            print(f"length of molokIds ({len(molok_Ids)}) is NOT equal to length of molok_positions ({len(molok_positions)}). They must be equal")
            exit()

        # --- config vars ---
        self.DB_NAME = "Server\MolokData.db" # fix stien senere
        self.mainCon = lite.connect(self.DB_NAME) # creates connection to DB from main thread
        self.mainCur = self.mainCon.cursor() # creates cursor for main thread

        self.seed = seed
        self.rng = np.random.default_rng(seed=seed) # creates a np.random generator-object with specified seed. Use self.rng for randomness
        self.molokIds = molok_Ids
        self.molokPos = molok_positions
        self.numMoloks = len(self.molokIds)

        self.TableName = f"seed{self.seed}_NumM{self.numMoloks}"

        # create new table if TableName not in DBTables
        if not self.TableName in self.getTableNames():
            self.createTable(self.TableName)

        # --- socket vars ---
        if type(ADDR) == tuple: # checks that user wants to create socket for UDP comms with simulation
            self.simADDR = ADDR
            self.BUFFER_SIZE = 1024
            self.END_MSG = "end"
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP

            self.allowSim = threading.Event() # Creating flag for simulation control
            self.allowSim.set() # allowSim = True

            self.socketLock = threading.Lock()

            # self.socket.connect(self.simADDR) # connecting to simulation address
            self.socket.bind(self.simADDR)

            self.simThread = None # creating simThread variable
            

            print('Provided ADDR indicates simulation is to be run. UDP client running...')
            # print(f'Listening for incoming messages on address '+str(self.simADDR))
        
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
    
    def fetchLatestRows(self, TableName):
        """returns array containing a row for each molokId with its latest ID"""
        self.mainCur.execute(f"SELECT MAX(ID), molokID, molokPos, fillPct, timestamp FROM '{TableName}' GROUP BY molokID")
        
        return np.array(self.mainCur.fetchall())

    def dropTable(self, tableName):
        """
        EXTREME DANGER!!!!!
        ---
        This method deletes a table by TableName FOREVER!
        """
        # check if tableName is in DB:
        self.mainCur.execute(f"DROP TABLE IF EXISTS '{tableName}'")
        return f"You just deleted table {tableName} if it even existed"

    def contactSim(self) -> bool:
        """
        Tells simulation to start using our self made protocol called C22-SIM Protocol. return True if it succeeded, False if not
        
        """
        
        with self.socketLock: # auto acquires lock and releases it when done
            # This is done to ensure that the two threads do not mess with the protocols communication by "stealing" msg from oneanother

            if self.allowSim.is_set(): # If allowSim == True
                
                # creates list of fillPcts to send to sim
                lastFillpctList = []
                lastRowList = self.fetchLatestRows(self.TableName)
                for i in lastRowList:
                    fillpct = i[3]
                    lastFillpctList.append(fillpct)
                
                # creates message with nescessary data for sim
                sendsPrDay = 2
                first_msg = f"{[self.seed, self.numMoloks, lastFillpctList, sendsPrDay]}"
                print(f"First message of protocol: {first_msg}")

                # sending message to sim with socket.send. Lookup use of socket.connect and socket.send if in doubt
                self.socket.send(first_msg.encode('utf-8')) # using socket.recv() from now on will return messages from simADDR.
                # using socket.recv() from now on will return messages from simADDR.
                print("Sent first message.")
            else:
                print("allowSim == False; wait for current simulation to stop to start a new one!")
            
            # hashing msg to compare to answer from sim. Sim hashes msg and sends it back to datastorage for validation.
            hash_value = hash(first_msg)
            print(f"hash of first msg: {hash_value}")
            
            # recieving hash from sim
            hash_request = self.socket.recv(self.BUFFER_SIZE)
            hash_request = hash_request.decode()
            print(f"recieved hash request: {hash_request}")

            # confirming that sim got correct information by comparing hashes
            if hash_value == hash_request:
                self.socket.send("proceed".encode('utf-8'))
                # handshake done, clearing allowSim-flag (setting to False). handleSim() handles the rest of the protocol.
                self.allowSim.clear()
                self.handleSim()
                return True
            else: 
                self.socket.send("hash failed".encode('utf-8'))
                return False


    def handleSim(self):
        """Handles comms with simulation in a thread"""

        # creating and starting sim thread if simThread does not yet exist
        activeThreads = threading.enumerate()
        if not self.simThread in activeThreads:
            print("starting thread as there was no self.simThread")
            self.simThread = threading.Thread(target=self.writeToDB, args=["sim", self.socketLock], name='writeToDBThread')
            self.simThread.start()
        
        else: print("Thread is already active")

    def handleSigfox(self):
        """handles comms with sigfox. Only call if using measuring devices"""
        pass

    def writeToDB(self, cursor: str, lock):
        """logs data from comms handling functions 'handleSigfox' or 'handleSim' into DB"""
        if cursor == "sim":
            # --- DB vars ---
            self.simCon = lite.connect(self.DB_NAME) # creates connection to DB from sim thread
            self.simCur = self.simCon.cursor() # creates cursor for sim thread

            while True:

                with lock: # auto acquires lock and releases it when the threads iteration of while True is done with the socket
                    msg = self.socket.recv(self.BUFFER_SIZE) # socket.recvfrom() also returns senders ADDR.
                    msg = msg.decode()

                    if msg == self.END_MSG: # when simulation is done
                        self.socket.send("acknowledge end".encode("utf-8"))
                        print(f"'acknowledge end' has been sent to simulation")
                        self.allowSim.set() # sets flag to True, so that contactSim() can be run again

                # from hereon the socketLock is released so that the socket may be used elsewhere
                msg = msg.split()
                print(f"recieved msg: {msg}")

                # splitting msg
                molokId = int(msg[0].strip(")(, ")) # removes chars and changes to int
                fillPct = float(msg[1].strip(")(, "))
                timestamp = float(msg[2].strip(")(, "))
                
                # finding molok pos with molok ID
                self.simCur.execute(f"SELECT molokPos FROM '{self.TableName}' WHERE molokID = '{molokId}'")
                molokPos = self.simCur.fetchone() # Getting molokPos. Returns None if empty
                try: molokPos = molokPos[0] # molokPos is either None or ((),) , so this tries to get the inner tuple
                except Exception as e:
                    pass

                if molokPos == None:
                    # print(f"molokpos empty. Inserting from self.molokPos[molokId]")
                    molokPos = self.molokPos[molokId]

                # writing sim msg to DB
                self.simCur.execute(f"INSERT INTO {self.TableName} (molokId, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (molokId, str(molokPos), fillPct, timestamp))
                self.simCon.commit()


if __name__ == "__main__":
    
    molok_Ids = [0, 1, 2, 3, 4]
    molok_pos = [(22, 10), (67, 24), (76, 54), (80, 100), (10, 10)]

    myDS = DataStorage(69, molok_Ids, molok_pos)




    """Outcomment if you want to test"""
    # print(f"showing all table names in DB: {myDS.getTableNames()}")

    # print(f"{myDS.TableName} exists in DB: {myDS.TableName in myDS.getTableNames()}")

    print(f" showing table {myDS.TableName}: \n {myDS.showTableByName(myDS.TableName)}")

    # print(f" Dropping table {'seed69_NumM5'}: {myDS.dropTable('seed69_NumM5')}")

    # print(myDS.getTableNames())

    # print(myDS.showColumnNamesByTableName(myDS.TableName))

    # print(type(myDS.fetchDataByMolokId(myDS.TableName, 2)[0][4]))

    # print(myDS.fetchColumn(myDS.TableName, 'fillPct'))

    # print(myDS.fetchLatestRows(myDS.TableName))

    # print(myDS.contactSim())

    myDS.handleSim()

    # for i in range(5):
    #     time.sleep(6)
    #     print(f" showing table {myDS.TableName}: \n {myDS.showTableByName(myDS.TableName)}")
