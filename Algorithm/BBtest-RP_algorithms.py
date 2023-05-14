"""
Black box testing of which algorithm to choose when running our master planner and route planner.

The test will run like this:
Static parameters:
- 61 trucks
- same depot position (45, 10) <- coordinates in decimal degrees
- workhours and openhours
- emptytime of moloks
- truck capacity
- solution limit
(see inputs for more)


Dynamic parameters:

- seed (we iterate over 3 different seeds to test the algorithm with three different datamodels)
- 100, 200, 300 moloks. (to try to find big-O somewhat)

Every single run is timed and put into a table.
The most simple algorithm PATH_CHEAPEST_ARC will be the baseline and every other algorithm will be compared to it with +/- performance in percentage.

First we compare the 'first solution strategies'. We will then use 'CHRISTOFIDES' as 'first solution strategy' when comparing the 'local search strategies'.


The test will go like this in pseudocode and be done for the initial solutions and then for the metaheuristics:

for seed in [10, 20, 30]:
    for num_moloks in [100, 200, 300]:
        for algorithm in algorithms:
        
            result = route_planner(inputs, num_moloks, algorithm)
            table.append(result)    

save result in pickle file

"""

import numpy as np
import time
import pandas as pd
import pickle

import support_functions as sf
from routePlanner import RoutePlanner


def save_KPIs(num_moloks: int, routes: list, visit_times: list, cumul_load: list, cumul_dist):
    total_time = 0
    total_dist = 0
    total_load = 0
    num_moloks = num_moloks
    num_trucks = len(routes)
    trucks_utilized = 0

    for truck in range(num_trucks):

        route_lst = routes[truck]                           # save trucks route to var
        route_visit_times = visit_times[truck]              # save trucks visit times to var
        route_cumul_load = cumul_load[truck]                # save trucks cumulative load to var
        route_cumul_dist = cumul_dist[truck]                # save trucks cumulative distance to var

        stops = len(route_lst)
        for stop_num in range(stops):                       # loop over the length of trucks route
            node = route_lst[stop_num]                      # molok or depot index (if 0)
            node_time = route_visit_times[stop_num]         # visit time at node
            node_cumul_load = route_cumul_load[stop_num]    # cumulative load at node
            node_cumul_dist = route_cumul_dist[stop_num]    # cumulative distance at node
            node_cumul_dist = node_cumul_dist / 1000        # convert to km

            if stop_num < stops - 1:                        # add an arrow between nodes
                route_string = " -> "
            
            elif stop_num == stops - 1:                     # add totals to end of route string
                route_string = f"\nRoutes total time: {node_time} min \nRoutes total distance: {node_cumul_dist} km \nRoutes total load: {node_cumul_load} kg"
                total_time += node_time                     # count total time
                total_load += node_cumul_load               # count total load
                total_dist += node_cumul_dist               # count total distance

                if node_time != 0:                          # If truck actually left depot, count it as utilized
                    trucks_utilized += 1 
    

    moloks_pr_route = num_moloks / trucks_utilized
    time_pr_route = total_time / trucks_utilized
    distance_pr_route = total_dist / trucks_utilized
    load_pr_route = total_load / trucks_utilized

    return num_moloks, total_time, total_dist, total_load, moloks_pr_route, time_pr_route, distance_pr_route, load_pr_route




