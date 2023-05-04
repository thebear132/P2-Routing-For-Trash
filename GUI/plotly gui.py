import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State


from DELETEME.datastorage import DataStorage
myDS = DataStorage(69, 1000, ADDR=('127.0.0.1', 12445))
latest_rows = myDS.fetch_latest_rows(myDS.table_name, "main")
tableNames = myDS.get_tablenames()
del myDS

df = pd.DataFrame(latest_rows[:3])
df.columns = ["maxID", "MolokID", "Coords", "Fill_pct", "Timestamp"]        # Set names of columns

# Remove the Coords[] column and split it into lon and lat, then place into their own columns
y = df['Coords'].str.replace(' ', ',', 1).str.strip('[ ]')
df[['lat', 'lon']] = y.str.split(',', expand=True)
df = df.drop(columns=["Coords"])    # Remove Coords column (useless now)

# Convert column data from string to float or int
df = df.astype('float')
df["MolokID"] = df["MolokID"].astype('int')

#print(df)



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
                        lat="lat"
                        )



#Setting for the maps 
fig.update_layout(mapbox_style="open-street-map", margin ={'l':0,'t':0,'b':0,'r':0})



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



# Layout consist of every figure, graph and models on the GUI
app.layout = html.Div([
        dcc.Graph(
        id="Map",
        figure=fig,
        style={'width': '50vw', 'height': '100vh', 'margin-right': '50px'}
        ),
        
        html.Div(children=[     # HELE VORES SETTINGS SHIT
            
            html.H2("Create New Table"),
            #SIM Input
            html.Div([
                #slider
                html.Label(html.B("Moloks: ")),
                dcc.Slider(0, 1000, 100,
                    value=1000,
                    id='nrMoloksSlider'),
                
                #Input (seed)
                html.Label(html.B("Seed: ")),
                dcc.Input(id="seedText", type="text", placeholder="Seed", style={"width": "80px"}),
                
                #Dogshit button
                html.Button("Create table", id='CreateTableButton', style={"width": "100px"})

            ], style={'display' :'flex', 'flex-direction': 'column'}),

            dcc.Markdown("___", style={"margin-top": "20px"}), # HORIZONTAL LINE DIVIDER            

            
            html.H2("Mode"),
            html.Div([
                #Radio items
                dcc.RadioItems(["Simulation", "SigFox"], "Simulation", id="radioItems", inline=True, style={"margin-right": "30px","padding": "5px"}),

                #IP-address
                dcc.Input(type="text", value="127.0.0.1", style={"width": "70px", "margin-right": "30px"}),

                #Dropdown
                dcc.Dropdown(tableNames, id="tableDropdown", searchable=True, placeholder="Select table", style={"width": "200px"})
            
            ], style={"display": "flex", "flex-direction": "row", 'width': '40vw'}),
            
            dcc.Markdown("___", style={"margin-top": "20px"}),  # HORIZONTAL LINE DIVIDER

            

            html.Br(),
            html.Div(id='my-output'),
        ])
        
        ], style={'display' :'flex', 'flex-direction': 'row'})


@app.callback(
        Output('tableDropdown', "children"),
        Input('CreateTableButton', 'n_clicks'),
        State('nrMoloksSlider', 'value'),
        State('seedText', 'value'))
def callCreateTable(buttonSubmit, nrMoloksSlider, seedText):
    print(nrMoloksSlider, seedText)
    if seedText != None:
        print("Trying to create table")
        temporaryDS = DataStorage(int(seedText), int(nrMoloksSlider))
        print(f"Creating table with {nrMoloksSlider} moloks and seed {seedText}")
    else: print("seed var None, noob")
    tableNames = temporaryDS.get_tablenames()
    del temporaryDS
    return tableNames
    
""""
@app.callback(
    Output('my-output', "children"),
    Input('radioItems', 'value'))
def callSim_or_sigfox(selection):
    return selection
"""



def Callupdate_scatterMap(Updater):
    return Updater












if __name__ == "__main__":
    app.run_server(debug=True)


#fig.show()