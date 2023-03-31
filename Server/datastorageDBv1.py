import socket
import sqlite3 as lite
import numpy as np
import time
import threading

class DataStorage:
    """
    Handles data from sigfox or simulation.

    Logs data in pd.dataframe

    Stores data in CSV as "cold storage" - works!

    Loads CSV if simulation continues at later time - works!

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

    def getTableNames(self):
        """returns table names from DB"""
        self.mainCur.execute("SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        return [i[0] for i in list(self.mainCur)]

    def createTable(self, tableName):
        """creates new table in DB with tableName"""
        self.mainCur.execute(f"CREATE TABLE {tableName}(molokID INT, molokPos TUPLE, fillPct REAL, timestamp REAL)")
        return True

    def showTableByName(self, TableName):
        """shows Table with TableName from DB"""
        self.mainCur.execute(f"SELECT * FROM '{TableName}'")

        return np.array(list(self.mainCur))
    
    def dropTable(self, tableName):
        """
        EXTREME DANGER!!!!!
        ---
        This method deletes a table by TableName FOREVER!
        """
        # check if tableName is in DB:
        self.mainCur.execute(f"DROP TABLE IF EXISTS '{tableName}'")
        return f"You just deleted table {tableName} if it even existed"

    def handleSim(self):
        """Called by handleSimThread(). Handles comms with sim"""

        # creating and starting sim thread
        self.simThread = threading.Thread(target=self.writeToDB, args=["sim"])
        self.simThread.start()

    def handleSigfox(self):
        """handles comms with sigfox. Only call if using measuring devices"""
        pass

    def writeToDB(self, cursor: str):
        """logs data from comms handling functions 'handleSigfox' or 'handleSim' into DB"""
        if cursor == "sim":
            # --- DB vars ---
            self.simCon = lite.connect(self.DB_NAME) # creates connection to DB from sim thread
            self.simCur = self.simCon.cursor() # creates cursor for sim thread
            
            while True:
                msg, clientADDR = self.socket.recvfrom(self.BUFFER_SIZE) # socket.recvfrom() also returns senders ADDR.
                msg = msg.decode()
                msg = msg.split()
                print(f"recieved msg: {msg} from {clientADDR}")
                
                # splitting msg
                molokId = int(msg[0].strip(")(, ")) # removes chars and changes to int
                fillPct = float(msg[1].strip(")(, "))
                timestamp = float(msg[2].strip(")(, "))
                
                # finding molok pos with molok ID
                self.simCur.execute(f"SELECT molokPos FROM '{self.TableName}' WHERE molokID = '{molokId}'")
                molokPos = tuple(self.simCur)

                # writing sim msg to DB
                self.simCur.execute(f"INSERT INTO '{self.TableName}' VALUES ('{molokId}', '{molokPos}', '{fillPct}', '{timestamp}')")
                self.simCon.commit()


if __name__ == "__main__":
    
    molok_Ids = [0, 1, 2, 3, 4]
    molok_pos = [(22, 10), (67, 24), (76, 54), (80, 100), (10, 10)]

    myDS = DataStorage(69, molok_Ids, molok_pos, ADDR=('192.168.137.1', 9999))

    # print(f"showing all tables in DB: {myDS.getTableNames()}")

    # print(f"{myDS.TableName} exists in DB: {myDS.TableName in myDS.getTableNames()}")

    print(f" showing table {myDS.TableName}: {myDS.showTableByName(myDS.TableName)}")

    # print(f" Dropping table {'seed69_NumM5'}: {myDS.dropTable('seed69_NumM5')}")

    # print(myDS.getTableNames())

    # myDS.handleSim()

    for i in range(5):
        time.sleep(10)
        print(f" showing table {myDS.TableName}: {myDS.showTableByName(myDS.TableName)}")
