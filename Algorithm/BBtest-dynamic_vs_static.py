"""
This document consists of the following:
 - Logic to find static routes
    - save routes for later use
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

import support_functions as sf
import routePlanner
from datastorage import DataStorage



class StaticRoutes:

    def __init__(self) -> None:
        self.unemptied_moloks = []
        self.routes_dict = {}

        self.day_num = 1
    

    def prep_test(self, num_moloks):

        self.unemptied_moloks = list(range(num_moloks))


if __name__ == '__main__':

    # --- statics ---

    seed = 10
    time_limit = 20         # seconds

    depot_open = 600        # hhmm time
    depot_close = 2200      # hhmm time
    depot_pos = (45, 10)    # decimal degrees coords

    num_moloks = 10
    ttem = 5                # time to empty molok
    molok_capacity = 200    # kg
    slack = 0               # no added slack to timewindows for moloks
    molok_pos_list_of_lists = sf.normal_distribution(45, 10, 0.1, num_moloks)
    molok_pos_list = []
    for pos in molok_pos_list_of_lists:
        molok_pos_list.append(tuple(pos))

    molok_fillpcts = np.random.normal(70, 5, num_moloks)
    avg_grs = np.random.normal(0.1, 0.01, num_moloks)

    num_trucks = 61
    truck_range = 150       # km
    truck_capacity = 3000   # kg
    truck_start = 600       # work start
    truck_stop = 1400       # work end

    master_planner = routePlanner.MasterPlanner(depot_open, depot_close, depot_pos, molok_pos_list, ttem, molok_fillpcts,
                                                molok_capacity, avg_grs, truck_range, num_trucks, truck_capacity, truck_start,
                                                truck_stop, time_limit)

    stat_routes = StaticRoutes()
    stat_routes.prep_test(num_moloks=num_moloks)

    print(stat_routes.unemptied_moloks)