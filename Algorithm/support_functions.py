import numpy as np
import time
import webbrowser
import folium



def create_map(location=(57.04830168757387, 9.915331444926698), zoom_start=17, max_zoom=24) -> object:
    """
    Creates a empty folium.Map object.

    Inputs:
    ---
    - location: A tuple or list of coordinates.
    - zoom_start: The zoom level when created.
    - max_zoom: The max zoom level.
    
    Returns:
    ---
    - map_obj which is a folium.Map object.
    """

    map_obj = folium.Map(location=location, zoom_start=zoom_start, max_zoom=max_zoom)
    
    return map_obj


def create_circles(map_obj:object, number_of_moloks:int, coords:list, radius=1, color='red') -> object:
    """
    Creates circles of a specified radius on the map_obj.
    
    Inputs:
    ---
    - map_obj: A folium object to plot in.
    - number_of_moloks: the number of moloks.
    - coords: The location for the RSSI values to be plotted at.
    - radius: The radius of the circles to be plotted in meters.
    
    Returns:
    ---
    - A map_obj with plotted RSSI values.
    """

    for i in range(number_of_moloks):
            folium.Circle(location=coords[i], radius=radius, fill=True, color=color).add_to(map_obj)

    return map_obj


def save_and_show_map(map_obj:object, name = 'gps_vis') -> None:
    """
    Saves a folium map object in html with a given name.

    Inputs:
    ---
    - map_obj: A folium map object to be saved.
    - name: The name of the html file to be saved.

    Returns:
    ---
    - None
    """
    map_obj.save(f'{name}.html')
    webbrowser.open(f'{name}.html')


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

if __name__ == '__main__':
    num_moloks = 10

    # simulation variables
    depot_position = (57.04830168757387, 9.915331444926698)
    coord_distance_max = 0.0025016281667760154 # approximately 550 meters in decimaldegrees
    coord_center = depot_position # center of normal distribution of simulation of molok positions
    
    locations = np.array([depot_position])
    locations = np.append(locations, normal_distribution(coord_center[0], coord_center[1], coord_distance_max, num_moloks), axis=0)

    dist_matrix = create_distance_matrix(num_moloks, locations)

    print(dist_matrix)
    