import csv
import itertools
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.datatables import MDDataTable
from kivy.metrics import dp
from plyer import filechooser
from kivy.uix.label import Label
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.button import MDRaisedButton
import os
from kivymd.uix.textfield import MDTextField
from PIL import Image, ImageDraw, ImageFont
import nfc
from jnius import autoclass, cast

# Dynamically load Android classes
Intent = autoclass('android.content.Intent')
Activity = autoclass('android.app.Activity')
NfcAdapter = autoclass('android.nfc.NfcAdapter')
NdefRecord = autoclass('android.nfc.NdefRecord')
NdefMessage = autoclass('android.nfc.NdefMessage')

#change color of the filechooser
Builder.load_string('''

<FileChooserListView>:
    # --------------------
    # ADD BACKGROUND COLOR
    # --------------------
    canvas.before:
        Color:
            rgb: 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size
    layout: layout
    FileChooserListLayout:
        id: layout
        controller: root

[FileListEntry@FloatLayout+TreeViewNode]:
    locked: False
    entries: []
    path: ctx.path
    # FIXME: is_selected is actually a read_only treeview property. In this
    # case, however, we're doing this because treeview only has single-selection
    # hardcoded in it. The fix to this would be to update treeview to allow
    # multiple selection.
    is_selected: self.path in ctx.controller().selection

    orientation: 'horizontal'
    size_hint_y: None
    height: '48dp' if dp(1) > 1 else '24dp'
    # Don't allow expansion of the ../ node
    is_leaf: not ctx.isdir or ctx.name.endswith('..' + ctx.sep) or self.locked
    on_touch_down: self.collide_point(*args[1].pos) and ctx.controller().entry_touched(self, args[1])
    on_touch_up: self.collide_point(*args[1].pos) and ctx.controller().entry_released(self, args[1])
    BoxLayout:
        pos: root.pos
        size_hint_x: None
        width: root.width - dp(10)
        Label:
            # --------------
            # CHANGE FONT COLOR
            # --------------
            color: 0, 0, 0, 1
            id: filename
            text_size: self.width, None
            halign: 'left'
            shorten: True
            text: ctx.name
        Label:
            # --------------
            # CHANGE FONT COLOR
            # --------------
            color: 0, 0, 0, 1
            text_size: self.width, None
            size_hint_x: None
            halign: 'right'
            text: '{}'.format(ctx.get_nice_size())


<MyWidget>:
    FileChooserListView
''')

# Define Screens
class HomeScreen(Screen):
    pass

class SavedCardsScreen(Screen):
    pass

class ManageDataScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass

