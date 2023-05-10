"""It is recommended to visit these links when working on the route planner. They provide great help:
https://developers.google.com/optimization/routing/cvrp
https://developers.google.com/optimization/routing/vrptw#python_3
https://developers.google.com/optimization/routing/dimensions

If they were not enough, read the entire routing section on the page from top to bottom.


TO-TEST:
 - add the solver - tror det er gjort nu. kræver testing. Opstil tests
 - add method for getting timestamps for moloks when they are cannonically emptied - tror det er gjort nu. Valider med DS
 - slack og molok drop skal evt. justeres
 - max tries skal evt justeres
 - test cases where best routes might change (dunno how tho)

TO-DO:

 - Skriv test-kode der kan outputte tabel med relevant data??? - kunne være fucking sej black box test vel (black box siden vi ikke
                                                                                                            kender OR-Tools så godt)

 - skal kunne:
    - returnere bedste ruter til sidst                              DONE
    - returnere hvilke molokker der blev tømt og hvornår            DONE
    - returnere hvilke molokker der blev droppet                    DONE
    - hvor meget slack der var og om der evt. var overfyldninger    (snak i gruppen)

 
 - overvej at molokker bliver mere fyldte i løbet af dagen - hvorfor kan vi ikke løse det? hvad ville det kræve?
 - overvej at man ikke kan tilpasse ruter så de er lige lange - vi kan i hvert fald ikke finde ud af det.
"""

import numpy as np
import time
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# our support functions
import support_functions as sf


