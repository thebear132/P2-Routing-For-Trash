# https://realpython.com/pysimplegui-python/#getting-started-with-pysimplegui

import PySimpleGUI as sg
sg.theme('DarkBlue3')


map_column = sg.Column(
    [[sg.Graph(key='-graph-', canvas_size=(800, 600), graph_bottom_left=(0, 0), graph_top_right=(400, 400), background_color="black")],
     [sg.Text("VORES MAP SKAL VÆRE HER")]])


layout = [
    [map_column, sg.VSeperator(), sg.Text('Some text on Row 1')]
]

# Create the Window
window = sg.Window('Window Title', layout, finalize=True)
# window.Maximize()
window.size = (1300, 700)
window.move_to_center()
window.move(0, 0)

w,h = window.current_size_accurate()
print(w, h)
print(window.get_screen_size()[0]-w, window.get_screen_size()[1]-h)



while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':
        break
    print('You entered ', values[0])

window.close()
