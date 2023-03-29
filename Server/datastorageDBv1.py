import socket
import sqlite3 as lite
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
        self.con = lite.connect(self.DB_NAME)
        self.cur = self.con.cursor()

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
        self.cur.execute("SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        return [i[0] for i in list(self.cur)]

    def createTable(self, tableName):
        """creates new table in DB with tableName"""
        self.cur.execute(f"CREATE TABLE {tableName}(molokID INT, molokPos TUPLE, fillPct INT, timestamp INT)")
        return True

    def showTableByName(self, TableName):
        """shows Table with TableName from DB"""
        self.cur.execute(f"SELECT * FROM '{TableName}'")

        return np.array(list(self.cur))
    
    def dropTable(self, tableName):
        """
        EXTREME DANGER!!!!!
        ---
        This method deletes a table by TableName FOREVER!
        """
        # check if tableName is in DB:
        self.cur.execute(f"DROP TABLE IF EXISTS '{tableName}'")
        return f"You just deleted table {tableName} if it even existed"

    
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
    
    molok_Ids = [0, 1, 2, 3, 4]
    molok_pos = [(22, 10), (67, 24), (76, 54), (80, 100), (10, 10)]

    myDS = DataStorage(69, molok_Ids, molok_pos)

    print(f"showing all tables in DB: {myDS.getTableNames()}")

    print(f"{myDS.TableName} exists in DB: {myDS.TableName in myDS.getTableNames()}")

    print(f" showing table {myDS.TableName}: {myDS.showTableByName(myDS.TableName)}")

    print(f" Dropping table {'seed69_NumM5'}: {myDS.dropTable('seed69_NumM5')}")

    print(myDS.getTableNames())
