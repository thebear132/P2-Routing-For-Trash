# https://realpython.com/pysimplegui-python/#getting-started-with-pysimplegui

import PySimpleGUI as sg
sg.theme('DarkBlue3')


map_column = sg.Column(
    [[sg.Graph(key='-graph-', canvas_size=(800, 600), graph_bottom_left=(0, 0), graph_top_right=(400, 400), background_color="black")],
     [sg.Text("Aalborg Satellite map", )]], element_justification="center")

info_column = sg.Column(
    [[sg.Text("Info", justification="center", size=(10, 100))]], element_justification="center")

layout = [
    [map_column, sg.VSeperator(), info_column]
]

# Create the Window
window = sg.Window('Window Title', layout, default_element_size=(12, 1), resizable=True, finalize=True)
window.size = (1300, 700)
window.move_to_center()



while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':
        break
    print('You entered ', values[0])

window.close()
