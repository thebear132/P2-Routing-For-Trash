import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# our support functions
import support_functions as sf


class routePlanner:

    def __init__(self, depotArgs: list = ["int(openTime)", "int(closeTime)", "tuple(lat, long)"],
                 molokAgrs: list = ["list[molokPositions]", "int(emptying time)", "list[fillPcts]", "int(molokCapacity(kg))", "list[estimatedLinearGrowthrates]"],
                 truckAgrs: list = ["int(range(km))", "int(numTrucks)", "int(capacity(kg))", "int(workStart)", "int(workStop)"]) -> None:
        """
        Executed when initializing a routePlanner-object

        inputs:
         - coming later

        outputs:
         - None
        """
        # --- vars ---
        self.data = self.createDataModel(depotArgs, molokAgrs, truckAgrs)
        
        # create the routing index manager
        self.manager = self.createManager()

        # create routing model
        self.routing = pywrapcp.RoutingModel(self.manager)

        # create and register a transit callback
        self.transit_callback_index = self.routing.RegisterTransitCallback(self.time_callback)

        # Define cost of each arc.
        self.routing.SetArcCostEvaluatorOfAllVehicles(self.transit_callback_index)

        # add constraints and save their names in this var
        self.constraints = self.add_time_windows_constraint()


    def createManager(self):
        """Create the routing index manager"""
        manager = pywrapcp.RoutingIndexManager(len(self.data['time_matrix']),
                                           self.data['numTrucks'], self.data['depotIndex'])
        return manager

    def timeMatrix(self, depotPos, molokPos, truckSpeed=50) -> any:
        """creates the time-matrix based on assumption of avg. speed of truck and distance-matrix"""

        locations = [depotPos] + molokPos
        numMoloks = len(molokPos)
        
        distanceMatrix = sf.create_distance_matrix(numMoloks, locations, decimals_if_float=0)

        # generalisation on truck speed
        speed_kmh = truckSpeed # km/h
        speed_mtr_pr_min = (speed_kmh * 1000) / 60 # meters/minute

        # dividing all distances in distance matrix by speed in order to get time. numpy arrays are smart for this. See simplicity below
        timeMatrix = distanceMatrix / speed_mtr_pr_min

        return timeMatrix

    def createDataModel(self, depotArgs, molokArgs, truckArgs) -> dict:
        """Stores the data for the problem."""
        data = {}

        # --- depot vars ---
        data['depotOpen'] = depotArgs[0]
        data['depotClose'] = depotArgs[1]
        data['depotPos'] = depotArgs[2]
        data['depotIndex'] = 0 # depot index of time-matrix. This is equivalent to element a_11 in matrix A

        # --- molok vars ---
        data['molokPositions'] = molokArgs[0]
        data['molokEmptyTime'] = molokArgs[1]
        data['molokFillPcts'] = molokArgs[2]
        data['molokCapacity'] = molokArgs[3]
        molok_demands = [i/100 * molokArgs[3] for i in molokArgs[2]] # List of kg trash in each molok: pct * max capacity = current weight
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
        data['time_matrix'] = self.timeMatrix(data['depotPos'], data['molokPositions'], truckSpeed=50)

        return data
    

    def time_callback(self, from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = self.manager.IndexToNode(from_index)
        to_node = self.manager.IndexToNode(to_index)
        return self.data['time_matrix'][from_node][to_node]

    def add_time_windows_constraint(self) -> any:
        """creates and adds the time windows (VRPTW) constraint to self.routing"""
        time = 'Time' # name of dimension

        workhours_in_minutes = self.data["truckWorkStop"] - self.data["truckWorkStart"]
        # print(f"workhours in minutes: {workhours_in_minutes}")

        self.routing.AddDimension(
            self.transit_callback_index,
            0,  # don't allow waiting time at moloks
            workhours_in_minutes,  # maximum time per vehicle
            True,  # Force start cumul to zero meaning trucks start driving immediately.
            time) # dimension name assigned here
        time_dimension = self.routing.GetDimensionOrDie(time)

        # Add time window constraints for each location except depot.
        for location_idx, time_window in enumerate(self.data['timeWindows']):
            if location_idx == self.data['depotIndex']: # skips depot
                continue
            index = self.manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

        # Instantiate route start and end times to produce feasible times.
        for i in range(self.data['numTrucks']):
            self.routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(self.routing.Start(i)))
            self.routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(self.routing.End(i)))
            
        return None
    
    def demand_callback(self, from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = self.manager.IndexToNode(from_index)
        return self.data['demands'][from_node]
    



    def addConstraints(self) -> any:
        """creates constraints based on inputs. The constraints are added to self.routing"""

    def showSolution(self) -> list:
        """Returns solution found by OR-Tools"""
        pass

    def main(self) -> None:
        """Runs the show"""
        pass



if __name__ == "__main__":

    depotArgs = [600, 2200, (45, 10)] # 6:00 to 22:00 o'clock and position is (lat, long)
    molokArgs = [[(45, 11), (44, 10)], 10, [80, 90], 500, [0.05, 0.04]] # molokCoordinate list, emptying time cost in minutes, fillPct-list, molok capacity in kg, linear growth rates
    truckArgs = [150, 2, 3000, 600, 1400] # range, number of trucks, truck capacity in kg, working from 6:00 to 14:00

    rp = routePlanner(depotArgs=depotArgs, molokAgrs=molokArgs, truckAgrs=truckArgs)
    print(rp.data)
