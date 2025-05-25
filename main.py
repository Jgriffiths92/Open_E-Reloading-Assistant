import csv
import itertools
import time
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
from kivy.uix.boxlayout import BoxLayout
import os
from kivymd.uix.textfield import MDTextField
from PIL import Image, ImageDraw, ImageFont
import platform
from kivy.config import ConfigParser
from configparser import ConfigParser
from kivy.core.window import Window
import shutil
from plyer import notification
from kivy.clock import Clock


# Ensure the soft keyboard pushes the target widget above it
Window.softinput_mode = "below_target"

try:
    from android import mActivity
    from jnius import autoclass, cast
    from android.permissions import request_permissions, Permission
except ImportError:
    mActivity = None  # Handle cases where the app is not running on Android
    autoclass = None  # Handle cases where pyjnius is not available
    request_permissions = None
    Permission = None
try:
    from jnius import autoclass
except ImportError:
    autoclass = None  # Handle cases where pyjnius is not available


def is_android():
    """Check if the app is running on an Android device."""
    try:
        from android import mActivity
        from jnius import autoclass, cast
        print("Running on Android")
        # Print if these modules are imported
        print("android imported:", 'mActivity' in globals() and mActivity is not None)
        print("jnius imported:", 'autoclass' in globals() and autoclass is not None)
        return True
    except ImportError:
        return False


# Import the nfc module if not running on Android
if not is_android():
    try:
        import nfc
    except ImportError:
        nfc = None  # Handle cases where the nfc module is not available

# Change color of the filechooser
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
    def on_enter(self):
        """Refresh the FileChooserListView when the screen is entered."""
        try:
            filechooser = self.ids.filechooser
            filechooser._update_files()  # Refresh the file and folder list
            print("File and folder list refreshed on screen enter.")
        except Exception as e:
            print(f"Error refreshing file and folder list: {e}")

    def sort_filechooser(self, sort_by="name", reverse=False):
        try:
            filechooser = self.ids.filechooser
        except Exception as e:
            print(f"Error accessing filechooser: {e}")
            return

        if sort_by == "name":
            filechooser.sort_func = lambda items: sorted(
                items, key=lambda item: item[0].lower(), reverse=reverse
            )
        elif sort_by == "date":
            import os
            def safe_getmtime(item):
                try:
                    return os.path.getmtime(item[1])
                except Exception:
                    return 0

            filechooser.sort_func = lambda items: sorted(
                items, key=safe_getmtime, reverse=reverse
            )
        elif sort_by == "type":
            import os
            def safe_isdir(item):
                try:
                    return not os.path.isdir(item[1])
                except Exception:
                    return True

            filechooser.sort_func = lambda items: sorted(
                items, key=lambda item: (safe_isdir(item), item[0].lower()), reverse=reverse
            )
        filechooser._update_files()

    def open_sort_menu(self, caller):
        from kivymd.uix.menu import MDDropdownMenu
        menu_items = [
            {"text": "Name", "on_release": lambda x="name": self.sort_filechooser(x)},
            {"text": "Date", "on_release": lambda x="date": self.sort_filechooser(x)},
            {"text": "Type", "on_release": lambda x="type": self.sort_filechooser(x)},
        ]
        self.sort_menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width_mult=3,
        )
        self.sort_menu.open()


class ManageDataScreen(Screen):
    pass


class SettingsScreen(Screen):
    pass


