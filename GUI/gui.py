# https://realpython.com/pysimplegui-python/#getting-started-with-pysimplegui

import PySimpleGUI as sg

sg.theme('DarkBlue3')

map_column = sg.Column([
    [sg.Canvas(key='-graph-', size=(600, 500))],
    [sg.Text("VORES MAP SKAL VÆRE HER")]
    ]
)

layout = [
    [map_column, sg.VSeperator(), sg.Text('Some text on Row 1')]
]

# Create the Window
window = sg.Window('Window Title', layout, finalize=True)
#window.Maximize()
window.size = (1200, 600)


while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel': # if user closes window or clicks cancel
        break
    print('You entered ', values[0])

window.close()

