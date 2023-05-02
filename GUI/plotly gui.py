import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import pandas as pd
import json


from DELETEME.datastorage import DataStorage
myDS = DataStorage(69, 1000, ADDR=('127.0.0.1', 12445))
DS_last_rows = myDS.fetch_latest_rows(myDS.table_name, "main")

molok_id=[]; lon=[]; lat=[]; fill_pct=[]; timestamp=[]
for i in DS_last_rows:
    molok_id.append(i[1])
    fill_pct.append(i[3])
    timestamp.append(i[4])

    coords = json.loads(i[2].replace(' ',',', 1))
    lon.append(coords[0])
    lat.append(coords[1])

    #print(molok_id, lon, lat, fill_pct, timestamp)


df = pd.DataFrame(DS_last_rows)
df.columns = ["maxID", "MolokID", "Coords", "Fill_pct", "Timestamp"]


#print("Test shit")
y = df['Coords'].str.replace(' ', ',', 1).str.strip('[ ]')
df[['lat', 'lon']] = y.str.split(',', expand=True)
df = df.drop(columns=["Coords"])
print(df)

exit(0)

fig = px.scatter_mapbox(myDS,
                        lon=df[lon], 
                        lat=lat,
                        hover_data = molok_id,
                        zoom=10, #Starts zoom
                        color=fill_pct,
                        color_continuous_scale=px.colors.diverging.RdYlGn_r,
                        width=1200, height=900, 
                        title='Car share scatter map',
                        )


fig.update_layout(mapbox_style="open-street-map")
#fig.update_layout(margin={"r":0,"t":50,'l':50, 'b':50})
fig.update_layout(
    margin ={'l':0,'t':0,'b':0,'r':0},)


fig.add_trace(go.Scattermapbox(
    mode = "lines",
    hoverinfo= "skip",
    lon = lon,
    lat = lat,
    line = dict(width = 1, color = 'blue'),
    opacity = 0.5))

fig.show()
print("plot complete")
