import numpy as np
import time

def decimaldegrees_to_meters(coords_tuple1, coords_tuple2):

    R = 6371 # earth's radius in km.
    
    # latitudes
    lat1 = np.radians(coords_tuple1[0])
    lat2 = np.radians(coords_tuple2[0])

    # longitudes
    long1 = np.radians(coords_tuple1[1])
    long2 = np.radians(coords_tuple2[1])

    lat_calc = ( np.sin( (lat2 - lat1) / 2) ) **2

    long_calc = (np.sin( (long2 - long1) / 2)) **2

    calc = np.sqrt( lat_calc + np.cos(lat1) * np.cos(lat2) * long_calc )

    d = 2 * R * np.arcsin(calc) # in km

    return d * 1000 # ganges til meter


def normal_distribution(loc_lat, loc_long, scale, size):
     norm_dist_lat = np.random.normal(loc_lat, scale/2, size=size) # normal distribution of latitudes with size being number of moloks and scale being the outer bound
     norm_dist_long = np.random.normal(loc_long, scale, size=size) # normal distribution of longitudes with size being number of moloks and scale being the outer bound
     coords = np.array(list(zip(norm_dist_lat, norm_dist_long))) # zipping lats and long together to a list of tuples

     return coords


def create_distance_matrix(num_moloks:int, coords_array, dtype=np.int64, decimals_if_float=1): # defaults to integer64
    
    start = time.time()

    distance_matrix = np.zeros(shape=(num_moloks + 1, num_moloks + 1), dtype=dtype) # +1 because of the depot at ij = 00. 

    for i in range(len(coords_array)): # række index
        row_length = len(coords_array) # Vi vil kun udregne alle indgange over hoveddiagonalen, så i og 1 trækkes fra til j's range.
        for j in range(i + 1, row_length): # j er søjle-index.
            
            distance = round(decimaldegrees_to_meters(coords_array[i], coords_array[j]), decimals_if_float)

            # spejler indgangene i hoveddiagonalen, så molok A til B er den samme distance som B til A
            distance_matrix[i][j] = distance
            distance_matrix[j][i] = distance
    
    finish = time.time()

    print(f"created distance matrix of size {distance_matrix.shape} in {finish - start} seconds")
    
    return distance_matrix

def molokTimeWindows(fillPcts, estGrowthrates, slack: int):
    """returns list of list of molok time windows to be used in the route planner. they are calculated on a minute basis on form [0, n].
     0 being the 0th minute from starting the route and n being the minute that the molok reaches 100% fill.
     Adding slack will allow moloks to be overfilled by 'slack' seconds"""

    TWs = [0] * len(fillPcts) # time windows list
    
     # solve for x: 100 = a*x + b -> x = (100-b)/a
     # a = growthrate, b= fillPct, and x is seconds
    for i in range(len(fillPcts)):
        x = (100 - fillPcts[i])/estGrowthrates[i]
        if x < 0:           # makes it so the smallest timewindow is [0, 0], meaning instant 100% fillpct
            x = 0
        
        x += slack * 60         # slack is added last

        TWs[i] = [0, int(x)]

    return TWs

if __name__ == '__main__':
    num_moloks = 10

    # simulation variables
    depot_position = (57.04830168757387, 9.915331444926698)
    coord_distance_max = 0.0025016281667760154 # approximately 550 meters in decimaldegrees
    coord_center = depot_position # center of normal distribution of simulation of molok positions
    
    locations = np.array([depot_position])
    locations = np.append(locations, normal_distribution(coord_center[0], coord_center[1], coord_distance_max, num_moloks), axis=0)

    # num_moloks = 2
    # locations = [(45, 10), (45, 11), (44, 10)]
    dist_matrix = create_distance_matrix(num_moloks, locations)

    print(dist_matrix)

    fillPcts = [80, 86, 87, 82]
    growthRates = [0.05, 0.04, 0.035, 0.02]

    print(molokTimeWindows(fillPcts, growthRates, 30))
    