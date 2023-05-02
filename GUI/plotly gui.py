import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from DELETEME.datastorage import DataStorage
myDS = DataStorage(69, 1000, ADDR=('127.0.0.1', 12445))
latest_rows = myDS.fetch_latest_rows(myDS.table_name, "main")


df = pd.DataFrame(latest_rows[:3])
df.columns = ["maxID", "MolokID", "Coords", "Fill_pct", "Timestamp"]        # Set names of columns

# Remove the Coords[] column and split it into lon and lat, then place into their own columns
y = df['Coords'].str.replace(' ', ',', 1).str.strip('[ ]')
df[['lat', 'lon']] = y.str.split(',', expand=True)
df = df.drop(columns=["Coords"])    # Remove Coords column (useless now)

# Convert column data from string to float or int
df = df.astype('float')
df["MolokID"] = df["MolokID"].astype('int')

print(df)


fig = px.scatter_mapbox(df,
                        title='Route planner',
                        zoom=10, #Starts zoom
                        range_color=[0,120],
                        color_continuous_scale=px.colors.sequential.Blackbody_r,
                        width=1200, height=900,
                        size=[1 for i in range(len(df["lon"]))],
                        opacity=1,
                        size_max=20,
                        hover_name="Molok:" + df["MolokID"].astype(str),
                        color="Fill_pct",
                        lon="lon",
                        lat="lat"
                        )


#fig.update_traces()




#Setting for the maps 
fig.update_layout(mapbox_style="open-street-map", margin ={'l':0,'t':0,'b':50,'r':0})


# Line for one route 
fig.add_trace(go.Scattermapbox(
    mode = "lines",
    hoverinfo= "skip",
    lon = df["lon"],
    lat = df["lat"],
    line = dict(width = 3, color = 'blue'),
    opacity = 0.5))

fig.show()
print("plot complete")
