import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
from tqdm import tqdm


from DELETEME.datastorage import DataStorage
from DELETEME.Simulation import Simulation


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


def plot_sim(selectedTable):
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
                            #size=[1 for i in range(len(df["lon"]))],
                            opacity=1,
                            size_max=5,
                            hover_name="Molok:" + df["MolokID"].astype(str),
                            color="Fill_pct",
                            lon="lon",
                            lat="lat",
                            mapbox_style="open-street-map")

    
    # Make map larger in GUI
    fig.update_layout(margin ={'l':0,'t':0,'b':0,'r':0})
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

# TODO2
# Start en simulation (start Simulation.py og dataStorage.py og få data)
# Plot molokkerne igen med deres nye fill_pct's (de burde være gået op nu)

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
                dcc.Slider(0, 1000, 200, value=500, id='nrMoloksSlider'),
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
                 dcc.Dropdown(id="tableDropdown", options=[1, 2], searchable=True, placeholder="Select table", style={"width": "200px"}),
            
            ], style={"display": "flex", "flex-direction": "row", 'width': '40vw'}),
            
            dcc.Markdown("___", style={"margin-top": "20px"}),  # HORIZONTAL LINE DIVIDER
            html.Br(),
            html.Div(id='my-output'),

            html.H2("Start simulation"),
            html.Div(children=[
                
                #IP-address
                dcc.Input(type="text", id="IPTextInput", value="127.0.0.1", style={"width": "70px", "margin-right": "30px"}),

                #Start sim / get sigfox
                html.Button("Start simulation", id='gatherDataButton', style={"width": "100px"}),

            
            ], style={"display": "flex", "flex-direction": "row", 'width': '40vw'}),
            
            dcc.Markdown("___", style={"margin-top": "20px"}),  # HORIZONTAL LINE DIVIDER
            html.Br(),
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
    #print("@ CALL_CREATE_TABLE() |", n_clicksButton, nrMoloksSlider, seedText, typeTable)
    
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
    print("hej hej hejeh ejeh eh")
    tmpDS = DataStorage()
    tableType, seed, molok = getSeedAndMolok(selectTable)
    tmpDS.select_table(selectTable, seed, molok)
    sim = Simulation()


    return blank_fig()

#   def simulate(self, seed, fill_pct, sendHyp, time_stamps):

#Updates Scatter-map when table is selected from dropdown
@app.callback(Output("Map1", "figure"),
              Input('tableDropdown', "value"))
def Callupdate_scatterMap(selectedTable):
    print("\n@ Callupdate_scatterMap()")
    
    # When intitial request (meaning selectedTable is None), return a blank figure
    if selectedTable == None: return blank_fig()

    return plot_sim(selectedTable)

    


if __name__ == "__main__":
    app.run_server(debug=True)


#fig.show()