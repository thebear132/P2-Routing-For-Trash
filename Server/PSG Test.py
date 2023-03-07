import PySimpleGUI as sg

column = [[sg.Image(filename='D:/tree.png', key='Image')]]
layout = [[sg.Column(column, size=(200, 200), scrollable=True, key='Column')],
          [sg.FileBrowse('Load', enable_events=True)]]
window = sg.Window('test', layout, finalize=True)

while True:

    event, values = window.read()
    print(event, values)
    if event == sg.WINDOW_CLOSED:
        break
    elif event == 'Load':
        filename = values['Load']
        if filename:
            window['Image'].Update(filename=filename)
            # Refresh the update
            window.refresh()
            # Update for scroll area of Column element
            window['Column'].contents_changed()

window.close()