if __name__ == "__main__":

    # --- statics ---
    depot_open = 600        # hhmm time
    depot_close = 2200      # hhmm time
    depot_pos = (45, 10)    # decimal degrees coords

    ttem = 5                # time to empty molok
    molok_capacity = 200    # kg
    slack = 0               # no added slack to timewindows for moloks

    num_trucks = 61
    truck_range = 150       # km
    truck_capacity = 3000   # kg
    truck_start = 600       # work start
    truck_stop = 1400       # work end

    solution_limit = 500    # Limit to the number of solutions generated during the search
    time_limit = 2        # 2 minute timelimit

    # --- test vars ---
    seeds = [10, 20, 30]
    num_moloks_list = [10, 50, 100]
    first_solution_strategies_list = ["1", "2", "3"]
    local_search_strategies = ["1", "2", "3", "4"]

    test_res_dict = {}

    # start looping to test params
    for seed in seeds:

        test_res_dict[seed] = {}
        times = []
        df_index = []

        test_res_dict[seed]['times'] = []
        test_res_dict[seed]['num_moloks'] = []
        test_res_dict[seed]['total_time'] = []
        test_res_dict[seed]['total_dist'] = []
        test_res_dict[seed]['total_load'] = []
        test_res_dict[seed]['moloks_pr_route'] = []
        test_res_dict[seed]['time_pr_route'] = []
        test_res_dict[seed]['dist_pr_route'] = []
        test_res_dict[seed]['load_pr_route'] = []

        for num_moloks in num_moloks_list:

            np.random.seed(seed=seed)           # lock seed for random generation. This will make datamodels identical

            molok_pos_list_of_lists = sf.normal_distribution(45, 10, 0.1, num_moloks)
            molok_pos_list = []
            for pos in molok_pos_list_of_lists:
                molok_pos_list.append(tuple(pos))

            molok_fillpcts = np.random.normal(70, 5, num_moloks)
            avg_grs = np.random.normal(0.1, 0.01, num_moloks)

            for i, sol_strat in enumerate(local_search_strategies):  # use RP in this loop. Save results from here as well

                df_index.append(f"{sol_strat}")

                print(f"\n@@@@@ Test for local sol strat {sol_strat} @@@@@")

                print(f"___Test_Params___")
                print(f"seed: {seed}")
                print(f"num_moloks: {num_moloks}")

                rp = RoutePlanner(depotArgs=[depot_open, depot_close, depot_pos],
                                  molokAgrs=[molok_pos_list, ttem, molok_fillpcts, molok_capacity, avg_grs, slack],
                                  truckAgrs=[truck_range, num_trucks, truck_capacity, truck_start, truck_stop],
                                  time_limit=time_limit,
                                  solution_limit=None,                      # set to None if time_limit is to be used
                                  first_solution_strategy="1",              # set to "1" when testing local search metaheuristics
                                  local_search_strategy=sol_strat,          # set to 'local_search_strategies'
                                  initial_routes=None)
                
                # print(rp.data)
                print(f"@ Starting to solve problem")
                start = time.time()
                solver_status, solution = rp.main()
                finish = time.time()

                # get routes to list of lists
                routes = rp.get_routes(solution, rp.routing, rp.manager)

                # get cumulative data from routes and put into lists of lists
                time_const = rp.routing.GetDimensionOrDie(rp.time_windows_constraint)
                visit_times = rp.get_cumul_data(solution, rp.routing, dimension=time_const)

                capacity_const = rp.routing.GetDimensionOrDie(rp.capacity_constraint)
                truck_loads = rp.get_cumul_data(solution, rp.routing, capacity_const)
                
                distance_constraint = rp.routing.GetDimensionOrDie(rp.range_constraint)
                truck_distances = rp.get_cumul_data(solution, rp.routing, distance_constraint)

                num_moloks, total_time, total_dist, total_load, moloks_pr_route, time_pr_route, distance_pr_route, load_pr_route = save_KPIs(num_moloks, routes, visit_times, truck_loads, truck_distances)

                time_spent = finish - start
                times.append(time_spent)
                # print(f"Time spent solving: {time_spent} seconds")

                # if i == 0:          # save first solution strategy's result. All others will then be compared to this
                #     first_sol_total_time = total_time
                #     first_sol_total_dist = total_dist
                #     first_sol_total_load = total_load
                #     first_sol_t_pr_r = time_pr_route
                #     first_sol_d_pr_r = distance_pr_route
                #     first_sol_l_pr_r = load_pr_route

                # elif i in [1, 2]:               # compare solution with christofides and display as +/-
                #     total_time = first_sol_total_time - total_time
                #     total_dist = first_sol_total_dist - total_dist
                #     total_load = first_sol_total_load - total_load
                #     time_pr_route = first_sol_t_pr_r - time_pr_route
                #     distance_pr_route = first_sol_d_pr_r - distance_pr_route
                #     load_pr_route = first_sol_l_pr_r - load_pr_route


                test_res_dict[seed]['times'].append(time_spent)
                test_res_dict[seed]['num_moloks'].append(num_moloks)
                test_res_dict[seed]['total_time'].append(total_time)
                test_res_dict[seed]['total_dist'].append(total_dist)
                test_res_dict[seed]['total_load'].append(total_load)
                test_res_dict[seed]['moloks_pr_route'].append(moloks_pr_route)
                test_res_dict[seed]['time_pr_route'].append(time_pr_route)
                test_res_dict[seed]['dist_pr_route'].append(distance_pr_route)
                test_res_dict[seed]['load_pr_route'].append(load_pr_route)

df_dict = {
    "inputs" : [depot_open, depot_close, depot_pos, ttem, molok_capacity, slack, num_trucks, truck_range,
                truck_capacity, truck_start, truck_stop, time_limit, seeds, num_moloks_list, first_solution_strategies_list,
                local_search_strategies]
}

for seed in seeds:
    df_dict[seed] = pd.DataFrame(data=test_res_dict[seed], index=df_index)
    # print(df_dict[seed])

filename = f"BB_algotest_meta-timelimit123"

with open(filename, "wb") as file:
    pickle.dump(df_dict, file)

