import socket
import sqlite3 as lite
import numpy as np
import time
import threading
import pickle
from scipy import stats
import requests
import json
# from Algorithm.routePlanner import routePlanner as rP
from routePlanner import RoutePlanner
import support_functions as sf



class DataStorage:
    """
    Handles data from sigfox or simulation.
    Logs data in DB
    Manipulates data and presents it to 'Route Planner' or 'GUI'
    """

    def __init__(self, seed: any, num_moloks: int, center_coordinates = (57.01466, 9.987159), scale = 0.01 , ADDR = ('127.0.0.1', 12445)) -> None:
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
            self.END_MSG = "stop"
            self.UDP_recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP

            self.UDP_recv_socket.bind(("", self.sim_ADDR[1])) # UDP server sock for receiving from sim

            # IPAddr=socket.gethostbyname(socket.gethostname())
            # print(f"My IP is : {IPAddr}")

            self.sim_thread = None # creating simThread variable
            
            print('Provided ADDR indicates simulation is to be run. UDP client ready...')
        
        # --- sigfox vars ---
        elif ADDR == "sigfox":
            self.table_name = f"sigfox_seed{self.seed}_NumM{self.num_moloks}"
            self.md_positions = self.generate_MD_positions(self.num_moloks)
            print(f"""Generated positions for moloks/measuring devices: {self.md_positions}. If you wish to override these
            positions, change the 'md_positions' attribute manually""")

            print("Call 'get_sigfox_data()' to get sigfox data from the implemented measuring device")

        # create new table if TableName not in DBTables
        if not self.table_name in self.get_tablenames():
            print(f"{self.table_name} not found in table names. Creating it now")
            self.create_table(self.table_name)


    def get_tablenames(self):
        """returns table names from DB"""
        self.main_cur.execute("SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        return [i[0] for i in list(self.main_cur)]

    def create_table(self, table_name):
        """creates new table in DB with tableName"""
        self.main_cur.execute(f"CREATE TABLE {table_name}(ID INTEGER PRIMARY KEY, molokID INTEGER, molokPos TUPLE, fillPct REAL, timestamp REAL)")
        if table_name[:3] == "sim": # only auto generate data if simulations are to be run
            self.generate_init_data(table_name)
        return True

    def show_table_by_tablename(self, table_name):
        """shows Table with TableName from DB"""
        self.main_cur.execute(f"SELECT * FROM '{table_name}'")

        return np.array(list(self.main_cur))
    
    def show_column_names_by_tablename(self, table_name):
        """Shows columns of specified table with TableName"""
        self.main_cur.execute(f"PRAGMA table_info('{table_name}')")

        return np.array(self.main_cur.fetchall())

    def fetch_data_by_molok_ID(self,table_name, Id):
        """Returns all rows with specified Id"""
        self.main_cur.execute(f"SELECT * FROM '{table_name}' WHERE molokID = '{Id}'")

        return np.array(self.main_cur.fetchall()) 
    
    # felt cute, might delete later
    def fetch_column(self, table_name, column_name):
        """Returns a specified column as a Numpy array"""
        self.main_cur.execute(f"SELECT {column_name} FROM '{table_name}'")

        return np.array(self.main_cur.fetchall())
    
    def fetch_latest_rows(self, table_name, cursor: str):
        """returns array containing a row for each molokId with its latest ID"""
        if cursor == "main":
            self.main_cur.execute(f"SELECT MAX(ID), molokID, molokPos, fillPct, timestamp FROM '{table_name}' GROUP BY molokID")
            return np.array(self.main_cur.fetchall())
        elif cursor == "sim":
            self.sim_cur.execute(f"SELECT MAX(ID), molokID, molokPos, fillPct, timestamp FROM '{table_name}' GROUP BY molokID")
            return np.array(self.sim_cur.fetchall())

    def drop_table(self, table_name):
        """
        EXTREME DANGER!!!!!
        ---
        This method deletes a table by TableName FOREVER!
        """
        # check if tableName is in DB:
        self.main_cur.execute(f"DROP TABLE IF EXISTS '{table_name}'")
        return f"You just deleted table {table_name} if it even existed"

    def generate_init_data(self, table_name):
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
            self.main_cur.execute(f"INSERT INTO {table_name}(molokID, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (i, str(molok_coords[i]), init_fill_pcts[i], timestamp))
        self.main_con.commit()

        return True

    def split_fillpcts_to_sections(self, fillpcts_array, timestamp_array, msg_ID_array):
        """split filpcts and their timestamps into sections to account for emptying moloks"""

        sections_dict = {}
        section = 0
        first_index = 0

        for cur_index in range(1, len(fillpcts_array)):
            
            # putting fillpcts from 0-100 into sections_dict by a first and current index
            if fillpcts_array[cur_index] == 0: # split into sections when molok has been emptied
                timestamp_section = timestamp_array[first_index:cur_index]
                fillpcts_section = fillpcts_array[first_index:cur_index]
                msg_ID_section = msg_ID_array[first_index:cur_index]
                sections_dict[section] = np.vstack((timestamp_section, fillpcts_section, msg_ID_section))
                
                section += 1
                first_index = cur_index
            
            # putting last section into dict
            elif cur_index == len(fillpcts_array) - 1:
                timestamp_section = timestamp_array[first_index:]
                fillpcts_section = fillpcts_array[first_index:]
                msg_ID_section = msg_ID_array[first_index:]
                sections_dict[section] = np.vstack((timestamp_section, fillpcts_section, msg_ID_section))
                
        return sections_dict

    def lin_reg_sections(self):
        """
        find all sections for each molok and do linear reggresion on each section. A section is between each emptying
        returns a dictionary that contains info on form (a = pcts/second, b = pcts, t0 = seconds, t1 = seconds, msg_IDs)
        """

        growthrates_dict = {}

        for molok_id in range(self.num_moloks):
            molok_data = self.fetch_data_by_molok_ID(self.table_name, molok_id)
            
            first_timestamp = molok_data[0][4] # epoch time

            x_array = np.zeros(len(molok_data))
            y_array = np.zeros(len(molok_data))

            msg_ID_array = np.zeros(len(molok_data)) # adding msg_IDs to know which rows in DB are used


            for row_index in range(len(molok_data)):
                timestamp = molok_data[row_index][4] # x-axis for lin. reg. model.
                fill_pct = molok_data[row_index][3] # y-axis
                msg_ID = molok_data[row_index][0] # msg ID
                                
                # subtracting by first timestamp to make graphing since time = 0 on x-axis
                timestamp = float(timestamp) - float(first_timestamp)

                x_array[row_index] = timestamp # putting timestamps in the first array of molok_id
                y_array[row_index] = fill_pct # putting fill_pct in the second array of molok_id
                msg_ID_array[row_index] = msg_ID

            molok_sections = self.split_fillpcts_to_sections(timestamp_array=x_array, fillpcts_array=y_array, msg_ID_array=msg_ID_array)

            # lin req her
            sections = len(molok_sections)
            sections_list = []

            for section in range(sections):

                x = molok_sections[section][0] # array of timestamps
                y = molok_sections[section][1] # array of fillpcts
                # reg on form y = ax + b
                a, b, r, p, std_err = stats.linregress(x, y)

                msg_IDs = molok_sections[section][2] # looking up relevant IDs

                # first and last timestamp of each section
                t0 = x[0] + float(first_timestamp) # adding first timestamp as it was subtracted before
                t1 = x[-1] + float(first_timestamp)

                data = (a, b, t0, t1, msg_IDs) # a = pcts/second, b = pcts, t0 = seconds, t1 = seconds
                sections_list.append(data)

            growthrates_dict[molok_id] = sections_list

        return growthrates_dict

    def avg_growth_over_period(self, regression_dictionary: dict, period_start: float = (time.time() - 86400 * 7), period_end: float = time.time()):
        """
        calculate avg growth in fill pcts over time in the passed 'regression_dictionary'.
        """
        avg_growthrates = np.zeros(len(regression_dictionary))

        for key in regression_dictionary:
            molok_periods = regression_dictionary[key]

            num_valid_periods = 0
            sum_period_growthrates = 0

            for period in molok_periods:
                
                section_start = period[2]
                section_end = period[3]

                if section_start < period_end and period_start < section_end:
                    
                    num_valid_periods += 1 # increase num of valid periods
                    sum_period_growthrates += period[0] # increase sum of a's by valid periods a

            if num_valid_periods == 0:
                return f"No valid sections found for period {period_start} to {period_end}"
            
            # finding avg. growthrate of sections that are part of specified period
            molok_avg_growthrate = sum_period_growthrates / num_valid_periods
            avg_growthrates[key] = molok_avg_growthrate

        return avg_growthrates

    def set_fillpcts_to_0(self, routePlanner_data, route_start_time):
        """
        From routeplanner, when moloks are emptied from routes,
        this function sets the filling procentage to 0 by updating the latest rows in the database. 
        """
        
        for molok in routePlanner_data:
            molok_id = molok[0]
            timestamp = molok[1] + route_start_time
            self.main_cur.execute(f"SELECT molokPos FROM '{self.table_name}' WHERE molokID = '{molok_id}'")
            molokPos = self.main_cur.fetchone() # Getting molokPos. Returns None if empty
            try: molokPos = molokPos[0] # molokPos is either None or ((),) , so this tries to get the inner tuple
            except Exception as e:
                pass

            # writing sim msg to DB
            self.main_cur.execute(f"INSERT INTO {self.table_name} (molokId, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (molok_id, str(molokPos), 0, timestamp))
            self.main_con.commit()
            




    def calc_fillpcts_from_MD(self, distance, molok_depth) -> float:
        """Calculates the fillpct from a measuring device based on measured distance and molok depth (both in cm)"""
        # the pct-wise distance from sensor to garbage. subtract from 100% to get garbage pct
        measured_pct = distance / molok_depth
        fillpct = 100 * (1 - measured_pct) # * 100 to convert from decimal to pct.

        return fillpct
    
    def generate_MD_positions(self, num_devices):
        """Generates measuring device positions for 'log_sigfox_to_DB' to use. This method can be used if no positions exist
        yet or if you want random positions instead of user-defined ones"""

        norm_dist_lat = self.rng.normal(self.center_coords[0], self.scale/2, size = num_devices)
        norm_dist_long = self.rng.normal(self.center_coords[1], self.scale, size = num_devices)
        md_positions = np.array(list(zip(norm_dist_lat, norm_dist_long)))

        return md_positions


    def get_sigfox_data(self, epoch):
        """Get msgs from sigfox network for the measuring device that were recieved after 'epoch' epoch time
        by the network"""

        epoch = str((int(epoch) + 1) * 1000) # Do not include specified 'epoch'. Only msgs after (AKA > epoch)
        # * 1000 as sigfox needs time in ms

        authentication = ("643d0041e0b8bb55976d44fe", "ca70a8def999c45aaf1a3fd5a56f2f58") #Credentials

        sigID = "1D3711"

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

    def log_sigfox_to_DB(self, epoch: int = 1681720002):
        """Log information from MD's to DB"""
        
        # if multiple MDs were implemented, this var could be dynamic instead of hardcoded, but we only use the one
        meas_device_id = 0

        md_msgs = self.get_sigfox_data(epoch=epoch)

        device_pos = self.md_positions[meas_device_id]

        for msg in md_msgs:

            # calc fill_pct
            meas_distance_str = str(msg[2])
            meas_dist = float(meas_distance_str.split(':')[0])
            fill_pct = self.calc_fillpcts_from_MD(meas_dist, molok_depth=200)

            # isolate timestamp
            timestamp = float(msg[1])

            self.main_cur.execute(f"INSERT INTO {self.table_name} (molokId, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (meas_device_id, str(device_pos), fill_pct, timestamp))
            self.main_con.commit()


    def handshake(self, send_freq):
        """
        Internal method. Do not call manually! \n
        Contacts sim by sending required data to it, comparing hashes and sending proceed if acceptable. Uses our protocol called C22-SIM Protocol \n
        If succesfull, calls simDBLogger, if not then tells sim to abort
        """
        # --- DB vars ---
        self.sim_con = lite.connect(self.DB_NAME) # creates connection to DB from sim thread
        self.sim_cur = self.sim_con.cursor() # creates cursor for sim thread

        # --- socket var ---
        try:
            self.TCP_handshake_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IPv4, TCP
            self.TCP_handshake_socket.connect(self.sim_ADDR) # client sock to send init data to sim

        except TimeoutError as e:
            print(f"TimeoutError: {e}")
            print("Closing sim thread")
            return False

        # If routePlanner has emptied moloks then call set_fillpcts_to_0
        # if RoutePlanner.get_molok_empty_timestamps() == True:
        #    self.set_fillpcts_to_0() 



        # creates list of fillPcts to send to sim and creates list of latest timestamps by molokID
        last_fillpct_list = []
        latest_timestamps = []
        last_row_list = self.fetch_latest_rows(self.table_name, "sim")
        for i in last_row_list:
            fillpct = float(i[3])
            timestamp = float(i[4])
            last_fillpct_list.append(fillpct)
            latest_timestamps.append(timestamp)
        
        # creates message with nescessary data for sim. The list is pickled for easy use on sim-side.
        sends_pr_day = send_freq
        init_data = [self.seed, last_fillpct_list, sends_pr_day, latest_timestamps]
        # print(f"First message of protocol: {init_data}")
        init_data_pickle = pickle.dumps(init_data)

        # sending message to sim with socket.send. Lookup use of socket.connect and socket.send if in doubt
        bytes_sent = self.TCP_handshake_socket.send(init_data_pickle + self.END_MSG.encode())
        print(f"sent {bytes_sent} bytes to sim in init data")

        self.simDBLogger()

        return True
    
    def simDBLogger(self):
        """
        Internal method. Do not call manually! \n 
        logs data from sim into DB. This is the second part of our protocol called C22-SIM Protocol"""
        self.UDP_recv_socket.settimeout(20) # socket now has n second to receive information before raising an error and ending the thread as intended
        msg_counter = 0

        try:
            while True: # loop until self.END_MSG is received or socket times out
                
                time.sleep(0.05)
                msg = self.UDP_recv_socket.recv(self.BUFFER_SIZE)
                msg = pickle.loads(msg)                
                
                if msg == self.END_MSG: # when simulation is done
                    print(f"END_MSG has been sent by simulation. Breaking out of loop and ending thread")
                    break
                
                # print(f"recieved msg: {msg}")

                molokId = int(msg[0])
                fillPct = float(msg[1]) 
                timestamp = float(msg[2]) 

                msg_counter += 1
                
                # finding molok pos with molok ID
                self.sim_cur.execute(f"SELECT molokPos FROM '{self.table_name}' WHERE molokID = '{molokId}'")
                molokPos = self.sim_cur.fetchone() # Getting molokPos. Returns None if empty
                try: molokPos = molokPos[0] # molokPos is either None or ((),) , so this tries to get the inner tuple
                except Exception as e:
                    pass

                # writing sim msg to DB
                self.sim_cur.execute(f"INSERT INTO {self.table_name} (molokId, molokPos, fillPct, timestamp) VALUES (?,?,?,?)", (molokId, str(molokPos), fillPct, timestamp))
                self.sim_con.commit()
            
            self.TCP_handshake_socket.close()
            print(f"Comms ended succesfully. Recieved {msg_counter} datapoints")

        except Exception as e:
            print(f"The following error occured in simDBLogger: {e}")
            print("The thread will now be terminated")
            self.UDP_recv_socket.settimeout(None) # now the socket will block forever, as by default. When thread runs again, timeout is set to n above
            self.TCP_handshake_socket.close()

    def startSim(self, send_freq: int = 3) -> bool:
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
            self.sim_thread = threading.Thread(target=self.handshake, args=[send_freq], name='writeToDBThread')
            self.sim_thread.start()

            return True # meaning thread started succesfully

        else: return False # meaning thread already running

    def join_sim_thread(self):
        """Allows GUI to join simthread into another thread. It lets the GUI update the map as soon as the sim thread is done"""

        self.sim_thread.join()


if __name__ == "__main__":
    
    def testOfSimThread(DS: DataStorage, sendFreq = 1):
        """Run this func to test DS. Must be run with simulation
        Check that all communication occurs correctly and remember that the first sent msg is a pickle."""

        while True:
            print(DS.startSim(send_freq=sendFreq))
            time.sleep(3)
            print(myDS.show_table_by_tablename(myDS.table_name))
   

    myDS = DataStorage(69, 1000, ADDR=('192.168.137.234', 12445))


    print(myDS.startSim(send_freq=1))
    print("joining threads")
    starttime = time.time()
    # myDS.join_sim_thread()

    finish_time = time.time()

    print(f"after join. It took {finish_time-starttime} seconds")


    exit()
    
    num_trucks = 2
    ttem = 5                                            # time to empty molok
    num_moloks = 3
    seed = 20
    np.random.seed(seed=seed)

    molok_pos_list_of_lists = sf.normal_distribution(45, 10, 0.1, num_moloks)
    molok_pos_list = []
    for pos in molok_pos_list_of_lists:
        molok_pos_list.append(tuple(pos))

    molok_fillpcts = np.random.normal(70, 7.5, num_moloks)
    avg_grs = np.random.normal(0.05, 0.01, num_moloks)

    depotArgs = [600, 2200, (45, 10)] # 6:00 to 22:00 o'clock and position is (lat, long)
    molokArgs = [molok_pos_list, ttem, molok_fillpcts, 500, avg_grs] # molokCoordinate list, emptying time cost in minutes, fillPct-list, molok capacity in kg, linear growth rates
    truckArgs = [150, num_trucks, 3000, 600, 1400] # range, number of trucks, truck capacity in kg, working from 6:00 to 14:00

    rp = RoutePlanner(depotArgs=depotArgs, molokAgrs=molokArgs, truckAgrs=truckArgs, time_limit=1, first_solution_strategy='3', local_search_strategy='2')
    print(rp.data)

    solution = rp.main()
    print(solution)
    time_const = rp.routing.GetDimensionOrDie(rp.time_windows_constraint)
    visit_times = rp.get_cumul_data(solution, rp.routing, dimension=time_const)
    routes = rp.get_routes(solution, rp.routing, rp.manager)
    emptying_list = rp.get_molok_empty_timestamps(routes, visit_times)
    print(emptying_list)

    # print(myDS.set_fillpcts_to_0(emptying_list, 0))

    # print(myDS.log_sigfox_to_DB())

    print(myDS.show_table_by_tablename(myDS.table_name))

    # reg_dict = myDS.lin_reg_sections()
    # print(reg_dict)

    # avg_a = myDS.avg_growth_over_period(reg_dict, period_start=time.time() - 1000)
    # print(avg_a)
    # print(len(avg_a))

    # testOfSimThread(myDS)
    # data= [[0, 200],[1, 340],[3, 401]]
    # print(myDS.set_fillpcts_to_0(routePlanner_data=data))

    """Outcomment if you want to test"""
    # print(f"showing all table names in DB: {myDS.getTableNames()}")

    # print(f"{myDS.TableName} exists in DB: {myDS.TableName in myDS.getTableNames()}")

    # print(f" showing table {myDS.TableName}: \n {myDS.showTableByName(myDS.TableName)}")

    # print(f" Dropping table {'seed69_NumM5'}: {myDS.dropTable('seed69_NumM5')}")

    # print(myDS.getTableNames())

    # print(myDS.showColumnNamesByTableName(myDS.TableName))

    # print(type(myDS.fetchDataByMolokId(myDS.TableName, 2)[0][4]))

    # print(myDS.fetch_Column(myDS.tableName, 'fillPct'))

    # print(myDS.fetch_latest_rows(myDS.table_name, "main"))

    # print(myDS.contactSim())   
