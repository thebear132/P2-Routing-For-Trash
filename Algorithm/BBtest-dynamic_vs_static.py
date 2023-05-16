"""
This document consists of the following:
 - Logic to find static routes
    - save routes in dict as pickle for later use (save inputs as well)
    - cover all 1000 moloks

 - test unit for comparing results
    - run day by day AFTER static routes have been created
    - showcase KPI comparison
    - showcase overfill

"""

import numpy as np
import time
import pickle

import support_functions as sf
import routePlanner
from datastorage import DataStorage



class FindStaticRoutes:

    def __init__(self, seed, num_moloks) -> None:
        self.unemptied_moloks = []
        self.routes_dict = {}

        self.day_num = 1
        self.seed = seed
        self.num_moloks = num_moloks
        self.conservative_growth = None         # assume that all moloks grow by some amount. Amount will be conservative.
        # This assumes that the municipality does not have measuring devices and that they are conservative when it comes to assuming
        # growth. Paired with a low threshhold for when a molok should be emptied, we believe this will be an OK depiction of the
        # static routes

        self.unemptied_moloks = list(range(num_moloks))
        self.datastorage = DataStorage()
        self.datastorage.create_and_connect_to_DB(DB_name='Static_DB.db')
        tablename = self.datastorage.create_table(self.seed, self.num_moloks, 'sim')
        self.datastorage.select_table(tablename, self.seed, self.num_moloks)
    
    def make_master_planner(self, moloks_to_empty):

        time_limit = 3             # seconds

        depot_open = 600            # hhmm time
        depot_close = 2200          # hhmm time
        depot_pos = (57.014, 9.98)  # decimal degrees coords

        ttem = 5                # time to empty molok
        molok_capacity = 500    # kg
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

        num_attempts = 1        # must not drop molok nor add slack

        mp = routePlanner.MasterPlanner(depot_open, depot_close, depot_pos, molok_pos_list, ttem, molok_fillpcts,
                                                molok_capacity, avg_grs, truck_range, num_trucks, truck_capacity, truck_start,
                                                truck_stop, time_limit, num_attempts=num_attempts)
        
        return mp
    
    def check_fill_lvls(self, empty_at_pct: int = 60):
        latest_rows = self.datastorage.fetch_latest_rows(cursor='main')
        # print(f"Latest rows:\n{latest_rows}")
        last_row = latest_rows[-1]
        self.last_timestamp = float(last_row[-1])           # used for emptying moloks later

        moloks_to_empty = []
        for molok_id, row in enumerate(latest_rows):
            fill_pct = float(row[3])

            if fill_pct > empty_at_pct:
                if self.conservative_growth == None:            # when the first ever molok has to be emptied, calc a conservative gr
                    reg_dict = self.datastorage.lin_reg_sections()
                    avg_growthrates = self.datastorage.avg_growth_over_period(reg_dict, 0, time.time() * 2)
                    max_avg_gwr = max(avg_growthrates)
                    self.conservative_growth = max_avg_gwr * 1.25
                    print(f"conservative gr set to: {self.conservative_growth}")
                
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

                growth_rate = self.conservative_growth * 60            # times 60 to go from pct/second to pct/minute
                print(f"found molok to empty: {molok_id, position, fill_pct, growth_rate}")
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
            visit_times = mp.current_best['visit_times']
            truck_loads = mp.current_best['truck_loads']
            truck_distances = mp.current_best['truck_distances']


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
            self.routes_dict[self.day_num] = [routes, visit_times, truck_loads, truck_distances]
            self.day_num += 1

        else:
            print(f"No moloks to empty yet.")

            if self.day_num > 1:        # start counting days after the first emptying has happened
                self.day_num += 1

    def create_static_routes(self):

        while len(self.unemptied_moloks) > 0:
            self.run_once()
            # print("Latest rows:\n", self.datastorage.fetch_latest_rows('main'))
            print(f"Moloks yet to empty: {len(self.unemptied_moloks)}")
            print(f"day num: {self.day_num}")
            # continue_running = input('----- Press enter to continue')
            time.sleep(0.1)
    
        print(f"Final routes:\n{self.routes_dict}")
        print(f"final day reached: {self.day_num}")

        filename = f"static_routes_pickle"

        with open(filename, "wb") as file:
            pickle.dump(self.routes_dict, file)