class MainApp(MDApp):
    EPD_INIT_MAP = {
        # Good Display 3.7-inch (SSD1680, 280x480)
        "Good Display 3.7-inch": [
            # Initialization sequence (hex string, no spaces)
            "120101DF01001103440023450000DF014E004F0000",  # SWRESET, DRIVER_OUTPUT, DATA_ENTRY, RAM X/Y, etc.
            "2200"  # Display update command (example)
        ],
        # Good Display 4.2-inch (SSD1680, 400x300)
        "Good Display 4.2-inch": [
            # Initialization sequence (hex string, no spaces)
            "12012B010011034400314500002B014E004F0000",  # SWRESET, DRIVER_OUTPUT, DATA_ENTRY, RAM X/Y, etc.
            "2200"  # Display update command (example)
        ],
        "Good Display 2.9-inch": [
            # Typical SSD1680 2.9" init commands (hex string, no spaces)
            # These are EXAMPLES. Replace with your vendor's actual values if needed.
            "012701000CD7D69D2CA83A1A3B08110344000F45270100004E004F2701",  # Initialization sequence
            "2200"  # Display update command (example)
        ],
    }

    def on_permissions_result(self, permissions, grant_results):
        """Handle the result of the permission request."""
        for permission, granted in zip(permissions, grant_results):
            if permission == Permission.NFC:
                if granted:
                    print("NFC permission granted.")
                    self.initialize_nfc()
                else:
                    print("NFC permission denied.")
            elif permission == Permission.READ_EXTERNAL_STORAGE:
                if granted:
                    print("Read external storage permission granted.")
                else:
                    print("Read external storage permission denied.")
            elif permission == Permission.WRITE_EXTERNAL_STORAGE:
                if granted:
                    print("Write external storage permission granted.")
                else:
                    print("Write external storage permission denied.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_parser = ConfigParser()  # Initialize ConfigParser
        private_storage_path = self.get_private_storage_path()
        self.config_file = os.path.join(private_storage_path, "settings.ini")  # Path to the settings file
        self.standalone_mode_enabled = False  # Default to standalone mode being disabled
        self.selected_display = "Good Display 3.7-inch"  # Default selected display
        self.selected_resolution = (280, 416)  # Default resolution for 3.7-inch display
        self.selected_orientation = "Portrait"  # Default orientation
        self.selected_save_folder = None  # Store the selected folder for saving CSV files
        self.detected_tag = None  # Initialize the detected_tag attribute

    dialog = None  # Store the dialog instance

    def send_csv_bitmap_via_nfc(self, intent):
        # 1. Convert CSV to bitmap
        output_path = self.csv_to_bitmap(self.current_data)
        if not output_path:
            print("Failed to create bitmap.")
            return

        # 2. Read bitmap as bytes
        with open(output_path, "rb") as f:
            image_buffer = f.read()

        # 3. Get bitmap dimensions
        from PIL import Image
        img = Image.open(output_path)
        width, height = img.size

        # 4. Prepare epd_init (replace with your actual values)
        epd_init = self.EPD_INIT_MAP.get(self.selected_display)
        if not epd_init:
            print(f"No epd_init found for display: {self.selected_display}")
            return

        # 5. Pass the intent down!
        self.send_nfc_image(intent, width, height, image_buffer, epd_init)

    def send_nfc_image(self, intent, width, height, image_buffer, epd_init):
        print("send_nfc_image called")
        NfcHelper = autoclass('com.openedope.open_edope.NfcHelper')

        # Convert Python bytes to Java byte[]
        ByteBuffer = autoclass('java.nio.ByteBuffer')
        image_buffer_java = ByteBuffer.wrap(bytes(image_buffer))

        # Convert Python list of strings to Java String[]
        String = autoclass('java.lang.String')
        Array = autoclass('java.lang.reflect.Array')
        epd_init_java_array = Array.newInstance(String, len(epd_init))
        for i, s in enumerate(epd_init):
            epd_init_java_array[i] = String(s)

        # Call your Java static method
        NfcHelper.processNfcIntent(intent, width, height, image_buffer_java, epd_init_java_array)

    def on_pause(self):
        print("on_pause CALLED")
        return True  # Returning True allows the app to be paused

    def on_resume(self):
        print("on_resume CALLED")
        self.enable_nfc_foreground_dispatch()
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        intent = PythonActivity.mActivity.getIntent()
        action = intent.getAction()
        print(f"Checking for new intent on resume... Action: {action}")

        # Check for SEND, VIEW, or any NFC action
        if action in [
            "android.intent.action.SEND",
            "android.intent.action.VIEW",
            "android.nfc.action.TAG_DISCOVERED",
            "android.nfc.action.NDEF_DISCOVERED",
            "android.nfc.action.TECH_DISCOVERED",
        ]:
            print("Calling on_new_intent from on_resume")
            self.on_new_intent(intent)
            # Optionally clear the intent action so it doesn't get handled again
            intent.setAction("")
        else:
            print("No shared file/text or NFC intent to process on resume.")

    def request_bal_exemption(self):
        if is_android() and autoclass:
            try:
                ActivityCompat = autoclass('androidx.core.app.ActivityCompat')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity

                # Request BAL exemption
                ActivityCompat.requestPermissions(
                    activity,
                    ["android.permission.BAL_EXEMPTION"],
                    0
                )
                print("Requested BAL exemption.")
            except Exception as e:
                print(f"Error requesting BAL exemption: {e}")

    def build(self):

        """Build the app's UI and initialize settings."""
        # Set the theme to Light
        self.theme_cls.theme_style = "Light"

        # Load saved settings
        self.load_settings()

        # Request permissions on Android
        if is_android():
            request_permissions(
                [Permission.NFC, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE],
                self.on_permissions_result
            )

        # Initialize NFC only on Android
        if is_android() and self.initialize_nfc():
            print("NFC initialized successfully.")

        # Dynamically set the rootpath for the FileChooserListView
        self.root = Builder.load_file("layout.kv")  # Load the root widget from the KV file
        saved_cards_screen = self.root.ids.screen_manager.get_screen("saved_cards")
        csv_directory = self.ensure_csv_directory()
        saved_cards_screen.ids.filechooser.rootpath = csv_directory

        # Handle the intent if the app was opened via an intent
        if is_android():
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = PythonActivity.mActivity.getIntent()
                print(f"Scheduling on_new_intent for action: {intent.getAction()}")  # <-- Add this line
                Clock.schedule_once(lambda dt: self.on_new_intent(intent), 0)
            except Exception as e:
                print(f"Error handling startup intent: {e}")
            def poll_intent(dt):
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = PythonActivity.mActivity.getIntent()
                action = intent.getAction()
                if action in [
                    "android.nfc.action.TAG_DISCOVERED",
                    "android.nfc.action.NDEF_DISCOVERED",
                    "android.nfc.action.TECH_DISCOVERED",
                ]:
                    print(f"Polling: found NFC intent action: {action}")
                    self.on_new_intent(intent)
                    intent.setAction("")  # Clear so it doesn't get handled again
        
            # Poll every second for new NFC intents
            Clock.schedule_interval(poll_intent, 1)
        
        # Initialize the dropdown menus
        self.display_menu = None
        self.orientation_menu = None

        # Set the default text for the display and orientation dropdown buttons
        self.root.ids.settings_screen.ids.display_dropdown_button.text = self.selected_display
        self.root.ids.settings_screen.ids.orientation_dropdown_button.text = self.selected_orientation

        # Hide the NFC button if on Android
        self.hide_nfc_button()

        # Delay check for empty table and show manual input if needed
        def check_and_show_manual_input(dt):
            # Only show manual input if there is no data loaded
            if not hasattr(self, "current_data") or not self.current_data:
                print("No data found after UI load, showing manual data input.")
                self.show_manual_data_input()

        Clock.schedule_once(check_and_show_manual_input, 0.5)  # Delay to ensure UI is loaded

        return self.root

    global show_lead, show_range, show_2_wind_holds
    show_lead = False
    show_range = False
    show_2_wind_holds = True
        
    def ensure_csv_directory(self):
        """Ensure the assets/CSV directory exists and is accessible."""
        if is_android():
            # Copy assets/CSV to internal storage on Android
            return self.copy_assets_to_internal_storage()
        else:
            # Use the local assets/CSV folder on non-Android platforms
            csv_directory = os.path.join(os.path.dirname(__file__), "assets", "CSV")
            if not os.path.exists(csv_directory):
                os.makedirs(csv_directory)
            return csv_directory

    def on_file_selected(self, selection):
        """Handle the file or folder selected in the FileChooserListView."""
        if self.standalone_mode_enabled:
            # If standalone mode is enabled
            print("Standalone mode is enabled.")
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

                    # Preprocess the data
                    processed_data = self.preprocess_data(data)

                    # Display the data as a table on the Home Screen
                    self.display_table(processed_data)

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

    def read_csv_to_dict(self, file_or_path):
        """Reads a CSV file or file-like object and maps it to static column names, ignoring the headers and skipping the first 6 lines."""
        static_columns = ["Target", "Range", "Elv", "Wnd1", "Wnd2", "Lead"]  # Static column names
        data = []
        try:
            print(f"Reading CSV: {file_or_path}")
            # Detect if file_or_path is a path or file-like object
            if isinstance(file_or_path, str):
                csv_file = open(file_or_path, mode="r", encoding="latin-1")
                close_after = True
            else:
                csv_file = file_or_path
                close_after = False

            reader = csv.reader(csv_file)
            # Skip the first 6 lines
            for _ in range(6):
                next(reader, None)
            for index, row in enumerate(reader, start=1):
                if not row:
                    continue
                if row[0].strip().lower() == "stage notes:":
                    break
                mapped_row = {static_columns[i]: row[i] if i < len(row) else "" for i in range(len(static_columns))}
                data.append(mapped_row)
            if close_after:
                csv_file.close()
            print(f"CSV data read successfully: {data}")
        except Exception as e:
            print(f"Error reading CSV file: {e}")
        return data

    def preprocess_data(self, data):
        """Shift columns to the right by one if 'Target' contains a number."""
        processed_data = []
        for row in data:
            target_value = row.get("Target", "")
            # Check if the "Target" column contains a number
            try:
                float(target_value)
                is_number = True
            except (ValueError, TypeError):
                is_number = False

            if is_number:
                # Shift the columns across to the right by one
                shifted_row = {}
                keys = list(row.keys())
                for i in range(len(keys) - 1):
                    shifted_row[keys[i + 1]] = row[keys[i]]
                shifted_row[keys[0]] = ""  # Set the first column to empty
                processed_data.append(shifted_row)
            else:
                # Keep the row as is if "Target" is not a number
                processed_data.append(row)
        return processed_data

    def display_table(self, data):
        """Displays the filtered CSV data as text on the Home Screen."""
        if not data:
            print("No data to display.")
            return

        # Preprocess the data to handle numeric "Target" values
        data = self.preprocess_data(data)

        # Define the static column order
        static_headers = ["Target", "Range", "Elv", "Wnd1", "Wnd2", "Lead"]

        # Filter headers based on the show/hide options
        headers = ["Elv", "Wnd1"]  # Start with these columns
        target_present = any(row.get("Target") for row in data)
        if target_present:
            headers.insert(0, "Target")
        if show_range:
            if not target_present:
                headers.insert(0, "Range")  # Move Range to position 0 if Target is not displayed
            else:
                headers.insert(1, "Range")  # Otherwise, after Target
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
            table_text += " | ".join(
                f"{str(row.get(header, '')):<{column_widths[header]}}" for header in headers) + "\n"  # Add rows

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
            lead_menu = {"text": "Hide Lead",
                         "on_release": lambda: (self.menu_callback("Hide Lead"), self.menu.dismiss())}
        else:
            lead_menu = {"text": "Show Lead",
                         "on_release": lambda: (self.menu_callback("Show Lead"), self.menu.dismiss())}
        # Update the "Show Range" menu item dynamically
        if show_range:
            range_menu = {"text": "Hide Range",
                          "on_release": lambda: (self.menu_callback("Hide Range"), self.menu.dismiss())}
        else:
            range_menu = {"text": "Show Range",
                          "on_release": lambda: (self.menu_callback("Show Range"), self.menu.dismiss())}
        # Update the "Show 2 Wind Holds" menu item dynamically
        if show_2_wind_holds:
            wind_holds_menu = {"text": "Show 1 Wind Hold",
                               "on_release": lambda: (self.menu_callback("Show 1 Wind Hold"), self.menu.dismiss())}
        else:
            wind_holds_menu = {"text": "Show 2 Wind Holds",
                               "on_release": lambda: (self.menu_callback("Show 2 Wind Holds"), self.menu.dismiss())}

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

        # Regenerate the manual data input fields if they are visible
        home_screen = self.root.ids.home_screen
        table_container = home_screen.ids.table_container
        if table_container.children:  # Check if manual data input fields are displayed
            self.show_manual_data_input()

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
        if not self.dialog:
            # Get the list of folders in the assets/CSV directory
            csv_directory = self.ensure_csv_directory()
            folders = [f for f in os.listdir(csv_directory) if os.path.isdir(os.path.join(csv_directory, f))]

            # Create a BoxLayout to hold the dropdown button and text input
            content_layout = BoxLayout(
                orientation="vertical",
                spacing="10dp",  # Add spacing between the button and text field
                size_hint=(1, None),
                height="120dp",  # Adjust height to fit both widgets
            )

            # Add the dropdown button to the layout
            dropdown_button = MDFlatButton(
                id="dropdown_button",
                text="Select Event",
                size_hint=(1, None),
                height="48dp",
                pos_hint={"center_x": 0.5},
            )

            # Define the function to handle menu item selection
            def update_selected_folder(selected_option):
                dropdown_button.text = selected_option  # Update the button text to display the selected option
                dropdown_menu.dismiss()  # Close the dropdown menu
                if selected_option == "New Event...":
                    text_input.opacity = 1  # Make the text input visible
                    text_input.disabled = False  # Enable the text input
                    self.selected_save_folder = None  # Clear the selected folder
                else:
                    text_input.opacity = 0  # Hide the text input
                    text_input.disabled = True  # Disable the text input
                    self.selected_save_folder = os.path.join(csv_directory, selected_option)  # Set the selected folder

            # Create the dropdown menu
            dropdown_menu = MDDropdownMenu(
                caller=dropdown_button,
                items=[{"text": "New Event...", "on_release": lambda: update_selected_folder("New Event...")}] +
                      [{"text": folder,
                        "on_release": lambda selected_folder=folder: update_selected_folder(selected_folder)}
                       for folder in folders],
                position="center",
            )

            # Assign the menu to the button's on_release callback
            dropdown_button.on_release = lambda: dropdown_menu.open()

            # Add the text input field to the layout, initially hidden
            text_input = MDTextField(
                hint_text="Event Name",
                size_hint=(1, None),
                height="48dp",
                multiline=False,
                opacity=0,  # Make it invisible initially
                disabled=True,  # Disable it initially
                halign="center",  # Center the text horizontally
            )

            # Add both widgets to the layout
            content_layout.add_widget(dropdown_button)
            content_layout.add_widget(text_input)

            # Add the layout to the dialog
            self.dialog = MDDialog(
                title="Save Data",
                text="Select an event folder or create a new one.",
                type="custom",
                content_cls=content_layout,
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_release=lambda x: self.dialog.dismiss()
                    ),
                    MDRaisedButton(
                        text="SAVE",
                        on_release=lambda x: (
                            self.save_data(new_event_name=text_input.text.strip() if text_input.text.strip() else None),
                            self.dialog.dismiss()  # Automatically close the dialog after saving
                        )
                    ),
                ],
            )

        self.dialog.open()

    def save_data(self, new_event_name=None):
        """Save the current data to a CSV file in the private storage directory, creating it if it doesn't exist."""
        if hasattr(self, "current_data") and self.current_data:
            # Determine the private storage path
            storage_path = self.get_private_storage_path()
            if storage_path:
                try:
                    # Ensure the CSV folder exists
                    csv_folder_path = os.path.join(storage_path, "CSV")
                    if not os.path.exists(csv_folder_path):
                        os.makedirs(csv_folder_path)

                    # Construct the file name and path
                    file_name = f"{self.root.ids.home_screen.ids.stage_name_field.text}.csv"
                    if new_event_name:
                        # Use the new event name to create a folder inside the CSV folder
                        event_folder_path = os.path.join(csv_folder_path, new_event_name)
                        if not os.path.exists(event_folder_path):
                            os.makedirs(event_folder_path)  # Create the folder if it doesn't exist
                        file_path = os.path.join(event_folder_path, file_name)
                    elif self.selected_save_folder:
                        # Use the selected folder inside the CSV folder
                        if not os.path.exists(self.selected_save_folder):
                            os.makedirs(self.selected_save_folder)  # Create the folder if it doesn't exist
                        file_path = os.path.join(self.selected_save_folder, file_name)
                    else:
                        print("No folder selected or created. Cannot save data.")
                        return

                    # Write the data to the CSV file
                    with open(file_path, mode="w", encoding="utf-8", newline="") as csv_file:
                        writer = csv.writer(csv_file)

                        # Add 6 empty rows as the header
                        for _ in range(5):
                            writer.writerow([])

                        # Write the headers
                        headers = self.current_data[0].keys()
                        writer.writerow(headers)

                        # Write the data rows
                        for row in self.current_data:
                            writer.writerow(row.values())

                        # Write the stage notes as the footer
                        stage_notes = self.root.ids.home_screen.ids.stage_notes_field.text.strip()
                        if stage_notes:
                            writer.writerow([])  # Add an empty row before the footer
                            writer.writerow(["Stage Notes:"])
                            writer.writerow([stage_notes])

                        print(f"Data saved to: {file_path}")

                        # Refresh the FileChooserListView
                        saved_cards_screen = self.root.ids.screen_manager.get_screen("saved_cards")
                        filechooser = saved_cards_screen.ids.filechooser
                        filechooser._update_files()  # Refresh the file and folder list
                        print("File and folder list refreshed.")
                except Exception as e:
                    print(f"Error saving data to CSV: {e}")
            else:
                print("Private storage path is not available.")
        else:
            print("No data available to save.")

    def save_settings(self):
        """Save the selected settings to a configuration file."""
        try:
            # Add a section for settings if it doesn't exist
            if not self.config_parser.has_section("Settings"):
                self.config_parser.add_section("Settings")

            # Save the selected display model, orientation, and standalone mode
            self.config_parser.set("Settings", "display_model", self.selected_display)
            self.config_parser.set("Settings", "orientation", self.selected_orientation)
            self.config_parser.set("Settings", "standalone_mode", str(self.standalone_mode_enabled))  # Save as string

            # Debug: Print the settings being saved
            print(
                f"Saving settings: display_model={self.selected_display}, orientation={self.selected_orientation}, standalone_mode={self.standalone_mode_enabled}")

            # Write the settings to the file
            with open(self.config_file, "w") as config_file:
                self.config_parser.write(config_file)  # Pass the file object to the write() method
            print("Settings saved successfully.")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_settings(self):
        """Load the saved settings from the configuration file."""
        try:
            # Read the configuration file
            self.config_parser.read(self.config_file)

            # Load the display model and orientation
            if self.config_parser.has_option("Settings", "display_model"):
                self.selected_display = self.config_parser.get("Settings", "display_model")
            if self.config_parser.has_option("Settings", "orientation"):
                self.selected_orientation = self.config_parser.get("Settings", "orientation")

            # Debug: Print the loaded settings
            print(f"Loaded settings: display_model={self.selected_display}, orientation={self.selected_orientation}")
        except Exception as e:
            print(f"Error loading settings: {e}")

    def csv_to_bitmap(self, csv_data, output_path=None):
        """Convert CSV data to a bitmap image, resize it to fit the display resolution while keeping the aspect ratio, and save it."""
        try:
            # Set the default output path to the assets/bitmap folder
            bitmap_directory = os.path.join(os.path.dirname(__file__), "assets", "bitmap")
            if not os.path.exists(bitmap_directory):
                os.makedirs(bitmap_directory)  # Create the directory if it doesn't exist

            # Use the default output path if none is provided
            if output_path is None:
                output_path = os.path.join(bitmap_directory, "output.bmp")

            # Default resolution if no display is selected
            display_width, display_height = 280, 416

            # Adjust for orientation based on final resolution
            if self.selected_orientation == "Landscape":
                display_width, display_height = max(display_width, display_height), min(display_width, display_height)
            else:
                display_width, display_height = min(display_width, display_height), max(display_width, display_height)

            # Load the font file (ensure the font file is in the correct path)
            font_path = os.path.join(os.path.dirname(__file__), "assets", "fonts", "RobotoMono-Regular.ttf")
            font = ImageFont.truetype(font_path, 12)  # Load the font file

            # Create a blank white image
            image = Image.new("RGB", (display_width, display_height), "white")
            draw = ImageDraw.Draw(image)

            # Add the stage name at the top
            stage_name = self.root.ids.home_screen.ids.stage_name_field.text  # Get the stage name from the text field
            y = 10  # Starting vertical position
            text_bbox = draw.textbbox((0, 0), stage_name, font=font)  # Get the bounding box of the text
            text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
            x = (display_width - text_width) // 2  # Center the text horizontally
            draw.text((x, y), stage_name, fill="black", font=font)
            y += 20  # Add some spacing after the stage name

            # Draw a horizontal line under the stage name
            draw.line((10, y, display_width - 10, y), fill="black", width=1)
            y += 20  # Add some spacing after the line

            # Calculate column widths based on the data
            filtered_data = self.filter_table_data(csv_data)
            column_widths = {header: len("Tgt" if header == "Target" else header) for header in
                             filtered_data[0].keys()}  # Start with header lengths
            for row in filtered_data:
                for header, value in row.items():
                    column_widths[header] = max(column_widths[header], len(str(value)))

            # Write headers to the image
            headers = " | ".join(f"{'Tgt' if header == 'Target' else header:<{column_widths[header]}}" for header in
                                 filtered_data[0].keys())
            text_bbox = draw.textbbox((0, 0), headers, font=font)  # Get the bounding box of the headers
            text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
            x = (display_width - text_width) // 2  # Center the text horizontally
            draw.text((x, y), headers, fill="black", font=font)
            y += 20  # Move to the next line

            # Write CSV data to the image
            for row in filtered_data:
                row_text = " | ".join(f"{str(value):<{column_widths[header]}}" for header, value in row.items())
                text_bbox = draw.textbbox((0, 0), row_text, font=font)  # Get the bounding box of the row text
                text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
                x = (display_width - text_width) // 2  # Center the text horizontally
                draw.text((x, y), row_text, fill="black", font=font)
                y += 20  # Move to the next line

            # Add the stage notes below the table data
            stage_notes = self.root.ids.home_screen.ids.stage_notes_field.text  # Get the stage notes from the text field
            y += 20  # Add some spacing before the stage notes
            draw.line((10, y, display_width - 10, y), fill="black", width=1)  # Draw a line above the stage notes
            y += 10  # Add some spacing after the line
            text_bbox = draw.textbbox((0, 0), "Stage Notes:",
                                      font=font)  # Get the bounding box of the stage notes label
            text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
            x = (display_width - text_width) // 2  # Center the text horizontally
            draw.text((x, y), "Stage Notes:", fill="black", font=font)
            y += 30  # Add some spacing after the stage notes label
            draw.line((10, y, display_width - 10, y), fill="black",
                      width=1)  # Draw a horizontal line under the stage notes label
            y += 20  # Add some spacing after the line
            text_bbox = draw.textbbox((0, 0), stage_notes, font=font)  # Get the bounding box of the stage notes
            text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
            x = (display_width - text_width) // 2  # Center the text horizontally
            draw.text((x, y), stage_notes, fill="black", font=font)

            # Resize the image to fit within the display resolution while keeping the aspect ratio
            image.thumbnail(self.selected_resolution, Image.LANCZOS)

            # Save the resized image as a bitmap
            image.save(output_path)
            print(f"Bitmap saved to {output_path}")
            print(f"Bitmap dimensions: {image.size}")
            return output_path
        except Exception as e:
            print(f"Error converting CSV to bitmap: {e}")
            return None

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

    def open_display_dropdown(self, button):
        """Open the dropdown menu for selecting a display model."""
        # Define the available display models with their resolutions
        display_models = [
            {"text": "Good Display 3.7-inch", "resolution": (280, 416),
             "on_release": lambda: self.set_display_model("Good Display 3.7-inch", (280, 416))},
            {"text": "Good Display 4.2-inch", "resolution": (300, 400),
             "on_release": lambda: self.set_display_model("Good Display 4.2-inch", (400, 300))},
            {"text": "Good Display 2.9-inch", "resolution": (128, 296),
             "on_release": lambda: self.set_display_model("Good Display 2.9-inch", (296, 128))},
        ]

        # Create the dropdown menu if it doesn't exist
        if not self.display_menu:
            self.display_menu = MDDropdownMenu(
                caller=button,
                items=[
                    {"text": model["text"], "on_release": model["on_release"]}
                    for model in display_models
                ],
            )

        # Open the dropdown menu
        self.display_menu.open()

    def set_display_model(self, model, resolution):
        """Set the selected display model and update the button text."""
        # Check the selected orientation
        if self.selected_orientation == "Landscape":
            final_resolution = resolution  # Use the resolution as-is for Landscape
        else:
            final_resolution = (resolution[1], resolution[0])  # Invert the resolution for Portrait

        self.selected_display = model
        self.selected_resolution = final_resolution  # Store the final resolution
        self.root.ids.settings_screen.ids.display_dropdown_button.text = f"{model}"
        print(f"Selected display model: {model} with resolution {final_resolution}")

        # Save the updated settings
        self.save_settings()

        # Close the dropdown menu
        if self.display_menu:
            self.display_menu.dismiss()

    def open_orientation_dropdown(self, button):
        """Open the dropdown menu for selecting orientation."""
        # Define the available orientations
        orientation_options = [
            {"text": "Portrait", "on_release": lambda: self.set_orientation("Portrait")},
            {"text": "Landscape", "on_release": lambda: self.set_orientation("Landscape")},
        ]

        # Create the dropdown menu if it doesn't exist
        if not hasattr(self, "orientation_menu") or not self.orientation_menu:
            self.orientation_menu = MDDropdownMenu(
                caller=button,
                items=orientation_options,
            )

        # Open the dropdown menu
        self.orientation_menu.open()

    def set_orientation(self, orientation):
        """Set the selected orientation and update the button text."""
        self.selected_orientation = orientation  # Store the selected orientation
        self.root.ids.settings_screen.ids.orientation_dropdown_button.text = orientation
        print(f"Selected orientation: {orientation}")

        # Save the updated settings
        self.save_settings()

        # Close the dropdown menu
        if self.orientation_menu:
            self.orientation_menu.dismiss()

    def on_standalone_mode_toggle(self, active):
        """Handle the Stand Alone Mode toggle."""
        self.standalone_mode_enabled = active  # Update the standalone mode state
        print(f"Stand Alone Mode {'enabled' if active else 'disabled'}")

        # Save the updated state to the settings
        self.save_settings()

        if active:
            self.show_manual_data_input()  # Show manual data input fields
        else:
            # Clear the manual data input fields and restore the table container
            home_screen = self.root.ids.home_screen
            table_container = home_screen.ids.table_container
            table_container.clear_widgets()
            if hasattr(self, "current_data"):
                self.display_table(self.current_data)  # Restore the table if data exists

    def on_broom_button_press(self):
        """Handle the broom button press."""
        print("Broom button pressed. Performing cleanup...")
        # Add your cleanup logic here

    def get_external_storage_path(self):
        """Retrieve the external storage path using mActivity or default to assets/CSV."""
        if is_android():
            try:
                # Get the Android context
                context = mActivity.getApplicationContext()

                # Get the external files directory
                result = context.getExternalFilesDir(None)  # Pass `None` to get the root directory
                if result:
                    storage_path = str(result.toString())
                    print(f"External storage path: {storage_path}")
                    return storage_path
                else:
                    print("Failed to retrieve external storage path.")
                    return None
            except Exception as e:
                print(f"Error retrieving external storage path: {e}")
                return None
        else:
            # Default to assets/CSV folder
            csv_directory = os.path.join(os.path.dirname(__file__), "assets", "CSV")
            if not os.path.exists(csv_directory):
                os.makedirs(csv_directory)
            print(f"Defaulting to assets/CSV folder: {csv_directory}")
            return csv_directory

    def get_private_storage_path(self):
        """Retrieve the app's private storage path."""
        if is_android():
            try:
                context = mActivity.getApplicationContext()
                private_storage_path = context.getFilesDir().getAbsolutePath()
                print(f"Private storage path: {private_storage_path}")
                return private_storage_path
            except Exception as e:
                print(f"Error retrieving private storage path: {e}")
                return None
        else:
            # Use a local directory for non-Android platforms
            private_storage_path = os.path.join(os.path.dirname(__file__), "private_storage")
            if not os.path.exists(private_storage_path):
                os.makedirs(private_storage_path)
            print(f"Private storage path (non-Android): {private_storage_path}")
            return private_storage_path

    def save_to_external_storage(self, file_name, content):
        """Save a file to the external storage directory or assets/CSV."""
        storage_path = self.get_external_storage_path()
        if storage_path:
            try:
                # Construct the full file path
                file_path = os.path.join(storage_path, file_name)

                # Write the content to the file
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(content)
                print(f"File saved to: {file_path}")
            except Exception as e:
                print(f"Error saving file to storage: {e}")
        else:
            print("Storage path is not available.")

        if is_android():
            print("Running on Android. External storage is available.")
            storage_path = self.get_external_storage_path()
            if storage_path:
                print(f"External storage path: {storage_path}")
        else:
            print("Not running on Android. External storage is not available.")

    def initialize_nfc(self):
        """Initialize the NFC adapter and enable foreground dispatch."""
        if is_android() and autoclass:
            try:
                print("Initializing NFC adapter...")
                NfcAdapter = autoclass('android.nfc.NfcAdapter')
                PendingIntent = autoclass('android.app.PendingIntent')
                Intent = autoclass('android.content.Intent')
                IntentFilter = autoclass('android.content.IntentFilter')

                # Get the NFC adapter
                self.nfc_adapter = NfcAdapter.getDefaultAdapter(mActivity)
                if self.nfc_adapter is None:
                    print("NFC is not available on this device.")
                    return False

                # Create a pending intent for NFC
                intent = Intent(mActivity, mActivity.getClass())
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP)
                print(f"Intent flags: {intent.getFlags()}")  # Log the intent flags
                self.pending_intent = PendingIntent.getActivity(
                    mActivity, 0, intent, PendingIntent.FLAG_IMMUTABLE
                )
                print(f"PendingIntent created: {self.pending_intent}")

                # Create intent filters for NFC
                self.intent_filters = [
                    IntentFilter("android.nfc.action.TAG_DISCOVERED"),
                    IntentFilter("android.nfc.action.NDEF_DISCOVERED"),
                    IntentFilter("android.nfc.action.TECH_DISCOVERED"),
                ]
                print("Intent filters created for NFC.")

                print("NFC adapter initialized successfully.")
                return True
            except Exception as e:
                print(f"Error initializing NFC: {e}")
                return False
        else:
            print("NFC functionality is only available on Android.")
            return False

    def enable_nfc_foreground_dispatch(self):
        """Enable NFC foreground dispatch to handle NFC intents."""
        if is_android() and autoclass:
            try:
                # Use the same PendingIntent and intent filters as in initialize_nfc
                self.nfc_adapter.enableForegroundDispatch(
                    mActivity,
                    self.pending_intent,
                    self.intent_filters,
                    None
                )
                print("NFC foreground dispatch enabled.")
            except Exception as e:
                print(f"Error enabling NFC foreground dispatch: {e}")

    def on_new_intent(self, intent):
        print("on_new_intent called")
        """Handle new intents, including shared data and NFC tags."""
        if is_android() and autoclass:
            try:
                # Get the action from the intent
                action = intent.getAction()
                print(f"Intent action: {action}")

                # --- Print all extras for debugging ---
                extras = intent.getExtras()
                if extras:
                    print("Intent extras:")
                    for key in extras.keySet():
                        value = extras.get(key)
                        print(f"  {key}: {value}")
                else:
                    print("No extras in intent.")
                # --- End debug block ---

                # --- NEW: Always check for NFC tag extra, even if action is not NFC ---
                EXTRA_TAG = autoclass('android.nfc.NfcAdapter').EXTRA_TAG
                tag = intent.getParcelableExtra(EXTRA_TAG)
                if tag:
                    print("NFC tag detected (regardless of action)!")
                    tech_list = tag.getTechList()
                    print("Tag technologies detected by Android:")
                    for tech in tech_list:
                        print(f" - {tech}")
                    self.send_csv_bitmap_via_nfc(intent)
                    return  # Optionally return here if you don't want to process further

                # NFC tag detected by action
                if action in [
                    "android.nfc.action.TAG_DISCOVERED",
                    "android.nfc.action.NDEF_DISCOVERED",
                    "android.nfc.action.TECH_DISCOVERED",
                ]:
                    print("NFC tag detected!")

                    # Get the Tag object from the intent
                    tag = intent.getParcelableExtra(EXTRA_TAG)
                    if tag:
                        # Get the list of supported techs
                        tech_list = tag.getTechList()
                        print("Tag technologies detected by Android:")
                        for tech in tech_list:
                            print(f" - {tech}")
                    else:
                        print("No Tag object found in intent.")

                    self.send_csv_bitmap_via_nfc(intent)
                    return  # Optionally return here if you don't want to process further

                # Handle shared data (SEND/VIEW)
                if action in ["android.intent.action.SEND", "android.intent.action.VIEW"]:
                    extras = intent.getExtras()
                    if extras and extras.containsKey("android.intent.extra.TEXT"):
                        # Handle shared text
                        shared_text = extras.getString("android.intent.extra.TEXT")
                        print(f"Received shared text: {shared_text}")
                        self.process_received_text(shared_text)
                    elif extras and extras.containsKey("android.intent.extra.STREAM"):
                        # Handle shared file
                        stream_uri = extras.getParcelable("android.intent.extra.STREAM")
                        print(f"Received stream URI: {stream_uri}")

                        # If the stream_uri is a string path, open it directly
                        if isinstance(stream_uri, str) and stream_uri.startswith("/"):
                            print(f"Received file path: {stream_uri}")
                            self.process_received_csv(stream_uri)
                        else:
                            Uri = autoclass('android.net.Uri')
                            try:
                                stream_uri = cast('android.net.Uri', stream_uri)
                            except Exception:
                                stream_uri = Uri.parse(str(stream_uri))

                            content_resolver = mActivity.getContentResolver()
                            file_path = self.resolve_uri_to_path(content_resolver, stream_uri)

                            if file_path:
                                self.process_received_csv(file_path)
                            else:
                                try:
                                    input_stream = content_resolver.openInputStream(stream_uri)
                                    if input_stream:
                                        ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')
                                        buffer = ByteArrayOutputStream()
                                        byte = input_stream.read()
                                        while byte != -1:
                                            buffer.write(byte)
                                            byte = input_stream.read()
                                        input_stream.close()
                                        content_bytes = bytes(buffer.toByteArray())
                                        try:
                                            content = content_bytes.decode("utf-8")
                                        except UnicodeDecodeError:
                                            print("UTF-8 decode failed, trying latin-1...")
                                            content = content_bytes.decode("latin-1")
                                        print(f"File contents (from InputStream):\n{content}")
                                        self.process_received_csv(content)
                                    else:
                                        print("InputStream is None. Cannot read the file.")
                                except Exception as e:
                                    print(f"Error reading from InputStream: {e}")
                else:
                    print("No valid data found in the intent.")
            except Exception as e:
                print(f"Error handling new intent: {e}")

    def resolve_uri_to_path(self, content_resolver, uri):
        """Resolve a content URI to a file path."""
        try:
            if uri is None:
                print("Error: URI is None. Cannot resolve path.")
                return None

            # Cast the Parcelable to a Uri
            Uri = autoclass('android.net.Uri')
            if not isinstance(uri, Uri):
                uri = Uri.parse(str(uri))  # Ensure it's a Uri object

            print(f"Resolving URI: {uri}")

            # Check if the URI has a valid scheme
            scheme = uri.getScheme()
            if scheme == "file":
                return uri.getPath()
            elif scheme == "content":
                # Query the content resolver for the file path
                projection = [autoclass("android.provider.MediaStore$MediaColumns").DATA]
                cursor = content_resolver.query(uri, projection, None, None, None)
                if cursor is not None:
                    column_index = cursor.getColumnIndexOrThrow(projection[0])
                    cursor.moveToFirst()
                    file_path = cursor.getString(column_index)
                    cursor.close()
                    print(f"Content scheme URI resolved to path: {file_path}")
                    return file_path
                else:
                    print("Cursor is None. Could not resolve content URI.")
                    return None
            else:
                print(f"Unsupported URI scheme: {scheme}")
                return None
        except Exception as e:
            print(f"Error resolving URI to path: {e}")
            return None

    def process_received_csv(self, file_path_or_uri):
        """Process the received CSV file or CSV text."""
        import io
        try:
            # If it's CSV text (not a path or URI), parse directly
            if (
                    "\n" in file_path_or_uri or "\r" in file_path_or_uri
            ) and not file_path_or_uri.startswith("/") and not file_path_or_uri.startswith("content://"):
                # Looks like CSV text, not a path or URI
                csv_file = io.StringIO(file_path_or_uri)
                data = self.read_csv_to_dict(csv_file)
            else:
                # Fix for Android: prepend storage root if needed
                if file_path_or_uri.startswith("/Documents/"):
                    storage_root = "/storage/emulated/0"
                    abs_path = storage_root + file_path_or_uri
                    print(f"Trying absolute path: {abs_path}")
                    file_path_or_uri = abs_path

                if file_path_or_uri.startswith("/"):  # If it's a file path
                    with open(file_path_or_uri, mode="r", encoding="utf-8") as csv_file:
                        data = self.read_csv_to_dict(csv_file)
                else:  # If it's a content URI
                    content_resolver = mActivity.getContentResolver()
                    input_stream = content_resolver.openInputStream(file_path_or_uri)
                    content = input_stream.read().decode("utf-8")
                    csv_file = io.StringIO(content)
                    data = self.read_csv_to_dict(csv_file)

            self.current_data = data  # Store the data for filtering or other operations

            # Preprocess the data
            processed_data = self.preprocess_data(data)

            # Display the data as a table on the Home Screen
            self.display_table(processed_data)

            # Navigate to the Home Screen
            self.root.ids.screen_manager.current = "home"
            print(f"Processed received CSV: {file_path_or_uri}")
        except Exception as e:
            print(f"Error processing received CSV: {e}")

    def read_csv_from_assets(self, file_name):
        """Read a CSV file from the assets/CSV folder."""
        if is_android():
            try:
                # Get the Android context and AssetManager
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                context = PythonActivity.mActivity.getApplicationContext()
                AssetManager = autoclass('android.content.res.AssetManager')
                asset_manager = context.getAssets()

                # Open the file in the assets/CSV folder
                with asset_manager.open(f"CSV/{file_name}") as asset_file:
                    content = asset_file.read().decode("utf-8")
                    print(f"Content of {file_name}:\n{content}")
                    return content
            except Exception as e:
                print(f"Error reading CSV from assets: {e}")
                return None
        else:
            # On non-Android platforms, read from the local assets/CSV folder
            file_path = os.path.join(os.path.dirname(__file__), "assets", "CSV", file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    print(f"Content of {file_name}:\n{content}")
                    return content
            except Exception as e:
                print(f"Error reading CSV file: {e}")
                return None

    def copy_assets_to_internal_storage(self):
        """Copy the assets/CSV folder to the app's private storage directory."""
        private_storage_path = self.get_private_storage_path()
        if private_storage_path:
            try:
                csv_internal_path = os.path.join(private_storage_path, "CSV")

                # Ensure the destination directory exists
                if not os.path.exists(csv_internal_path):
                    os.makedirs(csv_internal_path)

                # Copy files and directories from assets/CSV to private storage
                if is_android():
                    AssetManager = autoclass('android.content.res.AssetManager')
                    context = mActivity.getApplicationContext()
                    asset_manager = context.getAssets()
                    files = asset_manager.list("CSV")  # List files and directories in the assets/CSV folder

                    for file_name in files:
                        source_path = f"CSV/{file_name}"
                        dest_path = os.path.join(csv_internal_path, file_name)

                        if asset_manager.list(source_path):  # Check if it's a directory
                            if not os.path.exists(dest_path):
                                os.makedirs(dest_path)  # Create the directory in the destination
                            # Recursively copy the directory
                            self.copy_directory_from_assets(asset_manager, source_path, dest_path)
                        else:
                            # Copy a single file
                            with asset_manager.open(source_path) as asset_file:
                                with open(dest_path, "wb") as output_file:
                                    output_file.write(asset_file.read())
                            print(f"Copied file: {source_path} to {dest_path}")
                else:
                    # Copy files locally for non-Android platforms
                    assets_csv_path = os.path.join(os.path.dirname(__file__), "assets", "CSV")
                    for file_name in os.listdir(assets_csv_path):
                        src_path = os.path.join(assets_csv_path, file_name)
                        dest_path = os.path.join(csv_internal_path, file_name)
                        if os.path.isdir(src_path):
                            if not os.path.exists(dest_path):
                                os.makedirs(dest_path)
                            # Recursively copy the directory
                            self.copy_directory_locally(src_path, dest_path)
                        else:
                            # Copy a single file
                            with open(src_path, "rb") as src, open(dest_path, "wb") as dest:
                                dest.write(src.read())
                            print(f"Copied file: {src_path} to {dest_path}")

                print(f"Assets copied to private storage: {csv_internal_path}")
                return csv_internal_path
            except Exception as e:
                print(f"Error copying assets to private storage: {e}")
                return None
        else:
            print("Private storage path is not available.")
            return None

    def delete_file_or_folder(self, path):
        """Delete the selected file or folder and refresh the file list."""
        try:
            if os.path.exists(path):
                if os.path.isdir(path):
                    # Remove the folder
                    os.rmdir(path)
                    print(f"Deleted folder: {path}")
                else:
                    # Remove the file
                    os.remove(path)
                    print(f"Deleted file: {path}")

                # Refresh the FileChooserListView
                saved_cards_screen = self.root.ids.screen_manager.get_screen("saved_cards")
                filechooser = saved_cards_screen.ids.filechooser
                filechooser._update_files()  # Refresh the file and folder list
                print("File and folder list refreshed.")
            else:
                print(f"Path does not exist: {path}")
        except Exception as e:
            print(f"Error deleting file or folder: {e}")

    def show_manual_data_input(self):
        """Display manual data input fields in the CSV data table location based on filtered display options."""
        home_screen = self.root.ids.home_screen
        table_container = home_screen.ids.table_container

        # Clear any existing widgets in the table container
        table_container.clear_widgets()

        # Create a vertical layout to hold the rows and buttons
        main_layout = BoxLayout(orientation="vertical", spacing="10dp", size_hint=(1, None))
        main_layout.bind(minimum_height=main_layout.setter("height"))  # Adjust height dynamically

        # Define the available fields and their display options
        available_fields = {
            "Target": {"hint_text": "Target", "show": True},  # Always show Target
            "Range": {"hint_text": "Range", "show": show_range},  # Controlled by show_range
            "Elv": {"hint_text": "Elevation", "show": True},  # Always show Elevation
            "Wnd1": {"hint_text": "Wind 1", "show": True},  # Always show Wind 1
            "Wnd2": {"hint_text": "Wind 2", "show": show_2_wind_holds},  # Controlled by show_2_wind_holds
            "Lead": {"hint_text": "Lead", "show": show_lead},  # Controlled by show_lead
        }

        # Store the available fields for later use
        self.available_fields = available_fields

        # Add the first row of input fields
        self.add_data_row(main_layout)

        # Create a layout for the "ADD ROW" and "DELETE ROW" buttons
        add_row_layout = BoxLayout(orientation="horizontal", spacing="10dp", size_hint=(1, None), height=dp(50))
        add_row_layout.add_widget(
            MDRaisedButton(
                text="ADD ROW",
                size_hint=(None, None),
                size=(dp(120), dp(40)),
                on_release=lambda x: self.add_data_row(main_layout)
            )
        )
        add_row_layout.add_widget(
            MDRaisedButton(
                text="DELETE ROW",
                size_hint=(None, None),
                size=(dp(120), dp(40)),
                md_bg_color=(1, 0, 0, 1),  # Red background
                on_release=lambda x: self.delete_last_row(main_layout)
            )
        )

        # Create a layout for the "CANCEL" and "ADD" buttons
        action_buttons_layout = BoxLayout(orientation="horizontal", spacing="10dp", size_hint=(1, None), height=dp(50))
        action_buttons_layout.add_widget(
            MDFlatButton(
                text="CANCEL",
                on_release=lambda x: self.cancel_manual_data_input()
            )
        )
        action_buttons_layout.add_widget(
            MDRaisedButton(
                text="ADD",
                on_release=lambda x: self.add_manual_data()
            )
        )

        # Add the button layouts to the main layout
        main_layout.add_widget(add_row_layout)
        main_layout.add_widget(action_buttons_layout)

        # Add the main layout to the table container
        table_container.add_widget(main_layout)

    def add_data_row(self, table_container):
        """Add a new row of data fields directly underneath the existing rows."""
        # Create a layout for the new row
        row_layout = BoxLayout(orientation="horizontal", spacing="10dp", size_hint=(1, None))
        row_layout.height = dp(50)  # Adjust height for a single row of text fields

        # Add text fields for manual data input based on display options
        row_fields = {}
        for field_name, field_options in self.available_fields.items():
            if field_options["show"]:  # Only add fields that are enabled
                text_field = MDTextField(
                    hint_text=field_options["hint_text"],
                    multiline=False,
                    size_hint_x=0.15
                )
                row_fields[field_name] = text_field
                row_layout.add_widget(text_field)

        # Store the row fields for later use
        if not hasattr(self, "manual_data_rows"):
            self.manual_data_rows = []
        self.manual_data_rows.append(row_fields)

        # Find the correct index to insert the new row
        # The new row should be added above the button layouts
        button_index = 0
        for i, child in enumerate(reversed(table_container.children)):
            if isinstance(child, BoxLayout) and any(
                    isinstance(widget, MDRaisedButton) or isinstance(widget, MDFlatButton) for widget in
                    child.children):
                button_index = len(table_container.children) - i
                break

        # Add the new row at the calculated index
        table_container.add_widget(row_layout, index=button_index)

    def add_manual_data(self):
        """Add the manually entered data to the current data and display it."""
        try:
            # Collect data from all rows of text fields
            for row_fields in self.manual_data_rows:
                # Initialize the row with all columns, defaulting to "0"
                manual_data = {key: "0" for key in self.available_fields.keys()}

                # Populate the row with data from the input fields
                for key, field in row_fields.items():
                    manual_data[key] = field.text if field.text.strip() else "0"

                # Validate the data (optional)
                if not manual_data["Target"]:
                    print("Target is required.")
                    return

                # Add the data to the current data
                if not hasattr(self, "current_data") or not self.current_data:
                    self.current_data = []  # Initialize if no data is loaded
                self.current_data.append(manual_data)

            # Display the updated data
            self.display_table(self.current_data)

            # Clear the input fields
            self.cancel_manual_data_input()
            print("Manual data added:", self.current_data)
        except Exception as e:
            print(f"Error adding manual data: {e}")

    def cancel_manual_data_input(self):
        """Cancel manual data input and restore the table container."""
        home_screen = self.root.ids.home_screen
        table_container = home_screen.ids.table_container
        table_container.clear_widgets()  # Clear the input fields
        if hasattr(self, "current_data"):
            self.display_table(self.current_data)  # Restore the table if data exists

    def delete_last_row(self, table_container):
        """Delete the bottom-most row of data fields from the table container."""
        if hasattr(self, "manual_data_rows") and len(self.manual_data_rows) > 1:
            # Remove the last row from the manual_data_rows list
            self.manual_data_rows.pop()

            # Remove the last row layout from the table container
            for child in table_container.children:
                # Check if the child is a row layout containing text fields
                if isinstance(child, BoxLayout) and any(isinstance(widget, MDTextField) for widget in child.children):
                    table_container.remove_widget(child)
                    break
        else:
            if len(self.manual_data_rows) > 0:
                # Clear the text fields in the last row
                last_row_fields = self.manual_data_rows[-1]
                for field in last_row_fields.values():
                    field.text = ""
            print("Cannot delete the last row. At least one row must remain.")

    def copy_directory_from_assets(self, asset_manager, source_path, dest_path):
        """Recursively copy a directory from the assets folder to the destination."""
        try:
            files = asset_manager.list(source_path)
            for file_name in files:
                sub_source_path = f"{source_path}/{file_name}"
                sub_dest_path = os.path.join(dest_path, file_name)

                if asset_manager.list(sub_source_path):  # Check if it's a directory
                    if not os.path.exists(sub_dest_path):
                        os.makedirs(sub_dest_path)
                    self.copy_directory_from_assets(asset_manager, sub_source_path, dest_path)
                else:
                    # Copy a single file
                    with asset_manager.open(sub_source_path) as asset_file:
                        with open(sub_dest_path, "wb") as output_file:
                            output_file.write(asset_file.read())
                    print(f"Copied file: {sub_source_path} to {sub_dest_path}")
        except Exception as e:
            print(f"Error copying directory from assets: {e}")

    def copy_directory_locally(self, src_path, dest_path):
        """Recursively copy a directory locally."""
        try:
            for file_name in os.listdir(src_path):
                sub_src_path = os.path.join(src_path, file_name)
                sub_dest_path = os.path.join(dest_path, file_name)

                if os.path.isdir(sub_src_path):
                    if not os.path.exists(sub_dest_path):
                        os.makedirs(sub_dest_path)
                    self.copy_directory_locally(sub_src_path, dest_path)
                else:
                    # Copy a single file
                    with open(sub_src_path, "rb") as src, open(sub_dest_path, "wb") as dest:
                        dest.write(src.read())
                    print(f"Copied file: {sub_src_path} to {sub_dest_path}")
        except Exception as e:
            print(f"Error copying directory locally: {e}")

    def process_subject_content(self, subject_content):
        """Process the subject content received in the intent."""
        print(f"Processing subject content: {subject_content}")

        if subject_content == "Range Card":
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = PythonActivity.mActivity.getIntent()

                # Try to get the URI from the intent's data
                stream_uri = intent.getData()
                if stream_uri is None:
                    # Fallback to extras if getData() doesn't work
                    extras = intent.getExtras()
                    if extras and extras.containsKey("android.intent.extra.STREAM"):
                        stream_uri = extras.getParcelable("android.intent.extra.STREAM")

                if stream_uri:
                    print(f"Received stream URI: {stream_uri}")

                    # Cast the Parcelable to a Uri
                    Uri = autoclass('android.net.Uri')
                    if not isinstance(stream_uri, Uri):
                        stream_uri = Uri.parse(str(stream_uri))  # Ensure it's a Uri object

                    # Resolve the URI to a file path or input stream
                    content_resolver = mActivity.getContentResolver()
                    file_path = self.resolve_uri_to_path(content_resolver, stream_uri)

                    if file_path:
                        # Read and print the file contents
                        print(f"Resolved file path: {file_path}")
                        with open(file_path, "r", encoding="utf-8") as file:
                            content = file.read()
                            print(f"Contents of the file:\n{content}")
                    else:
                        # Fallback: Read directly from the InputStream
                        try:
                            input_stream = content_resolver.openInputStream(stream_uri)
                            if input_stream:
                                content = input_stream.read().decode("utf-8")
                                print(f"File contents (from InputStream):\n{content}")
                                self.process_received_text(content)
                            else:
                                print("InputStream is None. Cannot read the file.")
                        except Exception as e:
                            print(f"Error reading from InputStream: {e}")
                else:
                    print("No valid URI found in the intent.")
            except Exception as e:
                print(f"Error processing subject content: {e}")

    def hide_nfc_button(self):
        """Hide the NFC button if running on Android."""
        if is_android():
            try:
                # Assuming the NFC button has an ID like 'nfc_button'
                nfc_button = self.root.ids.home_screen.ids.nfc_button
                nfc_button.opacity = 0  # Make the button invisible
                nfc_button.disabled = True  # Disable the button
                print("NFC button hidden on Android.")
            except Exception as e:
                print(f"Error hiding NFC button: {e}")

    def verify_copied_files(self):
        """Verify the contents of the copied CSV files."""
        dest_dir = os.path.join(os.environ.get("ANDROID_PRIVATE", ""), "CSV")
        for file_name in os.listdir(dest_dir):
            dest_file = os.path.join(dest_dir, file_name)
            print(f"Verifying file: {dest_file}")
            with open(dest_file, "r", encoding="utf-8") as file:
                print(file.read())


def handle_received_file(intent):
    """Handle a file received via Intent.EXTRA_STREAM."""
    if is_android() and autoclass:
        try:
            # Import necessary Android classes
            Uri = autoclass('android.net.Uri')
            ContentResolver = autoclass('android.content.ContentResolver')

            # Check if the intent contains EXTRA_STREAM
            if intent.hasExtra(Intent.EXTRA_STREAM):
                # Get the Parcelable URI
                stream_uri = intent.getParcelableExtra(Intent.EXTRA_STREAM)
                print(f"Received Parcelable URI: {stream_uri}")

                # Cast the Parcelable to a Uri
                if not isinstance(stream_uri, Uri):
                    stream_uri = Uri.parse(str(stream_uri))  # Ensure it's a Uri object

                # Resolve the URI to a file path or read from InputStream
                content_resolver = mActivity.getContentResolver()
                file_path = MainApp().resolve_uri_to_path(content_resolver, stream_uri)

                if file_path:
                    # File path resolved, read the file

                    print(f"Resolved file path: {file_path}")
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        print(f"File contents:\n{content}")
                else:
                    # Fallback: Read directly from the InputStream
                    try:
                        input_stream = content_resolver.openInputStream(stream_uri)
                        if input_stream:
                            content = input_stream.read().decode("utf-8")
                            print(f"File contents (from InputStream):\n{content}")
                            self.process_received_text(content)
                        else:
                            print("InputStream is None. Cannot read the file.")

                    except Exception as e:
                        print(f"Error reading from InputStream: {e}")
            else:
                print("No EXTRA_STREAM found in the intent.")
        except Exception as e:
            print(f"Error handling received file: {e}")
    else:
        print("This functionality is only available on Android.")


def start_foreground_service(self):
    """Start a foreground service with a persistent notification."""
    if is_android():
        try:
            # Create a persistent notification
            notification.notify(
                title="Open E-Dope Service",
                message="The app is running in the background.",
                timeout=10  # Notification timeout in seconds
            )
            print("Foreground service started with a persistent notification.")
        except Exception as e:
            print(f"Error starting foreground service: {e}")
    else:
        print("Foreground service is only available on Android.")


def process_received_file(self, file_path):
    """Process the received file."""
    try:
        print(f"Processing received file: {file_path}")
        if file_path.endswith(".csv"):
            # Read and process the CSV file
            with open(file_path, "r", encoding="utf-8") as csv_file:
                data = self.read_csv_to_dict(csv_file)
                self.current_data = data
                self.display_table(data)
                print("CSV file processed successfully.")
        else:
            print("Unsupported file type.")
    except Exception as e:
        print(f"Error processing received file: {e}")


def process_received_text(self, text_data):
    """Process the received text data."""
    try:
        # Split the data into lines
        lines = text_data.strip().split("\n")
        # Extract the headers from the second line (after the metadata)
        headers = lines[1].split(",")
        # Parse the rows into dictionaries
        data = []
        for line in lines[2:]:  # Skip the first two lines (metadata and headers)
            row = line.split(",")
            data.append({headers[i]: row[i] for i in range(len(headers))})

        # Store the data for filtering or other operations
        self.current_data = data

        # Display the data in the table
        self.display_table(data)
        print("Text data processed and displayed successfully.")
    except Exception as e:
        print(f"Error processing text data: {e}")
if __name__ == "__main__":
    MainApp().run()