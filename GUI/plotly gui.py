"""
Read the user manual here tak https://dash.plotly.com/ 
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
from Simulation import Simulation

b = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
+ '/Algorithm/')
sys.path.append(b)
from routePlanner import MasterPlanner



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
                            color_continuous_scale=px.colors.sequential.Blackbody_r,
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
    return fig
    

# TODO1
#Lav en "plot rute" knap
#Tegn ruterne ved at tegne linjer 

# # Line for one route 
# fig.add_trace(go.Scattermapbox(
#     mode = "lines",
#     hoverinfo= "skip",
#     lon = df["lon"],
#     lat = df["lat"],
#     line = dict(width = 3, color = 'blue'),
#     opacity = 0.5))


app = Dash(__name__)

#style={'width': '50vw', 'height': '100vh', 'margin-right': '50px'}
# Layout consist of every figure, graph and models on the GUI
app.layout = html.Div([
        dcc.Graph(
            id="Map1"),
        
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
                 dcc.Dropdown(id="tableDropdown", options=[1, 2], searchable=True, placeholder="Select table", value="sim_seed435_NumM5", style={"width": "200px"}),
            
            ], style={"display": "flex", "flex-direction": "row", 'width': '40vw'}),
            
            dcc.Markdown("___", style={"margin-top": "20px"}),  # HORIZONTAL LINE DIVIDER
            html.Br(),
            html.Div(id='my-output'),

            html.H2("Start simulation"),
            html.Div(children=[
                
                #IP-address
                dcc.Input(type="text", id="IPTextInput", value="127.0.0.1", style={"width": "100px", "margin-right": "30px"}),

                #Start sim / get sigfox
                html.Button("Start simulation", id='gatherDataButton', style={"width": "100px"}),
                html.Button("Update", id="update", style={"width": "100px"}),

            ], style={"display": "flex", "flex-direction": "row", 'width': '40vw'}),
                dcc.Markdown("___", style={"margin-top": "20px"}),  # HORIZONTAL LINE DIVIDER
                html.Br(),     
                   
            html.H2("Route planner"),
            html.Div(children=[
                
                #Plan route
                html.Button("Plan route", id='planRouteButton', style={"width": "100px"})
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
        tmpDS.create_table(seedText, nrMoloksSlider, typeTable.lower())
        
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
        # TODO 3
        # tmpDS.simThread.join()
    except Exception as e:
        print(e)
    print("Done")
    return blank_fig()
#   startSim(self, ADDR, send_freq: int = 3)





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
    
    return FigCraft(selectedTable)

    
@app.callback(Output("Map1", "figure",allow_duplicate=True),
              Input('planRouteButton', "n_clicks"),
              State('tableDropdown', "value"), prevent_initial_call=True)
def DisplayRoutes(n_clicks, select_table):
    print("@ DisplayRoutes", select_table)
    fig = FigCraft(select_table)


    molok_pos_list = list(zip(fig.data[0]["lat"], fig.data[0]["lon"]))
    
    molok_fillpcts = fig.data[0]['marker']['color']
    
  
    dataS = DataStorage() 
    type, seed, molok = getSeedAndMolok(select_table)
    dataS.select_table(select_table, seed, molok)
    molok_est_data = dataS.lin_reg_sections()
    
    avg_grs = dataS.avg_growth_over_period(molok_est_data, period_start = 0, period_end = 999999999999999)
    avg_grs = avg_grs * 60
    
    num_trucks = 2
    ttem = 5                                            # time to empty molok
    num_moloks = len(molok_pos_list)
    truck_range = 100
    truck_capacity = 3000
    timelimit = 20
    first_solution_strategy = "3"
    local_search_strategy = "3"
    seed = 20
    np.random.seed(seed=seed)

    mp = MasterPlanner(600, 2200, (57.01541, 9.99), molok_pos_list, ttem, molok_fillpcts.tolist(), 500, avg_grs.tolist(),
                       truck_range, num_trucks, truck_capacity, 600, 1400, timelimit,
                       first_solution_strategy, local_search_strategy)

    
    mp.master()

    routes = mp.current_best["routes"]

    print(routes)

    #routes = [['depot', 2, 1, 3, 'depot'], ['depot', 4]]
    for i, route in enumerate(routes):
        Rlat = []
        Rlon = []
        for ii, molok in enumerate(route):
            if molok == "depot":
                route[ii]=0
            Rlat.append(fig.data[0]["lat"][route[ii]])
            Rlon.append(fig.data[0]["lon"][route[ii]])

        fig.add_trace(go.Scattermapbox(
            mode = "lines",
            hoverinfo= "skip",
            name= f"Truck {i}",
            showlegend=True,
            lon = Rlon,
            lat = Rlat,
            line = dict(width = 3)))
    
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)

#fig.show()