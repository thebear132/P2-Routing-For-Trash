"""
Read the user manual here:
https://dash.plotly.com/ 
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
from tqdm import tqdm

import sys, os.path

# Append the Server/ folder to the sys.path in order to grab both datastorage.py and simulation.py
a = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
+ '/Server/')
sys.path.append(a)
from datastorage import DataStorage
#from Simulation import Simulation

b = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
+ '/Algorithm/')
sys.path.append(b)
from routePlanner import MasterPlanner

DEPOT_COORDINATES = (57.0257998,9.9194714)          #depot adress: Over Bækken 2, Aalborg



def getSeedAndMolok(tableName):
    a = tableName.split("_")
    type = a[0]
    seed = int(a[1][4:])
    moloks = int(a[2][4:])
    return type, seed, moloks

def blank_fig():    # A template for an empty figure
    fig = go.Figure(go.Scatter(x=[], y = []))
    fig.update_layout(template = None)
    fig.update_xaxes(showgrid = False, showticklabels = False, zeroline=False)
    fig.update_yaxes(showgrid = False, showticklabels = False, zeroline=False)
    
    return fig


def FigCraft(selectedTable):
    #print(selectedTable, seed, moloks)
    tmpDS = DataStorage()
    tableType, seed, moloks = getSeedAndMolok(selectedTable)
    a = tmpDS.select_table(selectedTable, seed, moloks)
    if a == False:
        #print(f"{selectedTable} does not exist!")
        return blank_fig()


    latest_rows = tmpDS.fetch_latest_rows("main")
    if len(latest_rows) == 0:
        print("[!] THIS TABLE IS EMPTY")
        return blank_fig()
    
    df = pd.DataFrame(latest_rows)
    df.columns = ["maxID", "MolokID", "Coords", "Fill_pct", "Timestamp"]        # Set names of columns

    # Remove the Coords[] column and split it into lon and lat, then place into their own columns
    y = df['Coords'].str.replace(' ', ',', 1).str.strip('[ ]')
    df[['lat', 'lon']] = y.str.split(',', expand=True)
    df = df.drop(columns=["Coords"])    # Remove Coords column (useless now)

    # Convert column data from string to float or int
    df = df.astype('float')
    df["MolokID"] = df["MolokID"].astype('int')

    fig = px.scatter_mapbox(df,
                            title='Route planner',
                            zoom=10, #Starts zoom
                            range_color=[0,100],
                            color_continuous_scale=["LimeGreen", "Gold","Red"], #px.colors.diverging.RdYlGn_r,
                            #width=1280, height=720,
                            size=[1 for i in range(len(df["lon"]))],
                            opacity=1,
                            size_max=20,
                            hover_name="Molok:" + df["MolokID"].astype(str),
                            color="Fill_pct",
                            lon="lon",
                            lat="lat")
    
    # Make map larger in GUI
    fig.update_layout(mapbox_style="open-street-map", margin ={'l':0,'t':0,'b':0,'r':0})
    #Color scale left side
    fig.update_layout(coloraxis_colorbar=dict(yanchor="top", y=1, x=0,
                                          ticks="outside"))
    
    # DEPOT MARKER
    fig.add_trace(go.Scattermapbox(
    mode = "markers",
    lat = [DEPOT_COORDINATES[0]], lon = [DEPOT_COORDINATES[1]],
    marker = {'size': 20, "color": "purple"},
    text = "Depot",textposition = "bottom right", name = "DEPOT"))

    return fig


app = Dash(__name__)

# LAYOUT - consist of every figure, graph and models on the GUI
app.layout = html.Div([
        html.Div([
            
            dcc.Graph(id="Map1", style={'width': '60vw', 'height': '85vh'}),
            dcc.Markdown("", id="routesOutput")
            ]),
        
        
        html.Div([     # HELE VORES SETTINGS SHIT
            html.H2("Create New Table"),
            #SIM Input
            html.Div([
                #slider
                html.Label(html.B("Moloks: ")),
                dcc.Slider(0, 100, 10, value=0, id='nrMoloksSlider'),
                #Radio items
                dcc.RadioItems(["Simulation", "SigFox"], "Simulation", id="radioItems", inline=True, style={"margin-right": "30px","padding": "5px"}),

                #Input (seed)
                html.Label(html.B("Seed: ")),
                dcc.Input(id="seedText", type="text", placeholder="Seed", style={"width": "93px"}),
                
                #Create table nutton
                html.Button("Create table", id='CreateTableButton', style={"width": "100px"})

            ], style={'display' :'flex', 'flex-direction': 'column'}),

            dcc.Markdown("___", style={"margin-top": "20px"}), # HORIZONTAL LINE DIVIDER            
            
            html.H2("Show table"),
            html.Div(children=[
                #Dropdown
                 dcc.Dropdown(id="tableDropdown", searchable=True, placeholder="Select table", value="sim_seed435_NumM5", style={"width": "200px"}),
            
            ], style={"display": "flex", "flex-direction": "row", 'width': '40vw'}),
            
            dcc.Markdown("___", style={"margin-top": "20px"}),  # HORIZONTAL LINE DIVIDER
            #html.Br(),
            html.Div(id='my-output'),

            html.H2("Start simulation"),
            html.Div(children=[
                
                #IP-address
                dcc.Input(type="text", id="IPTextInput", value="192.168.137.234", style={"width": "100px", "margin-right": "30px"}),

                #Start sim / get sigfox
                html.Button("Start simulation", id='gatherDataButton', style={"width": "100px"}),
                html.Button("Update", id="update", style={"width": "100px"}),

            ], style={"display": "flex", "flex-direction": "row", 'width': '40vw'}),
                dcc.Markdown("___", style={"margin-top": "20px"}),  # HORIZONTAL LINE DIVIDER
                #html.Br(),     
                   
            html.H2("Route planner"),
            html.Div(children=[
                
                #Plan route
                html.Button("Plan route", id='planRouteButton', style={"width": "100px", "margin-right": "40px"}),

                #Time limit input
                dcc.Input(type="number", id="timeLimit", placeholder="Time limit", style={"width": "100px"}),
                
                #Number of truck
                dcc.Input(type="text", id="numTrucks", placeholder="Number of trucks", value=5, style={"width": "100px", "margin-top": "10px"}),
                
                #Waste limit pct
                dcc.Input(type = "number", id='filter_pct', placeholder= "Waste limit pct." ),

                #First solution strategy
                dcc.Dropdown(id="fssDropdown", searchable=True, placeholder="First solution strategy", value=1, options=[1, 2, 3], style={"width": "100px","margin-top": "5px"}),

                #Local solution strategy 
                dcc.Dropdown(id="lssDropdown", searchable=True, placeholder="Local search strategy", value=1, options=[1, 2, 3, 4], style={"width": "100px","margin-top": "5px"}),
                
        
                          

                ])

        ])
        
       ], style={'display' :'flex', 'flex-direction': 'row'})


# CREATE TABLE
@app.callback(
        Output('tableDropdown', "options"),
        Input('CreateTableButton', 'n_clicks'),
        State('nrMoloksSlider', 'value'),
        State('seedText', 'value'),
        State('radioItems', 'value'))
def callCreateTable(n_clicksButton, nrMoloksSlider, seedText, typeTable):
    print("@ CALL_CREATE_TABLE() |", n_clicksButton, nrMoloksSlider, seedText, typeTable)
    
    tmpDS = DataStorage(center_coordinates=(57.0336483, 9.9261796), scale=0.05)
    typeTable = typeTable.lower()
        
    if n_clicksButton != None:
        if 'sim' in typeTable: typeTable = 'sim'
        tmpDS.create_table(int(seedText), nrMoloksSlider, typeTable.lower())
        
    return tmpDS.get_tablenames()



#Starts a simulation from the selected table
@app.callback(Output("Map1", "figure", allow_duplicate=True),
              Input('gatherDataButton', "n_clicks"),
              State('tableDropdown', "value"),
              State('IPTextInput', "value"), prevent_initial_call=True)
def StartSim(nrOfClicks, selectTable, IP):
    if selectTable == None:
        return blank_fig()
    
    try:
        tmpDS = DataStorage()
        tableType, seed, molok = getSeedAndMolok(selectTable)
        tmpDS.select_table(selectTable, seed, molok)
        tmpDS.startSim((IP, 12445))
        # tmpDS.simThread.join()
    except Exception as e:
        print(e)
    tmpDS.join_sim_thread()
    return FigCraft(selectTable)


#Button for updates 
@app.callback(Output("Map1","figure", allow_duplicate=True),
              Input("update", "n_clicks"),
              State('tableDropdown', "value"), prevent_initial_call=True)
def update_map(n_clicks,select_table):
    #print("update button !!!!!")
    return FigCraft(select_table)



#Updates Scatter-map when table is selected from dropdown
@app.callback(Output("Map1", "figure"),
              Input('tableDropdown', "value"))
def Callupdate_scatterMap(selectedTable):
    print("\n@ Callupdate_scatterMap()")
    # When intitial request (meaning selectedTable is None), return the first table in Database
    if selectedTable == None: return blank_fig()
    fig = FigCraft(selectedTable)
    return fig

    

# ______PLOT ROUTES______
@app.callback(Output("Map1", "figure", allow_duplicate=True),
            Output("routesOutput", "children"),
            Input('planRouteButton', "n_clicks"),
            State('tableDropdown', "value"),
            State('timeLimit', "value"),
            State('numTrucks', "value"),
            State('fssDropdown', "value"),
            State('lssDropdown', "value"),
            State('filter_pct', "value"),
            prevent_initial_call=True)
def DisplayRoutes(n_clicks, select_table, timeLimit, numTrucks, fss, lss, waste_limit):
    print("@ DisplayRoutes", select_table, timeLimit, numTrucks, fss, lss, waste_limit)
    fig = FigCraft(select_table)

    molok_pos_list = list(zip(fig.data[0]["lat"], fig.data[0]["lon"]))
    molok_fillpcts = fig.data[0]['marker']['color']
    
    dataS = DataStorage() 
    tableType, seed, molok = getSeedAndMolok(select_table)
    dataS.select_table(select_table, seed, molok)
    molok_est_data = dataS.lin_reg_sections()
    
    avg_grs = dataS.avg_growth_over_period(molok_est_data, period_start = 0, period_end = 999999999999999)  #lol
    #FILTER (only include if Fill Pct over 40)
    filteredMoloks = [id for id in range(len(molok_pos_list)) if molok_fillpcts[id] >= waste_limit]
    print("Filtered moloks ->", filteredMoloks)

    # Error handling
    if len(filteredMoloks) == 0:
        return fig, "Ingen valide molokker"
    if type(avg_grs) == str:
        return fig, "Not enough measurements! (Minimum of 2 required to perform linear regression)"
    
    #Apply filter to other lists
    molok_pos_list = [molok_pos_list[i] for i in filteredMoloks]
    molok_fillpcts = [molok_fillpcts[i] for i in filteredMoloks]
    avg_grs        = [avg_grs[i]        for i in filteredMoloks]
    
    
    ttem = 5                #Time it takes to empty molok
    truck_range = 100
    truck_capacity = 3000
    numberOfAttempts = 10
    MaximumSlack = 30
    print("Creating MasterPlanner object")
    mp = MasterPlanner(600, 2200, molok_pos_list, ttem, molok_fillpcts, 500, avg_grs, truck_range, numTrucks, truck_capacity, 600, 1400, timeLimit, first_solution_strategy=str(fss), local_search_strategy=str(lss), num_attempts=numberOfAttempts, max_slack=MaximumSlack)
        
    print("[!] Planning routes -> ", end="")
    sys.stdout = open(os.devnull, 'w')      #Disable print()
    mp.master()
    #print(mp.rp.data)
    routes = mp.current_best["routes"]
    sys.stdout = sys.__stdout__             #Enable print()
    print(routes)
    print(mp.empty_molok_times)
    
    emptiedMoloks = mp.empty_molok_times
    
    #Empty moloks + converting
    emptyMoloks_C = []
    for i in emptiedMoloks:     # [(1, 234), (3, 4123)]
        emptyMoloks_C.append((filteredMoloks[i[0]], 1))       
    
    #Get max() epoch time
    latest_rows_data = dataS.fetch_latest_rows("main")
    
    max_epoch_time = max(list(zip(*latest_rows_data))[4])
    dataS.set_fillpcts_to_0(emptyMoloks_C, float(max_epoch_time))

    # Create converted routes for GUI
    convertedRoutes = []    
    for route in routes:
        c_route = []
        for molok in route:
            if molok == "depot":
                c_route.append("depot")
            else:
                c_route.append(filteredMoloks[molok])
        convertedRoutes.append(c_route)
    #print("ConvertedRoutes", convertedRoutes)



    

    routeFormattedOutput = ""
    for i, route in enumerate(convertedRoutes):
        routeFormattedOutput += f"**Truck {i}** | "
        for place in route:
            routeFormattedOutput +=  " --> " + str(place)
        routeFormattedOutput += "  \n"

    
    # ADD ROUTE TRACES
    for i, route in enumerate(routes):
        Rlat = []
        Rlon = []
        for ii, molok in enumerate(route):
            if molok == "depot":
                Rlat.append(DEPOT_COORDINATES[0])
                Rlon.append(DEPOT_COORDINATES[1])
            else:
                Rlat.append(molok_pos_list[route[ii]][0])
                Rlon.append(molok_pos_list[route[ii]][1])
        
        #Add routes as lines
        fig.add_trace(go.Scattermapbox(
            mode = "lines",
            hoverinfo= "skip",
            name= f"Truck {i}",
            showlegend=True,
            lon = Rlon,
            lat = Rlat,
            line = {"width" : 3}))
    


    return fig, routeFormattedOutput


if __name__ == "__main__":
    app.run_server(debug=True)

#fig.show()