class MasterPlanner:

    def __init__(self, depot_open: int, depot_close: int, depot_pos: tuple, molok_pos_list: list, tte_molok: int,
                 fill_pcts: list, molok_capacity: int, molok_est_growthrates: list, truck_range: int, num_trucks: int,
                 truck_capacity: int, work_start: int, work_stop: int, time_limit_seconds: int,
                 first_solution_strategy: int = "2", local_search_strategy: int = "") -> None:
        """
        contains all inputs and meta parameters
        
        Inputs:
        ---
        - depot_open: hhmm (h=hour, m=minute) format of time. 8:00 o'clock is inputted as 0800. Trucks can only start driving
        after depot opens
        - depot_close: hhmm (h=hour, m=minute) format of time. 16:00 o'clock is inputted as 1600. Trucks must return to depot
        before it closes
        - depot_pos: coordinate position of depot in decimal degrees as tuple(lattitude, longitude)

        - molok_pos_list: list of tuples containing molok positions in decimal degrees (lattitude, longitude)
        - tte_molok: time it takes to empty a molok in minutes
        - fill_pcts: list of fill-percentages for each molok as floats. Used to calc actual weight in each molok
        - molok_capacity: weight (kg) capacity of each molok. Used to calc actual weight in each molok
        - molok_est_growthrates: list of estimated linear growthrate of each molok

        - truck_range: Range in kilometers of all trucks
        - num_trucks: number of trucks in total
        - truck_capacity: weight (kg) capacity of all trucks
        - work_start: hhmm (h=hour, m=minute) format of time. Is when trucks start driving
        - work_stop: hhmm (h=hour, m=minute) format of time. Latest time that trucks need to be back at the depot at

        - time_limit_seconds: time limit in seconds. Amount of time MasterPlanner has to optimize routes
        - first_solution_strategy: index of algorithm to use. Choose between:
            - '1' = AUTOMATIC
            - '2' = PATH_CHEAPEST_ARC
            - '3' = CHRISTOFIDES
        - local_search_strategy: index of metaheuristic algorithm to use on top of 'first_solution_strategy'. Choose between:
            - '1' = AUTOMATIC
            - '2' = SIMULATED_ANNEALING
            - '3' = GUIDED_LOCAL_SEARCH
            - '4' = TABU_SEARCH

        """

        # --- depot vars ---
        self.depot_open = depot_open 
        self.depot_close = depot_close
        self.depot_pos = depot_pos

        # --- molok vars ---
        self.molok_pos_list = molok_pos_list
        self.tte_molok = tte_molok
        self.fill_pcts = fill_pcts
        self.molok_capacity = molok_capacity
        self.molok_est_gr = molok_est_growthrates

        # --- truck vars ---
        self.truck_range = truck_range
        self.num_trucks = num_trucks
        self.truck_capacity = truck_capacity
        self.work_start = work_start
        self.work_stop = work_stop 

        # --- master planner vars ---
        self.first_solution_strat = first_solution_strategy
        self.local_search_strat = local_search_strategy
        self.try_num = 1                                    # counts amount of RoutePlanner tries
        self.goal_tries = 10                                # goal for 'self.try_num' to be incremented to
        self.current_best = {                               # save current best solution to dictionary
            "routes": [],
            "visit_times": [],
            "truck_loads": [],
            "truck_distances": []
        }
        self.rp = None

        # --- control vars ---
        self.moloks_dropped = 0
        self.molok_ids = list(range(len(self.fill_pcts)))   # list of all true molok IDs
        self.molok_id_mapping = {}                          # true molokIDs as keys, OR-Tools ref. as value
        for i in range(len(self.fill_pcts)):
            self.molok_id_mapping[i] = i + 1                # initially, all IDs are shifted + 1 due to depot = 0 in OR

        self.actions_taken = []                             # append action if moloks are dropped or slack is added

        self.added_slack = 0                                # slack added to time windows (in minutes)
        self.slack_increment = 10                           # amount to increment slack by each time (in minutes)
        self.slack_max = 3 * self.slack_increment           # max slack. If reached, drop a molok

        # --- time vars ---
        self.time_limit = time_limit_seconds                # seconds for MasterPlanner to try to optimize routes
        self.max_time = time.time() + self.time_limit       # epoch time when MP must be done


    # --- internal methods ---
    def add_action(self, action_type: str, value):
        """
        create action list for drop-action: [try_num, 'drop', (molok_id, molok_pos, fill_pct, est_gr)] \n
        create action list for slack-action: [try_num, 'slack', slack_in_seconds]
        """
        action = [self.try_num, action_type, value]
        return action
    
    def update_routes(self, routes):
            
        id_mapping = self.molok_id_mapping.items()

        for route in routes:
            route[0] = 'depot'
            route[-1] = 'depot'

            for i, node in enumerate(route[1:-1], start=1): # only loop over routes that contain moloks
                for true_ID, OR_ref in id_mapping:          # loop over items in molok_id_mapping dict
                    if OR_ref == node:                      # if OR ref is same as node(OR ref), true ID is put in
                        print(f"switching OR ref {node} with true ID {true_ID}")
                        route[i] = true_ID
                        break       # moloks are only visited once, so break out of loop when found.

        return routes

    def drop_molok(self):
        """drops molok that has the largest sum of distances to other moloks.
        Uses matrix-vector multiplication to sum distances from molok to every other molok"""

        distance_matrix = self.rp.data['distance_matrix']
        vector_of_1s = np.ones(len(distance_matrix))                # n by 1 vector, where n = len(distance_matrix)
        sum_dist_vector = np.matmul(distance_matrix, vector_of_1s)  # matrix-vector mult. to get sum of distances

        molok_id = 0
        max_sum = 0
        for i, sum_dist in enumerate(sum_dist_vector):  # loop over molok sum distances. Enumerate to keep track of ID

            if i == 0:                                  # pass the depot. It should never be dropped.
                continue
            if sum_dist > max_sum:                      # isolate the molok with highest sum dist. 
                max_sum = sum_dist
                molok_id = i - 1                        # Find index starting from 0 (-1 because depot always index 0)
        
        # delete all data on molok before creating new data model. data is saved in action list
        true_molok_id = self.molok_ids.pop(molok_id)    # pop true ID from molok_ids attribute. Ensures only true IDs are left
        molok_pos = self.molok_pos_list.pop(molok_id)
        fill_pct = self.fill_pcts.pop(molok_id)
        est_gr = self.molok_est_gr.pop(molok_id)

        self.molok_id_mapping.pop(true_molok_id)

        self.moloks_dropped += 1
        print(f"dropping molok by ID: {true_molok_id}")
        action = self.add_action('drop', (true_molok_id, molok_pos, fill_pct, est_gr))
        self.actions_taken.append(action)               # append action to actions taken list to keep track of changes

        # after removing a molok, reupdate OR mapping
        for i, key in enumerate(self.molok_id_mapping):
            self.molok_id_mapping[key] = i + 1

    def add_slack_to_tw(self):
        """Adds slack to time windows, allowing moloks to be overfilled if no solution exists. This might help the
        RoutePlanner actually create routes. If added_slack reaches slack_max, a molok should be droppen instead of
        adding more slack. Slack is then reset"""
        drop_molok = False

        if self.added_slack >= self.slack_max:          # if max slack reached/exceeded, reset slack and drop a molok
            drop_molok = True
            self.added_slack = 0
            return drop_molok
        
        self.added_slack += self.slack_increment        # increment slack
        action = self.add_action('slack', self.added_slack)
        self.actions_taken.append(action)
        print(f"Adding slack to time windows. \nMax slack: {self.slack_max} \nCurrent slack added: {self.added_slack}")

        return drop_molok

    def prep_rp(self):
        """prepares the data model and instantiates routePlanner object"""
        depot_args = [self.depot_open, self.depot_close, self.depot_pos]
        molok_args = [self.molok_pos_list, self.tte_molok, self.fill_pcts, self.molok_capacity, self.molok_est_gr, self.added_slack]
        truck_args = [self.truck_range, self.num_trucks, self.truck_capacity, self.work_start, self.work_stop]

        current_time = time.time()
        time_left = self.max_time - current_time
        tries_left = self.goal_tries - (self.try_num - 1)         
        timelimit_for_curr_try = int(time_left / tries_left)   # calculate timelimit for current try in seconds
        print(f"time for current try: {timelimit_for_curr_try} s")

        initial_routes = None

        # if there exists a solution already, pass it to the route planner
        if self.current_best['routes']:

            # remove depot(index 0) from routes or OR-Tools will return None from initial routes
            initial_routes = []                         
            for route in self.current_best['routes']:
                route.pop(0)        # remove depot at start of route
                route.pop(-1)       # remove depot at end of route
                initial_routes.append(route)
            print("Passing current best routes into route planner")

        self.rp = RoutePlanner(depot_args, molok_args, truck_args, timelimit_for_curr_try,
                    first_solution_strategy=self.first_solution_strat, local_search_strategy=self.local_search_strat,
                    initial_routes=initial_routes)
        
        return True

    def run_rp(self):
        
        # run the route planner as set up by self.prep_rp
        solver_status, solution = self.rp.main()

        if solver_status != 1:                    # if route planner could not solve data model
            return solver_status, None, None, None, None

        # get routes to list of lists
        routes = self.rp.get_routes(solution, self.rp.routing, self.rp.manager)

        # get cumulative data from routes and put into lists of lists
        time_const = self.rp.routing.GetDimensionOrDie(self.rp.time_windows_constraint)
        visit_times = self.rp.get_cumul_data(solution, self.rp.routing, dimension=time_const)

        capacity_const = self.rp.routing.GetDimensionOrDie(self.rp.capacity_constraint)
        truck_loads = self.rp.get_cumul_data(solution, self.rp.routing, capacity_const)
        
        distance_constraint = self.rp.routing.GetDimensionOrDie(self.rp.range_constraint)
        truck_distances = self.rp.get_cumul_data(solution, self.rp.routing, distance_constraint)

        return solver_status, routes, visit_times, truck_loads, truck_distances

    def master(self):
        """
        controls routePlanner
        """
        while self.try_num <= self.goal_tries:

            print(f"\n---------- attempt {self.try_num} of {self.goal_tries} ----------")

            success = self.prep_rp()
            if success:
                print("Route planner created succesfully")
            
            solver_status, routes, visit_times, truck_loads, truck_distances = self.run_rp()

            # solver status = 0 means not solved yet, 1 means solved, 2 means no solution found,
            # 3 means timeout, 4 means invalid model
            if solver_status != 1:                          # check if solution exists
                print(f"\nNo solution found. Taking nescessary actions\n")

                # take action if invalid model (4). Will end route planning and user will have to restart with new model
                if solver_status == 4:
                    raise Exception("""Data model invalid. Check if inputs contain non-positive numbers. Could also be that distances are too great for the range of the trucks or similar impossibilities""")

                # take action if no solution found (2) or if timeout (3)
                # always start by adding slack. if max slack reached, a molok will be dropped from route
                drop_molok = self.add_slack_to_tw()

                if drop_molok:
                    self.drop_molok()
                    print("slack reset to 0")

                self.try_num += 1     # after action is taken, increment and continue to next try
                continue                                    



            if self.try_num == self.goal_tries:     # only use when routes are presented at end
                routes = self.update_routes(routes)
                self.empty_molok_times = self.rp.get_molok_empty_timestamps(routes, visit_times)

                print(f"empty time of moloks: {self.empty_molok_times}")
            
            action = self.add_action('routes found', None)
            self.actions_taken.append(action)
                        
            # only reached if solver_status == 1
            self.current_best['routes'] = routes
            self.current_best['visit_times'] = visit_times
            self.current_best['truck_loads'] = truck_loads
            self.current_best['truck_distances'] = truck_distances

            self.rp.print_solution(self.current_best['routes'], self.current_best['visit_times'], self.current_best['truck_loads'], self.current_best['truck_distances'])

            print(self.rp.data)

            print(f"actions taken: {self.actions_taken}")

            # print(f"current_best routes: {self.current_best}")

            self.added_slack/2                      # slack is halved if route is found
            self.try_num += 1                       # increment count



