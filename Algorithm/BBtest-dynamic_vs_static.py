"""
This document consists of the following:
 - Logic to find static routes
    - save routes in dict as pickle for later use (save inputs as well)
    - cover all 1000 moloks

 - test unit for comparing results
    - run day by day AFTER static routes have been created
    - showcase KPI comparison
    - showcase overfill

# pseudocode for finding static routes

unemptied moloks = [] # list of all molok id's

while len(unemptied_moloks) > 0:

    sim 1 day

    check if emptying is needed

    empty moloks

    save routes

    remove emptied moloks from list unemptied_moloks

present routes in dict with cycle-day as key (1-14 maybe. Depends on last day of emptying)

"""

import numpy as np
import time
import pickle

import support_functions as sf
import routePlanner
from datastorage import DataStorage



class StaticRoutes:

    def __init__(self, seed, num_moloks) -> None:
        self.unemptied_moloks = []
        self.routes_dict = {}

        self.day_num = 1
        self.seed = seed
        self.num_moloks = num_moloks

        self.unemptied_moloks = list(range(num_moloks))
        self.datastorage = DataStorage()
        tablename = self.datastorage.create_table(self.seed, self.num_moloks, 'sim')
        self.datastorage.select_table(tablename, self.seed, self.num_moloks)
    
    def make_master_planner(self, moloks_to_empty):

        time_limit = 5             # seconds

        depot_open = 600            # hhmm time
        depot_close = 2200          # hhmm time
        depot_pos = (57.014, 9.98)  # decimal degrees coords

        ttem = 5                # time to empty molok
        molok_capacity = 200    # kg
        molok_pos_list = []     
        molok_fillpcts = []
        avg_grs = []

        for molok in moloks_to_empty:
            molok_id = molok[0]
            molok_pos = molok[1]
            molok_fillpct = molok[2]
            molok_growthrate = molok[3]

            molok_pos_list.append(molok_pos)
            molok_fillpcts.append(molok_fillpct)
            avg_grs.append(molok_growthrate)


        num_trucks = 61
        truck_range = 150       # km
        truck_capacity = 3000   # kg
        truck_start = 600       # work start
        truck_stop = 1400       # work end

        num_attempts = 1

        mp = routePlanner.MasterPlanner(depot_open, depot_close, depot_pos, molok_pos_list, ttem, molok_fillpcts,
                                                molok_capacity, avg_grs, truck_range, num_trucks, truck_capacity, truck_start,
                                                truck_stop, time_limit, num_attempts=num_attempts)
        
        return mp

    
    def check_fill_lvls(self, empty_at_pct: int = 60):
        latest_rows = self.datastorage.fetch_latest_rows(cursor='main')
        # print(f"Latest rows:\n{latest_rows}")
        last_row = latest_rows[-1]
        self.last_timestamp = float(last_row[-1])           # used for emptying moloks later
        reg_dict = self.datastorage.lin_reg_sections()
        avg_growthrates = self.datastorage.avg_growth_over_period(reg_dict, 0, time.time() * 2)

        moloks_to_empty = []
        for molok_id, row in enumerate(latest_rows):
            fill_pct = float(row[3])

            if fill_pct > empty_at_pct:
                
                unsorted_position = str(row[2])         # find pos and convert from str to tuple of floats (lat, long)
                unsorted_position = unsorted_position.strip('][')
                unsorted_position = unsorted_position.split(' ')
                # print("Before sorting: ", unsorted_position)
                position = []
                for part in unsorted_position:
                    if part != '':
                        position.append(part)
                # print("After sorting: ", position)
                position = (float(position[0]), float(position[1]))

                growth_rate = avg_growthrates[molok_id] * 60            # times 60 to go from pct/second to pct/minute
                # print(f"found molok to empty: {molok_id, position, fill_pct, growth_rate}")
                moloks_to_empty.append([molok_id, position, fill_pct, growth_rate])
        
        return moloks_to_empty
    
    def sim_24_hours(self):
        self.datastorage.startSim(ADDR=('127.0.0.1', 12445), send_freq=1)
        self.datastorage.sim_thread.join()      # wait for sim to end
    
    def run_once(self):

        self.sim_24_hours()
        moloks_to_empty = self.check_fill_lvls()

        if len(moloks_to_empty) > 0:
            # plan routes and save them
            mp = self.make_master_planner(moloks_to_empty)
            
            mp.master()

            routes = mp.current_best['routes']
            empty_times = mp.empty_molok_times

            for route in routes:
                if len(route) > 2:                      # meaning longer than (depot -> depot)
                    for i, destination in enumerate(route):    # loop over stops
                        if destination == 'depot':             # dont do anything to depot
                            continue
                        true_id = moloks_to_empty[destination][0]
                        route[i] = true_id
                        molok_emptied_time = empty_times[destination][1]
                        self.datastorage.set_fillpcts_to_0(molok_emptytime=[(true_id, molok_emptied_time)], route_start_time=self.last_timestamp)
                        try: self.unemptied_moloks.remove(true_id)   # remove molok from list as it has now been emptied
                        except ValueError as e:
                            # print(f"tried to remove molok {true_id} from list. It is already removed. Continuing")
                            pass
            # print(routes)
            # add route to routes_dict
            self.routes_dict[self.day_num] = routes
            self.day_num += 1

        else:
            print(f"No moloks to empty yet.")

            if self.day_num > 1:        # start counting days after the first emptying has happened
                self.day_num += 1


if __name__ == '__main__':

    # --- statics ---

    seed = 10
    num_moloks = 1000
    
    stat_routes = StaticRoutes(seed=seed, num_moloks=num_moloks)

    while len(stat_routes.unemptied_moloks) > 0:
        stat_routes.run_once()
        # print("Latest rows:\n", stat_routes.datastorage.fetch_latest_rows('main'))
        print(f"Moloks yet to empty: {len(stat_routes.unemptied_moloks)}")
        print(f"day num: {stat_routes.day_num}")
        # continue_running = input('----- Press enter to continue')
        time.sleep(0.1)
    
    print(f"Final routes:\n{stat_routes.routes_dict}")
    print(f"final day reached: {stat_routes.day_num}")


    filename = f"static_routes_pickle"

    with open(filename, "wb") as file:
        pickle.dump(stat_routes.routes_dict, file)