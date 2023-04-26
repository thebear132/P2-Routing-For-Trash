"""It is recommended to visit these links when working on the route planner. They provide great help:
https://developers.google.com/optimization/routing/cvrp
https://developers.google.com/optimization/routing/vrptw#python_3
https://developers.google.com/optimization/routing/dimensions

If they were not enough, read the entire routing section on the page from top to bottom.

HUSK NU FOR FAEN AT OR-TOOLS IKKE FUCKER MED FLOATS!!! DEN SKAL FODRES INTEGERS. ELLERS ER DEN ET LILLE RØVHUL DER IKKE
MELDER FEJL MEN SIMPELTHEN BARE GIVER UBRUGELIGT OUTPUT OG BLIVER FORNÆRMET!


TO-DO:
 - add the solver - tror det er gjort nu. kræver testing

 - add solution saving and printer

 - add logic if no routes are found (time-windows get slack? Måske noget med n iterationer og m mere slack pr iteration?)

 - add distance constraint for trucks
"""




import numpy as np
import time
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# our support functions
import support_functions as sf


class routePlanner:

    def __init__(self, depotArgs: list = ["int(openTime)", "int(closeTime)", "tuple(lat, long)"],
                 molokAgrs: list = ["list[molokPositions]", "int(emptying time)", "list[fillPcts]", "int(molokCapacity(kg))", "list[estimatedLinearGrowthrates]"],
                 truckAgrs: list = ["int(range(km))", "int(numTrucks)", "int(capacity(kg))", "int(workStart)", "int(workStop)"],
                 time_limit: int = 60,
                 first_solution_strategy: str = "2",
                 local_search_strategy: str = "") -> None:
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


        self.data = self.createDataModel(depotArgs, molokAgrs, truckAgrs)
        
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


    def createManager(self):
        """Create the routing index manager"""
        manager = pywrapcp.RoutingIndexManager(len(self.data['time_matrix']),
                                           self.data['numTrucks'], self.data['depotIndex'])
        return manager

    def time_matrix(self, depotPos, molokPos, time_to_empty_molok: int, truckSpeed=50) -> any:
        """creates the time-matrix based on assumption of avg. speed of truck and haversine distance between points
        also adds the time it takes to empty a molok.
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

        for i in range(len(locations)): # row index
            row_length = len(locations) # Only calc all entries over main diagonal, so i + 1 is subtracted from j's range
            for j in range(i + 1, row_length): # j is column-index.
                
                distance = sf.decimaldegrees_to_meters(locations[i], locations[j])

                drive_time = round((distance / speed_mtr_pr_min) + molok_ET, 0) # round to whole minutes. OR-Tools requires ints

                # mirror entries in main daigonal, so that molok i to j is same as j to i, except from depot(i = 0) to j
                if i == 0:
                    time_matrix[i][j] = drive_time - molok_ET
                else:
                    time_matrix[i][j] = drive_time
                time_matrix[j][i] = drive_time
        
        finish_time = time.time()

        print(f"created time matrix of size {time_matrix.shape} in {finish_time - start_time} seconds")
 
        return time_matrix

    def createDataModel(self, depotArgs, molokArgs, truckArgs) -> dict:
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
        molok_TWs = sf.molokTimeWindows(fillPcts=molokArgs[2], estGrowthrates=molokArgs[4])
        for tw in molok_TWs:
            data['timeWindows'].append(tw)

        # --- truck vars ---
        data['truckRange'] = truckArgs[0]
        data['numTrucks'] = truckArgs[1]
        data['truckCapacities'] = [truckArgs[2]] * truckArgs[1] # create list of truck capacities for OR-Tools to use
        data['truckWorkStart'] = truckArgs[3]
        data['truckWorkStop'] = truckArgs[4]
        data['time_matrix'] = self.time_matrix(data['depotPos'], data['molokPositions'], data["molokEmptyTime"], truckSpeed=50)

        return data
    

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
            dim_name)                     # name of constraint

        return dim_name
    
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
        """
        cumul_data = []

        for truck_num in range(routing.vehicles()):             # loop over each trucks route
            route_data = []
            
            index = routing.Start(truck_num)                    # get index of start-node for truck
            dim_var = dimension.CumulVar(index)                 # get value of dimension at that index
            min_dim_var = solution.Min(dim_var)
            max_dim_var = solution.Max(dim_var)
            route_data.append([min_dim_var, max_dim_var])

            while not routing.IsEnd(index):                     # loop until route ends (meaning return to depot)
                index = solution.Value(routing.NextVar(index))  # get next index
                dim_var = dimension.CumulVar(index)
                min_dim_var = solution.Min(dim_var)
                max_dim_var = solution.Max(dim_var)
                route_data.append([min_dim_var, max_dim_var])

            cumul_data.append(route_data)

        return cumul_data

    def print_solution(self) -> list:
        """Returns solution found by OR-Tools"""
        pass


    def main(self):
        """Runs the show"""

        # Setting first solution heuristic.
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (self.first_solution_strategy)

        if self.metaheuristics == True:
            print("applying metaheuristics")
            search_parameters.local_search_metaheuristic = (self.local_search_strategy)
        search_parameters.time_limit.seconds = self.time_limit

        solution = self.routing.SolveWithParameters(search_parameters)

        print("Solver status: ", self.routing.status())

        return solution


if __name__ == "__main__":

    depotArgs = [600, 2200, (45, 10)] # 6:00 to 22:00 o'clock and position is (lat, long)
    molokArgs = [[(45, 11), (43.5, 10), (44, 11)], 10, [80, 90, 75], 500, [0.05, 0.04, 0.06]] # molokCoordinate list, emptying time cost in minutes, fillPct-list, molok capacity in kg, linear growth rates
    truckArgs = [150, 2, 3000, 600, 1400] # range, number of trucks, truck capacity in kg, working from 6:00 to 14:00

    rp = routePlanner(depotArgs=depotArgs, molokAgrs=molokArgs, truckAgrs=truckArgs)
    print(rp.data)

    solution = rp.main()

    print(solution)

    routes = rp.get_routes(solution, rp.routing, rp.manager)

    time_const = rp.routing.GetDimensionOrDie(rp.time_windows_constraint)
    tws = rp.get_cumul_data(solution, rp.routing, dimension=time_const)

    capacity_const = rp.routing.GetDimensionOrDie(rp.capacity_constraint)
    truck_loads = rp.get_cumul_data(solution, rp.routing, capacity_const)

    print(routes)
    print(tws)
    print(truck_loads)



    def print_solution(data, manager, routing, solution):
        """Prints solution on console."""
        print(f'Objective: {solution.ObjectiveValue()}')
        time_dimension = routing.GetDimensionOrDie('Time')
        total_time = 0
        for vehicle_id in range(data['numTrucks']):
            index = routing.Start(vehicle_id)
            plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
            while not routing.IsEnd(index):
                time_var = time_dimension.CumulVar(index)
                plan_output += '{0} Time({1},{2}) -> '.format(
                    manager.IndexToNode(index), solution.Min(time_var),
                    solution.Max(time_var))
                index = solution.Value(routing.NextVar(index))
            time_var = time_dimension.CumulVar(index)
            plan_output += '{0} Time({1},{2})\n'.format(manager.IndexToNode(index),
                                                        solution.Min(time_var),
                                                        solution.Max(time_var))
            plan_output += 'Time of the route: {}min\n'.format(
                solution.Min(time_var))
            print(plan_output)
            total_time += solution.Min(time_var)
        print('Total time of all routes: {}min'.format(total_time))


    print_solution(data=rp.data, manager=rp.manager, routing=rp.routing, solution= solution)