class RoutePlanner:

    def __init__(self, depotArgs: list = ["int(openTime)", "int(closeTime)", "tuple(lat, long)"],
                 molokAgrs: list = ["list[molokPositions]", "int(emptying time)", "list[fillPcts]", "int(molokCapacity(kg))", "list[estimatedLinearGrowthrates]", "int(slack)"],
                 truckAgrs: list = ["int(range(km))", "int(numTrucks)", "int(capacity(kg))", "int(workStart)", "int(workStop)"],
                 time_limit: int = 60,
                 first_solution_strategy: str = "2",
                 local_search_strategy: str = "",
                 initial_routes = None) -> None:
        """
        Executed when initializing a routePlanner-object

        inputs:
         - coming later

        outputs:
         - None
        """
        # --- vars ---
        
        # algorithms for finding initial routes. 
        self.first_solution_strats = {
            "1": routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
            "2": routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            "3": routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES
        }

        # metaheuristic algorithms for escaping a local minimum - a solution that is shorter than all nearby routes,
        # but which is not the global minimum.
        self.local_search_strats = {
            "1": routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC,
            "2": routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
            "3": routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
            "4": routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH
        }

        self.time_limit = time_limit        # limit in seconds for solver to return best found set of routes

        self.first_solution_strategy = self.first_solution_strats[first_solution_strategy]

        self.metaheuristics = False
        if local_search_strategy != "": # only add metaheuristic if specified
            self.local_search_strategy = self.local_search_strats[local_search_strategy]
            self.metaheuristics = True


        self.data = self.create_data_model(depotArgs, molokAgrs, truckAgrs, initial_routes)
        
        # create the routing index manager
        self.manager = self.createManager()

        # create routing model
        self.routing = pywrapcp.RoutingModel(self.manager)

        # create and register a transit callback
        self.transit_callback_index = self.routing.RegisterTransitCallback(self.time_callback)

        # Define cost of each arc.
        self.routing.SetArcCostEvaluatorOfAllVehicles(self.transit_callback_index)

        # add constraints - maybe put in main()?
        self.time_windows_constraint = self.add_time_windows_constraint()
        self.capacity_constraint = self.add_capacity_constraint()
        self.range_constraint = self.add_truckrange_constraint()

    # --- Methods for creating data model ---
    def createManager(self):
        """Create the routing index manager"""
        manager = pywrapcp.RoutingIndexManager(len(self.data['time_matrix']),
                                           self.data['numTrucks'], self.data['depotIndex'])
        return manager

    def time_and_dist_matrices(self, depotPos, molokPos, time_to_empty_molok: int, truckSpeed=50) -> any:
        """creates the time-matrix based on assumption of avg. speed of truck and haversine distance between points
        also adds the time it takes to empty a molok. Distance matrix is created with haversine distance as well.
        Empty time is applied at beginning of transit between points as it results in a truck being able to reach a molok
        before time window closes and then empty it instead of the other way around.
        This means that empty time is NOT applied from depot to molok, but only from molok to molok or molok to depot"""

        locations = [depotPos] + molokPos
        numMoloks = len(molokPos)
        molok_ET = time_to_empty_molok

        # generalisation on truck speed
        speed_kmh = truckSpeed # km/h
        speed_mtr_pr_min = (speed_kmh * 1000) / 60 # meters/minute
        
        start_time = time.time()

        time_matrix = np.zeros(shape=(numMoloks + 1, numMoloks + 1), dtype=np.int64) # +1 because of the depot at ij = 00.
        distance_matrix = np.zeros_like(time_matrix)

        for i in range(len(locations)): # row index
            row_length = len(locations) # Only calc all entries over main diagonal, so i + 1 is subtracted from j's range
            for j in range(i + 1, row_length): # j is column-index.
                
                distance = sf.decimaldegrees_to_meters(locations[i], locations[j])
                
                distance_matrix[i][j] = round(distance)
                distance_matrix[j][i] = round(distance)

                drive_time = round((distance / speed_mtr_pr_min) + molok_ET, 0) # round to whole minutes. OR-Tools requires ints
                
                # mirror entries in main daigonal, so that molok i to j is same as j to i, except from depot(i = 0) to j
                if i == 0:
                    time_matrix[i][j] = drive_time - molok_ET
                else:
                    time_matrix[i][j] = drive_time
                time_matrix[j][i] = drive_time
        
        finish_time = time.time()

        print(f"created matrices of size {time_matrix.shape} in {finish_time - start_time} seconds")
 
        return time_matrix, distance_matrix

    def create_data_model(self, depotArgs, molokArgs, truckArgs, initial_routes) -> dict:
        """Stores the data for the problem."""
        data = {}

        # --- depot vars ---
        data['depotOpen'] = depotArgs[0]
        data['depotClose'] = depotArgs[1]
        data['depotPos'] = depotArgs[2]
        data['depotIndex'] = 0 # depot index of time-matrix. This is equivalent to element a_11 in some matrix A

        # --- molok vars ---
        data['molokPositions'] = molokArgs[0]
        data['molokEmptyTime'] = molokArgs[1]
        data['molokFillPcts'] = molokArgs[2]
        data['molokCapacity'] = molokArgs[3]
        # List of kg trash in each molok: pct * max capacity = current weight. OR-Tools only accepts ints, so value is rounded
        molok_demands = [round(i/100 * molokArgs[3]) for i in molokArgs[2]]
        data['demands'] = [0] # 0 is for depot demand
        for demand in molok_demands:
            data['demands'].append(demand)

        # calc time windows based on fillPct and lin. growthrate f(x)=ax+b from lin. reg.
        data['timeWindows'] = [[0, int(data['depotClose'] - data['depotOpen'])]] # first index is depot TW
        molok_TWs = sf.molokTimeWindows(fillPcts=molokArgs[2], estGrowthrates=molokArgs[4], slack=molokArgs[5])
        for tw in molok_TWs:
            data['timeWindows'].append(tw)

        # --- truck vars ---
        data['truckRange'] = truckArgs[0]
        data['numTrucks'] = truckArgs[1]
        data['truckCapacities'] = [truckArgs[2]] * truckArgs[1] # create list of truck capacities for OR-Tools to use
        data['truckWorkStart'] = truckArgs[3]
        data['truckWorkStop'] = truckArgs[4]
        data['time_matrix'], data['distance_matrix'] = self.time_and_dist_matrices(data['depotPos'], data['molokPositions'], data["molokEmptyTime"])

        data['initial_routes'] = initial_routes

        return data
    
    # --- Methods for creating constraints ---
    def time_callback(self, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = self.manager.IndexToNode(from_index)
        to_node = self.manager.IndexToNode(to_index)
        return self.data['time_matrix'][from_node][to_node]

    def add_time_windows_constraint(self) -> str:
        """
        creates and adds the time windows (VRPTW) constraint to self.routing
        returns dimension name
        """
        dim_name = 'Time' # name of dimension

        workhours_in_minutes = self.data["truckWorkStop"] - self.data["truckWorkStart"]
        # print(f"workhours in minutes: {workhours_in_minutes}")

        self.routing.AddDimension(
            self.transit_callback_index,
            0,  # don't allow waiting time at moloks
            workhours_in_minutes,  # maximum time per vehicle
            True,  # Force start cumul to zero meaning trucks start driving immediately.
            dim_name) # dimension name assigned here
        time_dimension = self.routing.GetDimensionOrDie(dim_name)

        # Add time window constraints for each location except depot.
        for location_idx, time_window in enumerate(self.data['timeWindows']):
            if location_idx == self.data['depotIndex']: # skips depot
                continue
            index = self.manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

        # Add time window constraints for each vehicle start node.
        depot_idx = self.data['depotIndex']
        for vehicle_id in range(self.data['numTrucks']):
            index = self.routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                self.data['timeWindows'][depot_idx][0],
                self.data['timeWindows'][depot_idx][1])

        # Instantiate route start and end times to produce feasible times.
        for i in range(self.data['numTrucks']):
            self.routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(self.routing.Start(i)))
            self.routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(self.routing.End(i)))
            
        return dim_name
    
    def demand_callback(self, from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = self.manager.IndexToNode(from_index)
        return self.data['demands'][from_node]
    
    def add_capacity_constraint(self) -> str:
        """creates and adds the capacity (CPTW) constraint to self.routing"""
        dim_name = 'Capacity'
        demand_callback_index = self.routing.RegisterUnaryTransitCallback(self.demand_callback)

        self.routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,                              # null capacity slack
            self.data['truckCapacities'],   # list of vehicle maximum capacities
            True,                           # start cumul to zero
            dim_name)                       # name of constraint

        return dim_name

    def distance_callback(self, from_index, to_index):
        """Returns the travel distance between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = self.manager.IndexToNode(from_index)
        to_node = self.manager.IndexToNode(to_index)
        return self.data['distance_matrix'][from_node][to_node]
    
    def add_truckrange_constraint(self):
        """creates and adds the trucks' range as a constraint to self.routing"""
        dim_name = 'Travelled_Distance'
        distance_callback_index = self.routing.RegisterTransitCallback(self.distance_callback)

        truck_range_meters = self.data['truckRange'] * 1000     # convert from km to meters

        self.routing.AddDimension(
            distance_callback_index,
            0,                                  # null range slack
            truck_range_meters,                 # truck ranges list
            True,                               # start cumul to zero
            dim_name                            # name of constraint
        )

        return dim_name

    # --- Methods for presenting solution ---
    def get_routes(self, solution, routing, manager):
        """
        Get vehicle routes from a solution and store them in a list. Get vehicle routes and store them in a 
        two dimensional list whose i,j entry is the jth location visited by vehicle i along its route.
        """
        routes = []

        for truck_num in range(routing.vehicles()):             # loop over each trucks route
            index = routing.Start(truck_num)                    # get index of start-node for truck
            
            route = [manager.IndexToNode(index)]                # start route-list for truck. Should always be [0], as that is the depot index
            
            while not routing.IsEnd(index):                     # loop until route ends (meaning return to depot)
                index = solution.Value(routing.NextVar(index))  # get next index
                route.append(manager.IndexToNode(index))        # append node to route
                # print(f"route-var: {route}")

            routes.append(route)

        return routes

    def get_cumul_data(self, solution, routing, dimension):
        """
        Get cumulative data from a dimension and store it in a list.
        Returns a list 'cumul_data' whose i,j entry contains the minimum and maximum of 'CumulVar' for the dimension
        at the jth node on route :
        - cumul_data[i][j][0] is the minimum.
        - cumul_data[i][j][1] is the maximum.
        - In some cases, the min and max are the same as there is only one value (fx. capacity)
        """
        cumul_data = []

        for truck_num in range(routing.vehicles()):             # loop over each trucks route
            route_data = []
            
            index = routing.Start(truck_num)                    # get index of start-node for truck
            dim_var = dimension.CumulVar(index)                 # get value of dimension at that index
            min_dim_var = solution.Min(dim_var)
            max_dim_var = solution.Max(dim_var)
            route_data.append(max_dim_var)
            # route_data.append([min_dim_var, max_dim_var])

            while not routing.IsEnd(index):                     # loop until route ends (meaning return to depot)
                index = solution.Value(routing.NextVar(index))  # get next index
                dim_var = dimension.CumulVar(index)
                min_dim_var = solution.Min(dim_var)
                max_dim_var = solution.Max(dim_var)
                route_data.append(max_dim_var)
                # route_data.append([min_dim_var, max_dim_var])

            cumul_data.append(route_data)

        return cumul_data

    def get_molok_empty_timestamps(self, routes, visit_times) -> list:
        """returns a list of tuples consisting of molok ID and the time from route-start to the molok being emptied (in seconds)"""

        molok_IDs_and_empty_time = []

        for route_num in range(len(routes)):
            zipped_route = list(zip(routes[route_num], visit_times[route_num]))

            for pair in zipped_route:
                if pair[0] != 0 and pair[0] != 'depot':      # only continue of node index not equal to depot
                    true_molok_ID = pair[0]                 # All molok IDs begin from 1, since 0 is reserved for depot. subtract 1 to match DataStorage
                    empty_time_mins = pair[1]
                    empty_time_secs = empty_time_mins * 60  # Time in seconds since truck started driving and it stopped to empty molok
                    molok_IDs_and_empty_time.append((true_molok_ID, empty_time_secs))

        return molok_IDs_and_empty_time                     # list of tuples of (ID, time in seconds)

    def print_solution(self, routes: list, visit_times: list, cumul_load: list, cumul_dist) -> None:
        """Prints solution along with cumulative data and stats on routes"""

        print("\n________Route Planner output________")
        # print(f'Objective: {solution.ObjectiveValue()}')        # Tror det er OR-Tools gæt på optimal værdi af total tid
        
        total_time = 0
        total_dist = 0
        total_load = 0
        num_trucks = len(routes)
        trucks_utilized = 0

        for truck in range(num_trucks):
            print(f"\nTruck {truck}'s route with node index (visit-times) |driven distance| [cumulative load]:")
            route_string = f"Truck {truck}: "                   # begin route at depot
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
                
                route_string += f"{node} ({node_time}) |{node_cumul_dist}| [{node_cumul_load}]"

                if stop_num < stops - 1:                        # add an arrow between nodes
                    route_string += " -> "
                
                elif stop_num == stops - 1:                     # add totals to end of route string
                    route_string += f"\nRoutes total time: {node_time} min \nRoutes total distance: {node_cumul_dist} km \nRoutes total load: {node_cumul_load} kg"
                    total_time += node_time                     # count total time
                    total_load += node_cumul_load               # count total load
                    total_dist += node_cumul_dist               # count total distance

                    if node_time != 0:                          # If truck actually left depot, count it as utilized
                        trucks_utilized += 1 

            print(route_string)
        
        # --- key values ---
        num_moloks = len(self.data['molokPositions'])
        final_string = f"\n___Key performance indicators___\n\nMoloks emptied: {num_moloks} \n"
        final_string += f"Trucks utilized: {trucks_utilized} \n"
        final_string += f"Total time spent: {total_time} min \nTotal distance driven: {total_dist} km \nTotal load collected: {total_load} kg \n"
        final_string += f"Average number of moloks pr. route: {num_moloks / trucks_utilized} moloks/route \n"
        final_string += f"Average time spent pr. route: {total_time / trucks_utilized} min/route \n"
        final_string += f"Average distance driven pr. route: {total_dist / trucks_utilized} km/route \n"
        final_string += f"Average load collected pr. route: {total_load / trucks_utilized} kg/route \n"

        print(final_string)


    def main(self):
        """Runs the show"""

        # Setting first solution heuristic.
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (self.first_solution_strategy)

        if self.metaheuristics == True:
            print("applying metaheuristics")
            search_parameters.local_search_metaheuristic = (self.local_search_strategy)

        search_parameters.time_limit.seconds = self.time_limit

        # If initial routes exist, solve from that standpoint
        if self.data['initial_routes'] != None:
            # According to the OR-Tools tutorial, when an initial solution is given, the model will be closed with the 
            # default search parameters unless it is closed with the custom search parameters.
            self.routing.CloseModelWithParameters(search_parameters)
            initial_solution = self.routing.ReadAssignmentFromRoutes(self.data['initial_routes'], True)

            solution = self.routing.SolveFromAssignmentWithParameters(initial_solution, search_parameters)
            solver_status = self.routing.status()
            print("Solver status: ", solver_status)

        # if no initial routes are passed in, solve from the ground up.
        else:
            solution = self.routing.SolveWithParameters(search_parameters)

            solver_status = self.routing.status()
            print("Solver status: ", solver_status)

        return solver_status, solution


