import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# our support functions
import support_functions as sf


def create_data_model(distance_matrix, num_vehicles, depot_index):
    """Stores the data for the problem."""
    data = {}
    data['distance_matrix'] = distance_matrix
    data['num_vehicles'] = num_vehicles
    data['depot'] = depot_index

    return data


def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')
    max_route_distance = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_distance = 0
        while not routing.IsEnd(index):
            plan_output += ' {} -> '.format(manager.IndexToNode(index))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        plan_output += '{}\n'.format(manager.IndexToNode(index))
        plan_output += 'Distance of the route: {}m\n'.format(route_distance)
        print(plan_output)
        max_route_distance = max(route_distance, max_route_distance)
    print('Maximum of the route distances: {}m'.format(max_route_distance))


def main(distance_matrix, num_vehicles, depot_index=0):
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model(distance_matrix, num_vehicles, depot_index)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                           data['num_vehicles'], data['depot'])
    
    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance constraint.
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        1000,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print('No solution found !')



if __name__ == '__main__':

    # VRP vars
    num_moloks = 100
    num_vehicles = 10

    # simulation variables
    depot_position = (57.04830168757387, 9.915331444926698)
    coord_distance_max = 0.0025016281667760154 # approximately 550 meters in decimaldegrees
    coord_center = depot_position # center of normal distribution of simulation of molok positions
    
    locations = np.array([depot_position])
    locations = np.append(locations, sf.normal_distribution(coord_center[0], coord_center[1], coord_distance_max, num_moloks), axis=0)

    locations = locations.tolist()

    dist_matrix = sf.create_distance_matrix(num_moloks, locations, decimals_if_float=0)

    print(dist_matrix)

    main(distance_matrix=dist_matrix, num_vehicles=num_vehicles)



    """maprelated stuff. Not nescesary for distance matrix creation"""

    # coords_list = locations

    # map_obj = sf.create_map(location=coord_center)

    # map_obj = sf.create_circles(map_obj=map_obj, number_of_moloks=num_moloks, coords=coords_list[1:], radius=1)
    # map_obj = sf.create_circles(map_obj=map_obj, number_of_moloks=1, coords=[depot_position], radius=2, color='purple') # tilføjer depotet til kortet

    # sf.save_and_show_map(map_obj=map_obj)