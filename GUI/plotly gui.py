import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import pandas as pd



from DELETEME.datastorage import DataStorage
myDS = DataStorage(69, 1000, ADDR=('127.0.0.1', 12445))
print(myDS.fetch_latest_rows(myDS.table_name, "main"))


print("Getting data...")
df = px.data.carshare()
print(df.head(10))
#print(df.tail(10))

df_10 = df.head(10)

fig = px.scatter_mapbox(df, 
                        lon=df['centroid_lon'], 
                        lat=df['centroid_lat'], 
                        zoom=10, #Starts zoom
                        color= df['peak_hour'],
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
    lon = df_10['centroid_lon'],
    lat = df_10['centroid_lat'],
    line = dict(width = 1, color = 'blue'),
    opacity = 0.5))

fig.show()
print("plot complete")
