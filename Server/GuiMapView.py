import tkinter as tk
import tkintermapview
import customtkinter
import gmaps

# create tkinter window
window = tk.Tk()
window.geometry(f"{800}x{600}")
window.title("p2.py")

# create map widget
map_widget = tkintermapview.TkinterMapView(
    window, width=800, height=600, corner_radius=0)
map_widget.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
# creating starting position in Aalborg
map_widget.set_position(57.05, 9.925)
map_widget.set_zoom(13)

# Mouse events on the map


def add_marker_event(coords):
    print("Add marker:", coords)
    new_marker = map_widget.set_marker(coords[0], coords[1], text="new marker")


map_widget.add_right_click_menu_command(label="Add Marker",
                                        command=add_marker_event,
                                        pass_coords=True)

# set a position marker
marker_2 = map_widget.set_marker(57.0509139, 9.9213629)
marker_3 = map_widget.set_marker(57.0574062, 9.9224943)

# # methods
# marker_3.set_position(...)
# marker_3.set_text(...)
# marker_3.change_icon(new_icon)
# marker_3.hide_image(True)  # or False
# marker_3.delete()

# set a path
path_1 = map_widget.set_path(
    [marker_2.position, marker_3.position])


# # methods
# path_1.set_position_list(new_position_list)
# path_1.add_position(position)
# path_1.remove_position(position)
# path_1.delete()


window.mainloop()