if __name__ == "__main__":

    num_trucks = 2
    ttem = 5                                            # time to empty molok
    num_moloks = 3
    truck_range = 15
    truck_capacity = 3000
    timelimit = 20
    first_solution_strategy = "3"
    local_search_strategy = "3"
    seed = 20
    np.random.seed(seed=seed)
    
    # molok_pos_list = [(45, 11), (43.5, 10), (44, 11)]
    # molok_fillpcts = [80, 90, 75]
    # avg_grs = [0.05, 0.04, 0.06]                        # avg growthrates

    molok_pos_list_of_lists = sf.normal_distribution(45, 10, 0.1, num_moloks)
    molok_pos_list = []
    for pos in molok_pos_list_of_lists:
        molok_pos_list.append(tuple(pos))

    molok_fillpcts = np.random.normal(70, 7.5, num_moloks)
    avg_grs = np.random.normal(0.1, 0.01, num_moloks)

    mp = MasterPlanner(600, 2200, (45, 10), molok_pos_list, ttem, molok_fillpcts.tolist(), 500, avg_grs.tolist(), truck_range, num_trucks,
                       truck_capacity, 600, 1400, timelimit, first_solution_strategy, local_search_strategy)

    
    mp.master()

    stop_time =time.time()

    time_diff = mp.max_time - stop_time
    print(time_diff)

    exit()