class MainApp(MDApp):
    dialog = None  # Store the dialog instance

    def build(self):
        # Load the KV file
        root = Builder.load_file("layout.kv")

        # Dynamically set the rootpath for the FileChooserListView
        saved_cards_screen = root.ids.screen_manager.get_screen("saved_cards")
        csv_directory = os.path.join(os.path.dirname(__file__), "assets", "CSV")
        if not os.path.exists(csv_directory):
            os.makedirs(csv_directory)  # Create the directory if it doesn't exist
        saved_cards_screen.ids.filechooser.rootpath = csv_directory

        return root
    
    global show_lead, show_range, show_2_wind_holds
    show_lead = False
    show_range = False
    show_2_wind_holds = True

   
    def on_file_selected(self, selection):
        """Handle the file or folder selected in the FileChooserListView."""
        if selection:
            selected_path = selection[0]
            # Extract the file name and set it to the stage_name_field
            file_name = os.path.basename(selected_path)
            self.root.ids.home_screen.ids.stage_name_field.text = os.path.splitext(file_name)[0]
            # If the selected file is a CSV, extract the stage notes footer and display it in the stage_notes_field
            if selected_path.endswith(".csv"):
                try:
                    with open(selected_path, mode="r", encoding="utf-8") as csv_file:
                        lines = csv_file.readlines()
                        # Look for the "Stage Notes:" footer and extract the notes
                        for i, line in enumerate(lines):
                            if line.strip().lower() == "stage notes:":
                                stage_notes = "".join(lines[i + 1:]).strip()
                                self.root.ids.home_screen.ids.stage_notes_field.text = stage_notes
                                break
                except Exception as e:
                    print(f"Error extracting stage notes: {e}")
            print(f"Selected: {selected_path}")  # Log the selected file or folder

            # Check if the selected file is a CSV
            if selected_path.endswith(".csv"):
                try:
                    # Read the CSV file and convert it to a dictionary
                    data = self.read_csv_to_dict(selected_path)
                    self.current_data = data  # Store the data for filtering or other operations

                    # Display the data as a table on the Home Screen
                    self.display_table(data)

                    # Reset the FileChooserListView to its rootpath
                    saved_cards_screen = self.root.ids.screen_manager.get_screen("saved_cards")
                    filechooser = saved_cards_screen.ids.filechooser
                    filechooser.path = filechooser.rootpath  # Reset to rootpath

                    # Navigate back to the Home Screen
                    self.root.ids.screen_manager.current = "home"  # Reference the Home Screen by its name in layout.kv

                    print(f"CSV loaded: {os.path.basename(selected_path)}")
                except Exception as e:
                    print(f"Error reading CSV: {e}")
            else:
                print("Please select a valid CSV file.")
        else:
            print("No file selected")

    def read_csv_to_dict(self, file_path):
        """Reads a CSV file and maps it to static column names, ignoring the headers and skipping the first 4 lines."""
        static_columns = ["Target", "Range", "Elv", "Wnd1", "Wnd2", "Lead"]  # Static column names
        data = []
        try:
            with open(file_path, mode="r", encoding="utf-8") as csv_file:
                reader = csv.reader(csv_file)  # Use csv.reader to read the file
                # Skip the first 4 lines
                for _ in range(6):
                    next(reader, None)
                for index, row in enumerate(reader, start=1):
                    # Skip empty rows
                    if not row:
                        continue

                    # Skip footer if it exists (e.g., rows starting with "Stage Notes:")
                    if row[0].strip().lower() == "stage notes:":
                        break
                    if not row:
                        continue

                    # Map the row to the static column names
                    mapped_row = {static_columns[i]: row[i] if i < len(row) else "" for i in range(len(static_columns))}
                    data.append(mapped_row)
        except Exception as e:
            print(f"Error reading CSV file: {e}")

        return data

    def display_table(self, data):
        """Displays the filtered CSV data as text on the Home Screen."""
        if not data:
            print("No data to display.")
            return

        # Define the static column order
        static_headers = ["Target", "Range", "Elv", "Wnd1", "Wnd2", "Lead"]

        # Filter headers based on the show/hide options
        headers = ["Target", "Elv", "Wnd1"]  # Always include these columns
        if show_range:
            headers.insert(1, "Range")  # Insert "Range" after "Target" and before "Elv"
        if show_2_wind_holds:
            headers.append("Wnd2")
        if show_lead:
            headers.append("Lead")

        # Filter the data rows based on the selected headers
        filtered_data = [
            {header: row.get(header, "") for header in headers} for row in data
        ]

        # Calculate the maximum width for each column
        column_widths = {header: len(header) for header in headers}  # Start with header lengths
        for row in filtered_data:
            for header in headers:
                column_widths[header] = max(column_widths[header], len(str(row.get(header, ""))))

        # Format the headers and rows as text
        table_text = " | ".join(f"{header:<{column_widths[header]}}" for header in headers) + "\n"  # Add headers
        table_text += "-" * (sum(column_widths.values()) + len(headers) * 3 - 1) + "\n"  # Add a separator line
        for row in filtered_data:
            table_text += " | ".join(f"{str(row.get(header, '')):<{column_widths[header]}}" for header in headers) + "\n"  # Add rows

        # Add the text to the table_container in Home Screen
        home_screen = self.root.ids.home_screen
        table_container = home_screen.ids.table_container
        table_container.clear_widgets()  # Clear any existing widgets in the container

        # Create a Label to display the table text
        table_label = Label(
            text=table_text,
            halign="center",
            valign="center",
            size_hint=(1, 1),
            text_size=(table_container.width, None),
            color=(0, 0, 0, 1),  # Set text color to black
            font_name="assets/fonts/RobotoMono-Regular.ttf",  # Path to the font file
        )
        table_container.add_widget(table_label)
        
    def on_dots_press(self, instance):
        global show_lead, show_range, show_2_wind_holds

        # Dismiss the existing menu if it exists
        if hasattr(self, "menu") and self.menu:
            self.menu.dismiss()

        # Update the "Show Lead" menu item dynamically
        if show_lead:
            lead_menu = {"text": "Hide Lead", "on_release": lambda: self.menu_callback("Hide Lead")}
        else:
            lead_menu = {"text": "Show Lead", "on_release": lambda: self.menu_callback("Show Lead")}
        # Update the "Show Range" menu item dynamically
        if show_range:
            range_menu = {"text": "Hide Range", "on_release": lambda: self.menu_callback("Hide Range")}
        else:
            range_menu = {"text": "Show Range", "on_release": lambda: self.menu_callback("Show Range")}
        # Update the "Show 2 Wind Holds" menu item dynamically
        if show_2_wind_holds:
            wind_holds_menu = {"text": "Show 1 Wind Hold", "on_release": lambda: self.menu_callback("Show 1 Wind Hold")}
        else:
            wind_holds_menu = {"text": "Show 2 Wind Holds", "on_release": lambda: self.menu_callback("Show 2 Wind Holds")}

        # Define menu items
        menu_items = [
            {"text": "Settings", "on_release": lambda: self.menu_callback("Settings")},
            lead_menu,
            range_menu,
            wind_holds_menu,
        ]

        # Create the dropdown menu
        self.menu = MDDropdownMenu(
            caller=instance,
            items=menu_items,
            width_mult=4,
        )
        self.menu.open()

    def menu_callback(self, option):
        global show_lead, show_range, show_2_wind_holds

        # Handle the selected option
        if option == "Hide Lead":
            show_lead = False
        elif option == "Show Lead":
            show_lead = True
        if option == "Hide Range":
            show_range = False
        elif option == "Show Range":
            show_range = True
        if option == "Show 1 Wind Hold":
            show_2_wind_holds = False
        elif option == "Show 2 Wind Holds":
            show_2_wind_holds = True
        elif option == "Settings":
            # Navigate to the settings screen
            self.root.ids.screen_manager.current = "settings"

            # Close the dots menu
            if hasattr(self, "menu") and self.menu:
                self.menu.dismiss()

        # Regenerate the table with updated columns
        if hasattr(self, "current_data"):  # Check if data is already loaded
            filtered_data = self.filter_table_data(self.current_data)
            self.display_table(filtered_data)

    def filter_table_data(self, data):
        """Filters the table data based on the show_lead and show_2_wind_holds flags."""
        filtered_data = []
        for row in data:
            filtered_row = {}
            # Add columns in the static order
            filtered_row["Target"] = row.get("Target", "")
            if show_range:
                filtered_row["Range"] = row.get("Range", "")
            filtered_row["Elv"] = row.get("Elv", "")
            filtered_row["Wnd1"] = row.get("Wnd1", "")
            if show_2_wind_holds:
                filtered_row["Wnd2"] = row.get("Wnd2", "")
            if show_lead:
                filtered_row["Lead"] = row.get("Lead", "")
            filtered_data.append(filtered_row)
        return filtered_data

    def on_fab_press(self):
        """Handle the floating action button press."""
              # Create the dialog if it doesn't already exist
        if not self.dialog:
               # Get the list of folders in the assets/CSV directory
            csv_directory = os.path.join(os.path.dirname(__file__), "assets", "CSV")
            folders = [f for f in os.listdir(csv_directory) if os.path.isdir(os.path.join(csv_directory, f))]

            # Create the dropdown menu
            self.dialog = MDDialog(
                title="Save Data",
                text="Do you want to save the current data?",
                type="custom",
                content_cls=MDFlatButton(
                    id="dropdown_button",
                    text="Select Event",
                    size_hint=(1, None),
                    height="48dp",
                    on_release=lambda x: MDDropdownMenu(
                        # Create a dropdown menu with the list of folders
                        # and a "New Event..." option
                        caller=x,
                        items=[
                             {
                                "text": "New Event...",
                                "on_release": lambda: (
                                    # Update the text input visibility based on the selected option
                                    update_text_input_visibility("New Event..."),
                                    setattr(self.dialog.content_cls, "text", "New Event..."),
                                    print("New Event selected"),
                                ),
                            }
                        ] + [
                            {
                                "text": folder,
                                "on_release": lambda selected_folder=folder: (
                                    # Update the text input visibility based on the selected folder
                                    update_text_input_visibility(selected_folder),
                                    setattr(self.dialog.content_cls, "text", f"{selected_folder}"),
                                    # Store the selected folder
                                    setattr(self, "selected_folder", selected_folder),
                                    # Update the save path to include the selected folder
                                    setattr(self, "save_path", os.path.join(csv_directory, selected_folder)),
                                    print(f"Selected folder: {selected_folder}")
                                ),
                            }
                            for folder in folders
                        ],
                        width_mult=4,  # Adjust width_mult to match the button width
                        position="center",
                    ).open(),
                    pos_hint={"center_x": 0, "center_y": 1},
                    halign="center",
                    valign="center",
                ),
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_release=lambda x: self.dialog.dismiss()
                    ),
                    MDRaisedButton(
                        text="SAVE",
                        on_release=lambda x: (
                            self.save_data(),  # Save data when the SAVE button is pressed
                        )
                    ),
                ],
            )

            # Add a text input field to the dialog, initially hidden
            text_input = MDTextField(
                hint_text="Event Name",
                size_hint=(1, None),
                height="48dp",
                multiline=False,
                opacity=0,  # Make it invisible initially
                disabled=True,  # Disable it initially
            )

            # Update visibility based on the selected option
            def update_text_input_visibility(selected_option):
                if selected_option == "New Event...":
                    text_input.opacity = 1  # Make it visible
                    text_input.disabled = False  # Enable it
                else:
                    text_input.opacity = 0  # Hide it
                    text_input.disabled = True  # Disable it
            self.dialog.content_cls.add_widget(text_input)
            
        self.dialog.open()

    def save_data(self, *args):
        # Add your save logic here
        print("Data saved!")
        self.dialog.dismiss()
          # Save the stage name
        stage_name_field = self.root.ids.home_screen.ids.stage_name_field
        global stage_name
        stage_name = stage_name_field.text

        # Save the stage notes
        stage_notes_field = self.root.ids.home_screen.ids.stage_notes_field
        global stage_notes
        stage_notes = stage_notes_field.text

        # Add the stage notes as a footer to the CSV
        if hasattr(self, "current_data") and self.current_data:
            csv_directory = os.path.join(os.path.dirname(__file__), "assets", "CSV", self.selected_folder if hasattr(self, "selected_folder") else "")
            file_path = os.path.join(csv_directory, f"{stage_name}.csv")
            try:
                with open(file_path, mode="w", encoding="utf-8", newline="") as csv_file:
                    writer = csv.writer(csv_file)

                    # Write the headers
                    writer.writerow(["Kestrel Ballistics"])
                    writer.writerow([])
                    writer.writerow(["Gun Profile:"])
                    writer.writerow([])
                    writer.writerow(["Temp: 22 C", "Pressure: 29.63 inHg", "RH: 79%", "Range Unit: Meters", "Hold Unit: MILS", "Wind Speed Unit: MPH", "Target Speed Unit: MPH"])
                    headers = self.current_data[0].keys()
                    writer.writerow(headers)

                    # Write the data rows
                    for row in self.current_data:
                        writer.writerow(row.values())

                    # Add the stage notes as a footer
                    writer.writerow([])
                    writer.writerow(["Stage Notes:"])
                    writer.writerow([stage_notes])

            except Exception as e:
                print(f"Error displaying stage notes: {e}")
           
            try:
                # If data rows exist, display the stage notes in the text input
                if hasattr(self, "current_data") and self.current_data:
                    self.root.ids.home_screen.ids.stage_notes_field.text = stage_notes

                    print(f"Data saved to {file_path} with stage notes as footer.")
            
            except Exception as e:
                print(f"Error saving data to CSV: {e}")

    def csv_to_bitmap(self, csv_data, output_path="output.bmp"):
        """Convert CSV data to a bitmap image."""
        try:
            # Define image dimensions and font
            image_width = 240  # Width of the image
            image_height = 416  # Height of the image

            # Load the font file (ensure the font file is in the correct path)
            font_path = os.path.join(os.path.dirname(__file__), "assets", "fonts", "RobotoMono-Regular.ttf")
            font = ImageFont.truetype(font_path, 12)  # Load the font file

            # Create a blank white image
            image = Image.new("RGB", (image_width, image_height), "white")
            draw = ImageDraw.Draw(image)

            # Add the stage name at the top
            stage_name = self.root.ids.home_screen.ids.stage_name_field.text  # Get the stage name from the text field
            x, y = 10, 10  # Starting position for the stage name
            text_bbox = draw.textbbox((0, 0), stage_name, font=font)  # Get the bounding box of the text
            text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
            x = (image_width - text_width) // 2  # Center the text horizontally
            draw.text((x, y), f"{stage_name}", fill="black", font=font)
            # Draw a horizontal line under the stage name
            y += 20  # Add some spacing after the stage name
            draw.line((10, y, image_width - 10, y), fill="black", width=1)
            y += 20  # Add some spacing after the line

            # Calculate column widths based on the data
            filtered_data = self.filter_table_data(csv_data)
            column_widths = {header: len("Tgt" if header == "Target" else header) for header in filtered_data[0].keys()}  # Start with header lengths
            for row in filtered_data:
                for header, value in row.items():
                    column_widths[header] = max(column_widths[header], len(str(value)))

            # Write headers to the image
            headers = " | ".join(f"{'Tgt' if header == 'Target' else header:<{column_widths[header]}}" for header in filtered_data[0].keys())
            draw.text((10, y), headers, fill="black", font=font)
            y += 20  # Move to the next line

            # Write CSV data to the image
            for row in filtered_data:
                row_text = " | ".join(f"{str(value):<{column_widths[header]}}" for header, value in row.items())
                draw.text((10, y), row_text, fill="black", font=font)
                y += 20  # Move to the next line

            # Add the stage notes below the table data
            stage_notes = self.root.ids.home_screen.ids.stage_notes_field.text  # Get the stage notes from the text field
            y += 20  # Add some spacing before the stage notes
            draw.line((10, y, image_width - 10, y), fill="black", width=1)  # Draw a line above the stage notes
            y += 10  # Add some spacing after the line
            text_bbox = draw.textbbox((0, 0), "Stage Notes:", font=font)  # Get the bounding box of the text
            text_height = text_bbox[3] - text_bbox[1]  # Calculate the text height
            y_center = y + ((6 - text_height) // 2)  # Center the text vertically between the lines
            text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
            x = (image_width - text_width) // 2  # Center the text horizontally
            draw.text((x, y_center), f"Stage Notes:", fill="black", font=font)
            y += 20  # Add some spacing after the stage notes label
            draw.line((10, y, image_width - 10, y), fill="black", width=1)  # Draw a line below the stage notes
            y += 10  # Add some spacing after the line
            # Draw the stage notes text
            x, y = 10, y  # Starting position for the stage notes
            text_bbox = draw.textbbox((0, 0), stage_notes, font=font)  # Get the bounding box of the text
            text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
            x = (image_width - text_width) // 2  # Center the text horizontally
            draw.text((x, y), f"{stage_notes}", fill="black", font=font)
            y += 20  # Add some spacing after the stage notes

            # Save the image as a bitmap
            image.save(output_path)
            print(f"Bitmap saved to {output_path}")
            return output_path
        except Exception as e:
            print(f"Error converting CSV to bitmap: {e}")
            return None

    def send_bitmap_via_nfc(self, bitmap_path):
        """Send the bitmap image via NFC using pyjnius."""
        try:
            # Load the bitmap data
            with open(bitmap_path, "rb") as f:
                data = f.read()

            # Get the current Android activity and NFC adapter
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            nfc_adapter = NfcAdapter.getDefaultAdapter(activity)

            if not nfc_adapter:
                print("NFC is not available on this device.")
                return

            # Create an NDEF record with the bitmap data
            ndef_record = NdefRecord.createMime("application/octet-stream", data)

            # Create an NDEF message
            ndef_message = NdefMessage([ndef_record])

            # Set the NDEF message to be sent via NFC
            nfc_adapter.setNdefPushMessage(ndef_message, activity)
            print("Bitmap prepared for NFC transfer. Bring the device close to an NFC tag or another NFC-enabled device.")

        except Exception as e:
            print(f"Error sending bitmap via NFC: {e}")

    def on_send_via_nfc(self):
        """Convert CSV to bitmap and send it via NFC."""
        if hasattr(self, "current_data") and self.current_data:
            # Convert CSV data to bitmap
            bitmap_path = self.csv_to_bitmap(self.current_data)
            if bitmap_path:
                # Send the bitmap via NFC
                self.send_bitmap_via_nfc(bitmap_path)
        else:
            print("No CSV data loaded to send.")

    def navigate_to_home(self):
        """Navigate back to the home screen."""
        self.root.ids.screen_manager.current = "home"

# search functionality below
    def on_search_entered(self, search_text):
        """Filter the FileChooserListView based on the search input."""
        try:
            filechooser = self.root.ids.saved_cards_screen.ids.filechooser
            if search_text:
                # Update the filter to match files containing the search text
                filechooser.filters = [lambda folder, filename: search_text.lower() in filename.lower()]
            else:
                # Reset the filter to show all files
                filechooser.filters = []
        except Exception as e:
            print(f"Error in search functionality: {e}")
    
    def limit_stage_notes(self, text_field):
        """Limit the stage notes to 2 lines."""
        max_lines = 2
        lines = text_field.text.split("\n")
        if len(lines) > max_lines:
            # Trim the text to the first 2 lines
            text_field.text = "\n".join(lines[:max_lines])
            text_field.cursor = (len(text_field.text), 0)  # Reset the cursor position
    
            

if __name__ == "__main__":
    MainApp().run()
