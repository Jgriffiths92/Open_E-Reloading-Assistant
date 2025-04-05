import csv
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.datatables import MDDataTable
from kivy.metrics import dp
from plyer import filechooser
from kivy.uix.label import Label
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar
import os

# Define Screens
class HomeScreen(Screen):
    pass

class SavedCardsScreen(Screen):
    pass

class ManageDataScreen(Screen):
    pass

class MainApp(MDApp):
    def build(self):
        return Builder.load_file("layout.kv")
    
    global show_lead, show_range, show_2_wind_holds
    show_lead = False
    show_range = False
    show_2_wind_holds = True

    def open_file_chooser(self):
        # Specify the starting directory
        start_directory = os.path.join(os.getcwd(), "assets\CSV")
        filechooser.open_file(on_selection=self.on_file_selected, path=start_directory)
       
    def on_fab_press(self):
        # Open the native file chooser with a filter for CSV files
        filechooser.open_file(on_selection=self.on_file_selected, filters=["*.csv"])

    def on_file_selected(self, selection):
        if selection:
            # Handle the selected file
            file_path = selection[0]
            try:
                data = self.read_csv_to_dict(file_path)
                self.current_data = data  # Store the original data
                filtered_data = self.filter_table_data(data)  # Filter the data
                self.display_table(filtered_data)  # Display the filtered data
            except Exception as e:
                print(f"Error reading file: {str(e)}")  # Print the error message
        else:
            print("No file selected")  # Print a message if no file is selected

    def read_csv_to_dict(self, file_path):
        """Reads a CSV file and maps it to static column names, ignoring the headers."""
        static_columns = ["Target", "Range", "Elv", "Wnd1", "Wnd2", "Lead"]  # Static column names
        data = []

        with open(file_path, mode="r", encoding="utf-8") as csv_file:
            reader = csv.reader(csv_file)  # Use csv.reader to read the file
            next(reader, None)  # Skip the first row (headers), if present
            for index, row in enumerate(reader, start=1):
            # Skip lines 3 and 4 (index 2 and 3 in zero-based indexing)
                if index in [2, 3]:
                    continue

                # Skip empty rows
                if not row:
                    continue

                # Map the row to the static column names
                mapped_row = {static_columns[i]: row[i] if i < len(row) else "" for i in range(len(static_columns))}
                data.append(mapped_row)

        return data

    def display_table(self, data):
        """Displays the CSV data as text on the HomeScreen."""
        if not data:
            print("No data to display.")
            return

        # Define the static column order
        static_headers = ["Target", "Range", "Elv", "Wnd1", "Wnd2", "Lead"]

        # Filter headers based on the data keys to maintain the order
        headers = [header for header in static_headers if header in data[0]]

        # Calculate the maximum width for each column
        column_widths = {header: len(header) for header in headers}  # Start with header lengths
        for row in data:
            for header in headers:
                column_widths[header] = max(column_widths[header], len(str(row.get(header, ""))))

        # Format the headers and rows as text
        table_text = " | ".join(f"{header:<{column_widths[header]}}" for header in headers) + "\n"  # Add headers
        table_text += "-" * (sum(column_widths.values()) + len(headers) * 3 - 1) + "\n"  # Add a separator line
        for row in data:
            table_text += " | ".join(f"{str(row.get(header, '')):<{column_widths[header]}}" for header in headers) + "\n"  # Add rows

        # Add the text to the table_container in HomeScreen
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
        
    def on_settings_button_press(self, instance):
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

        # Regenerate the table with updated columns
        home_screen = self.root.ids.home_screen
        table_container = home_screen.ids.table_container
        table_container.clear_widgets()  # Clear the current table

        # Filter the data and regenerate the table
        if hasattr(self, "current_data"):  # Check if data is already loaded
            filtered_data = self.filter_table_data(self.current_data)
            self.display_table(filtered_data)

        # Re-run the on_settings_button_press to refresh the menu
        self.on_settings_button_press(self.menu.caller)

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


if __name__ == "__main__":
    MainApp().run()