class RunStaticRoutes:
    """Class to run static routes"""

    def __init__(self, seed, num_moloks, static_dict: dict, cycles_to_run: int) -> None:
        
        self.ADDR = ('127.0.0.1', 12445)
        self.seed = seed
        self.num_moloks = num_moloks

        self.KPI_dict = {}
        
        self.mcap = 500
        self.fill_pcts = None

        self.static_dict = static_dict

        self.current_day = 0
        self.current_cycle = 1                  # add 1 each time day 1 is reached again
        self.cycles_to_run = cycles_to_run      # stop running when all cycles complete

    def create_DS(self):
        # static datastorage
        self.stat_DS = DataStorage()
        self.stat_DS.create_and_connect_to_DB('Static_DB.db')
        tablename = self.stat_DS.create_table(self.seed, self.num_moloks, 'sim')
        self.stat_DS.select_table(tablename, self.seed, self.num_moloks)


    def master(self):
        """Runs the show"""
        # create DS object
        self.create_DS()

        # # sim until threshold is met. Then run day 1's routes and count upwards
        # self.sim_until_threshold_met(ADDR=self.ADDR)

        # start driving static routes
        while self.current_cycle <= self.cycles_to_run:     # run cycles_to_run amount of cycles
            print('\nCycle num:', self.current_cycle)
            for day in self.static_dict:                  # get key in routes dict

                while day != self.current_day:              # sim until days match
                    self.stat_DS.startSim(ADDR=self.ADDR, send_freq=1)
                    self.stat_DS.sim_thread.join()
                    self.current_day += 1

                if day == self.current_day:                 # only drive on specific days
                    print(f"\n@ Day{day}")
                    current_days_list = self.static_dict[day]
                    routes = current_days_list[0]
                    visit_times = current_days_list[1]
                    truck_loads = current_days_list[2]
                    truck_distances = current_days_list[3]
                    # find KPIs for current_day
                    moloks_emptied = 0
                    trucks_used = 0
                    tot_time = 0
                    tot_dist = 0
                    tot_load = 0

                    for truck_id, route in enumerate(routes):
                        if len(route) > 2:                      # truck is only in use if len > 2
                            trucks_used += 1
                            moloks_emptied += (len(route) - 2)          # number of moloks on route
                            tot_time += visit_times[truck_id][-1]       # add cumul time of each route
                            tot_dist += truck_distances[truck_id][-1]   # add cumul dist of each route

                            latest_rows = self.stat_DS.fetch_latest_rows('main')
                            fillpcts = []
                            overfill = []
                            moloks_to_empty = []
                            latest_timestamp = float(latest_rows[-1][-1])
                            for molok_id in route[1:-1]:
                                fill_pct = float(latest_rows[molok_id][3])
                                fillpcts.append(fill_pct)
                                if fill_pct > 100:
                                    overfill.append((molok_id, fill_pct))
                                moloks_to_empty.append((molok_id, 0))
                                tot_load += (fill_pct * self.mcap) / 100
                    
                    print(f"_____Key Performance Indicators_____")
                    print(f"moloks emptied: {moloks_emptied}")
                    print(f"trucks used: {trucks_used}")
                    print(f"total time: {tot_time}")
                    print(f"total distance: {tot_dist}")
                    print(f"total load: {tot_load}")
                    print(f"Moloks that where overfilled: {overfill}")
                    print(f"avg moloks pr route: {moloks_emptied/trucks_used}")
                    print(f"avg time pr route: {tot_time/trucks_used}")
                    print(f"avg distance pr route: {tot_dist/trucks_used}")
                    print(f"avg load pr route: {tot_load/trucks_used}")

                # empty moloks
                self.stat_DS.set_fillpcts_to_0(molok_emptytime=moloks_to_empty, route_start_time=latest_timestamp)

                # run sim for 24 hours
                print(f"\nSimulating 24 hours")
                self.stat_DS.startSim(ADDR=self.ADDR, send_freq=1)
                self.stat_DS.sim_thread.join()
                # count current day up
                self.current_day += 1
            
            # when a cycle is over, count self.current_cycle up 1
            self.current_cycle += 1
            self.current_day += 1

if __name__ == '__main__':

    seed = 10
    num_moloks = 10

    stat_MP = FindStaticRoutes(seed, num_moloks)
    stat_MP.create_static_routes()

    filename = 'static_routes_pickle'
    with open(filename, "rb") as file:
        static_dict = pickle.load(file)

    run_stat = RunStaticRoutes(seed, num_moloks, static_dict, 3)
    run_stat.master()
