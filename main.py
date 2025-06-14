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
from kivy.uix.filechooser import FileChooserListView
import shutil
from kivymd.uix.dialog import MDDialog
from circularprogressbar import CircularProgressBar
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.app import App
from kivymd.toast import toast
from kivy.properties import StringProperty


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
    from jnius import autoclass, cast
    NfcAdapter = autoclass('android.nfc.NfcAdapter')
    Ndef = autoclass('android.nfc.tech.Ndef')
    NdefFormatable = autoclass('android.nfc.tech.NdefFormatable')
    MifareClassic = autoclass('android.nfc.tech.MifareClassic')
    MifareUltralight = autoclass('android.nfc.tech.MifareUltralight')
except ImportError:
    autoclass = None
    NfcAdapter = None
    Ndef = None
    NdefFormatable = None
    MifareClassic = None
    MifareUltralight = None


def is_android():
    """Check if the app is running on an Android device."""
    try:
        from android import mActivity
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


class SavedCartridgesScreen(Screen):
    def on_enter(self):
        try:
            print("File and folder list refreshed on screen enter.")
            app = App.get_running_app()
            # Use the loaded sort_type and sort_order from settings
            reverse = app.sort_order == "desc"
            app.populate_swipe_file_list(sort_by=app.sort_type, reverse=reverse)
        except Exception as e:
            print(f"Error refreshing file and folder list: {e}")

    def sort_filechooser(self, sort_by="name", reverse=False):
        try:
            filechooser = self.ids.filechooser
            filechooser.sort_type = sort_by
            filechooser.sort_order = 'desc' if reverse else 'asc'
            filechooser.sort_dirs_first = True
            self.populate_swipe_file_list()
            print(f"Sorted by {sort_by}, reverse={reverse}")
        except Exception as e:
            print(f"Error accessing filechooser: {e}")

    def open_sort_menu(self, caller):
        from kivymd.uix.menu import MDDropdownMenu
        app = App.get_running_app()
        menu_items = [
            {"text": "Name", "on_release": lambda x="name": app.populate_swipe_file_list(sort_by="name")},
            {"text": "Date", "on_release": lambda x="date": app.populate_swipe_file_list(sort_by="date")},
            {"text": "Type", "on_release": lambda x="type": app.populate_swipe_file_list(sort_by="type")},
        ]
        self.sort_menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width_mult=3,
        )
        self.sort_menu.open()


class ManageDataScreen(Screen):
    delete_option_label = StringProperty("Delete Folders After")  # Default text
    def on_enter(self):
        app = App.get_running_app()
        if not getattr(app, "manage_data_dialog_shown", False):
            self.show_manage_data_dialog()

    def show_manage_data_dialog(self):
        app = App.get_running_app()
        def close_dialog(*args):
            dialog.dismiss()
            app.root.ids.screen_manager.current = "home"  # Go to Home screen

        def ok_and_never_show_again(*args):
            dialog.dismiss()
            app.manage_data_dialog_shown = True
            app.save_settings()

        dialog = MDDialog(
            title="Manage Data",
            type="custom",
            content_cls=Label(
            text="Here you can manage and delete your saved load data and folders.\nUse With Caution: deleted data cannot be recovered.",
            halign="center",
            valign="middle",
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height="100dp",
            ),
            buttons=[
            MDFlatButton(
                text="BACK",
                on_release=close_dialog
            ),
            MDFlatButton(
                text="OK",
                on_release=ok_and_never_show_again,
                theme_text_color="Custom",          # <-- Add this line
                text_color=(0, 0.4, 1, 1)           # Blue color for OK button
            ),
            ],
        )
        dialog.open()
    def open_delete_option_menu(self, caller):
        options = [
            {"text": "After 1 week", "on_release": lambda: self.set_delete_option("week")},
            {"text": "After 1 month", "on_release": lambda: self.set_delete_option("month")},
            {"text": "After 1 year", "on_release": lambda: self.set_delete_option("year")},
            {"text": "Never", "on_release": lambda: self.set_delete_option("never")},
        ]
        self.delete_menu = MDDropdownMenu(caller=caller, items=options)
        self.delete_menu.open()

    def set_delete_option(self, option):
        app = App.get_running_app()
        labels = {
            "week": "After 1 week",
            "month": "After 1 month",
            "year": "After 1 year",
            "never": "Never",
        }
        app.delete_folders_after = option
        app.delete_option_label = labels.get(option, "Delete Folders After")
        app.save_settings()
        if hasattr(self, "delete_menu"):
            self.delete_menu.dismiss()
        app.delete_old_folders()

    def delete_all_csv_files(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        def confirm_delete(*args):
            app = App.get_running_app()
            csv_dir = app.ensure_csv_directory()
            try:
                for item in os.listdir(csv_dir):
                    item_path = os.path.join(csv_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                print("All files and folders in assets/CSV deleted.")
                toast("All Load Data files and folders deleted.")
            except Exception as e:
                print(f"Error deleting CSV files: {e}")
                toast(f"Error deleting files: {e}")
            dialog.dismiss()

        dialog = MDDialog(
            title="Confirm Delete",
            text="Are you sure you want to delete ALL Cartides and Load Data in? This cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDFlatButton(
                    text="DELETE",
                    text_color=(1, 0, 0, 1),
                    on_release=confirm_delete
                ),
            ],
        )
        dialog.open()


class SettingsScreen(Screen):
    pass


class CustomFileChooserListView(FileChooserListView):
    sort_type = "date"  # Default sort by date
    sort_order = "asc"  # Or "desc" if you want newest first

    def _sort_files(self, files):
        sort_type = getattr(self, 'sort_type', 'date')
        reverse = getattr(self, 'sort_order', 'asc') == 'desc'

        def get_date(item):
            try:
                return os.path.getmtime(item[1])
            except Exception:
                return 0

        def get_type(item):
            # Folders first, then by extension
            if os.path.isdir(item[1]):
                return ('', '')
            name, ext = os.path.splitext(item[0])
            return (ext.lower(), item[0].lower())

        if sort_type == 'date':
            key = get_date
        elif sort_type == 'type':
            key = get_type
        else:
            key = lambda item: item[0].lower()

        # Sort all items (folders and files) together
        return sorted(files, key=key, reverse=reverse)


if is_android():
    from jnius import PythonJavaClass, java_method

    class NfcProgressListener(PythonJavaClass):
        __javainterfaces__ = ['com/openedope/open_e_reloading_assistant/NfcProgressListener']
        __javacontext__ = 'app'

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method('(I)V')
        def onProgress(self, percent):
            # Called from Java with progress (0-100)
            print(f"NFC Progress: {percent}%")
            # Schedule on main thread to update UI
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.app.update_nfc_progress(percent))


class MainApp(MDApp):
    search_text = ""
    delete_option_label = StringProperty("Delete Folders After")  # Default text
    EPD_INIT_MAP = {
        # Good Display 3.7-inch (UC8171, 240x416)
        "Good Display 3.7-inch": [
            "F0DB00005EA006512000F001A0A4010CA502000AA40108A502000AA4010CA502000AA40108A502000AA4010CA502000AA40108A502000AA4010CA502000AA40103A102001FA10104A40103A3021013A20112A502000AA40103A20102A40103A20207A5",
            "F0DA000003F05120"
        ],
        # Good Display 4.2-inch (SSD1680, 400x300)
        "Good Display 4.2-inch": [
            "F0DB000063A00603300190012CA4010CA502000AA40108A502000AA4010CA502000AA40102A10112A40102A104012B0101A1021101A103440031A105452B010000A1023C01A1021880A1024E00A1034F2B01A3022426A20222F7A20120A40102A2021001A502000A",
            "F0DA000003F00330"
        ],
        # Good Display 2.9-inch (SSD1680, 296x128)
        "Good Display 2.9-inch": [
            "F0DB000067A006012000800128A4010CA502000AA40108A502000AA4010CA502000AA40102A10112A40102A10401270101A1021101A10344000FA1054527010000A1023C05A103210080A1021880A1024E00A1034F2701A30124A3022426A20222F7A20120A40102A2021001A502000A",
            "F0DA000003F00120"
        ],
    }
    def get_basename(self, path):
        import os
        return os.path.basename(path)
    def on_nfc_button_press(self, *args):
        """Handle the NFC button press: add manual data if present, display table, and generate the bitmap."""
        print("NFC button pressed!")

        # Only add manual data if at least one field is filled in
        if (
            hasattr(self, "manual_data_rows")
            and self.manual_data_rows
            and any(
                any(field.text.strip() for field in row_fields.values())
                for row_fields in self.manual_data_rows
            )
        ):
            print("Manual data input detected, adding manual data before NFC transfer.")
            self.add_manual_data()

        # Display the updated table (if not already)
        if hasattr(self, "current_data") and self.current_data:
            self.display_table(self.current_data)
            output_path = self.csv_to_bitmap(self.current_data)
            if output_path:
                print(f"Bitmap generated and saved to: {output_path}")
            else:
                print("Failed to generate bitmap.")
        else:
            print("No data loaded to generate bitmap.")

    def update_nfc_progress(self, percent):
        if hasattr(self, "nfc_progress_bar") and self.nfc_progress_bar:
            # If percent is 100, delay the update by 3 seconds
            if percent >= 100:
                Clock.schedule_once(lambda dt: self._finish_nfc_progress(), 3)
            else:
                self.nfc_progress_bar.value = percent

    def _finish_nfc_progress(self):
        if hasattr(self, "nfc_progress_bar") and self.nfc_progress_bar:
            self.nfc_progress_bar.value = 100
        if hasattr(self, "nfc_progress_label"):
            self.nfc_progress_label.text = "Transfer successful!"
            self.nfc_progress_label.color = (0, 0.6, 0, 1)
        Clock.schedule_once(lambda dt: self.hide_nfc_progress_dialog(), 1.5)
        # Clear the data table, cartridge notes, and cartridge name after success
        self.clear_table_data()
    def on_nfc_transfer_error(self, error_message="Transfer failed!"):
        if hasattr(self, "nfc_progress_label"):
            self.nfc_progress_label.text = error_message
            self.nfc_progress_label.color = (1, 0, 0, 1)  # Red color for error
        Clock.schedule_once(lambda dt: self.hide_nfc_progress_dialog(), 2)

        
    def show_nfc_progress_dialog(self, message="Transferring data..."):
        # Vibrate for 500ms when the dialog opens (Android only)
        if is_android() and mActivity and autoclass:
            try:
                Context = autoclass('android.content.Context')
                vibrator = mActivity.getSystemService(Context.VIBRATOR_SERVICE)
                # Try to use VibrationEffect if available, otherwise use legacy API
                try:
                    VibrationEffect = autoclass('android.os.VibrationEffect')
                    effect = VibrationEffect.createOneShot(500, VibrationEffect.DEFAULT_AMPLITUDE)
                    vibrator.vibrate(effect)
                    print("Vibrating with VibrationEffect")
                except Exception:
                    vibrator.vibrate(500)
                    print("Vibrating with legacy API")
            except Exception as e:
                print(f"Error vibrating device: {e}")

        if hasattr(self, "nfc_progress_dialog") and self.nfc_progress_dialog:
            self.nfc_progress_dialog.dismiss()
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.label import Label

        # Use FloatLayout to allow centering
        box = FloatLayout(size_hint_y=None, height="200dp")

        self.nfc_progress_bar = CircularProgressBar(
            size_hint=(None, None),
            size=(120, 120),
            pos_hint={"center_x": 0.5, "center_y": 0.6},
            max=100,
            value=0,
            thickness=15,
            color=(0.2, 0.6, 1, 1),
            label_color=(0.2, 0.6, 1, 1),  # <-- Add this line
            background_color=(0.9, 0.9, 0.9, 1),
        )
        box.add_widget(self.nfc_progress_bar)

        # Add the label below the progress bar, also centered
        self.nfc_progress_label = Label(
            text=message,
            size_hint=(None, None),
            size=(200, 40),
            pos_hint={"center_x": 0.5, "y": 0.05},
            halign="center",
            valign="middle",
            color=(0, 0, 0, 1),
        )
        self.nfc_progress_label.bind(size=self.nfc_progress_label.setter('text_size'))
        box.add_widget(self.nfc_progress_label)

        self.nfc_progress_dialog = MDDialog(
            title="NFC Transfer",
            type="custom",
            content_cls=box,
            auto_dismiss=False,
        )
        self.nfc_progress_dialog.open()
        """
        Handler for the NFC button press.
        Generates the bitmap from the current CSV data and saves it.
        """
        try:
            if not hasattr(self, "current_data") or not self.current_data:
                print("No data loaded to generate bitmap.")
                return
    
            output_path = self.csv_to_bitmap(self.current_data)
            if output_path:
                print(f"Bitmap generated and saved to: {output_path}")
            else:
                print("Failed to generate bitmap.")
        except Exception as e:
            print(f"Error generating bitmap: {e}")
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
        self.selected_resolution = (240, 416)  # Default resolution for 3.7-inch display
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

        # 2. Read bitmap as 1bpp bytes
        from PIL import Image
        with Image.open(output_path) as img:
            img = img.convert("1", dither=Image.FLOYDSTEINBERG)
            if self.selected_orientation == "Portrait":
                img = img.rotate(-90, expand=True)
            # else: do not rotate for landscape
            image_buffer = pack_image_column_major(img)

        # 3. Get bitmap dimensions
        from PIL import Image
        img = Image.open(output_path)
        width, height = img.size

        # 4. Prepare epd_init (replace with your actual values)
        epd_init = self.EPD_INIT_MAP.get(self.selected_display)
        if not epd_init:
            print(f"No epd_init found for display: {self.selected_display}")
            return

        # Add these debug prints:
        print("epd_init[0] raw string:", repr(epd_init[0]))
        print("epd_init[0] hex length:", len(epd_init[0]))
        try:
            test_bytes = bytes.fromhex(epd_init[0])
            print("epd_init[0] bytes length:", len(test_bytes))
        except Exception as e:
            print("Error converting epd_init[0] to bytes:", e)

        print(f"epd_init[0]: {epd_init[0]}")
        print(f"epd_init[0] length: {len(bytes.fromhex(epd_init[0]))} bytes")
        epd_init_bytes = bytes.fromhex(epd_init[0])
        print("epd_init[0] bytes:", epd_init_bytes)
        print("epd_init[0] length (bytes):", len(epd_init_bytes))
        print("First 16 bytes of image_buffer:", list(image_buffer[:16]))
        print("Image buffer length:", len(image_buffer))

        # 5. Pass the intent down!
        print("epd_init[0] right before Java:", repr(epd_init[0]), len(epd_init[0]))
        self.send_nfc_image(intent, width, height, image_buffer, epd_init)

    def send_nfc_image(self, intent, width, height, image_buffer, epd_init):
        print("send_nfc_image called")
        print(f"image_buffer type: {type(image_buffer)}")
        print("First 16 bytes of image_buffer:", list(image_buffer[:16]))
        print("Image buffer length:", len(image_buffer))
        expected_size = width * height // 8
        if len(image_buffer) != expected_size:
            print(f"WARNING: Image buffer size ({len(image_buffer)}) does not match expected size ({expected_size}) for {width}x{height} display.")
        NfcHelper = autoclass('com.openedope.open_e_reloading_assistant.NfcHelper')
        ByteBuffer = autoclass('java.nio.ByteBuffer')
        image_buffer_bb = ByteBuffer.wrap(bytes(image_buffer))

        # Convert epd_init to Java String[]
        String = autoclass('java.lang.String')
        Array = autoclass('java.lang.reflect.Array')
        epd_init_java_array = Array.newInstance(String, len(epd_init))
        for i, s in enumerate(epd_init):
            epd_init_java_array[i] = String(s)
        # Create the progress listener
        listener = NfcProgressListener(self)
        # Call the ByteBuffer method
        NfcHelper.processNfcIntentByteBufferAsync(intent, width, height, image_buffer_bb, epd_init_java_array, listener)
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
    def delete_old_folders(self):
        """Delete folders in assets/CSV older than the selected threshold."""
        thresholds = {
            "week": 7 * 24 * 3600,
            "month": 30 * 24 * 3600,
            "year": 365 * 24 * 3600,
            "never": None,
        }
        option = getattr(self, "delete_folders_after", "never").lower()
        threshold = thresholds.get(option)
        if threshold is None:
            return  # Never delete

        csv_dir = self.ensure_csv_directory()
        now = time.time()
        for folder in os.listdir(csv_dir):
            folder_path = os.path.join(csv_dir, folder)
            if os.path.isdir(folder_path):
                mtime = os.path.getmtime(folder_path)
                if now - mtime > threshold:
                    try:
                        shutil.rmtree(folder_path)
                        print(f"Deleted old folder: {folder_path}")
                    except Exception as e:
                        print(f"Error deleting folder {folder_path}: {e}")
    def build(self):

        """Build the app's UI and initialize settings."""
        # Set the theme to Light
        self.theme_cls.theme_style = "Light"

        # Load saved settings
        self.load_settings()

        # Request permissions on Android
        if is_android():
            request_permissions([
                Permission.NFC,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.VIBRATE,  # <-- Add this line
            ], self.on_permissions_result)
            if self.initialize_nfc():
                print("NFC initialized successfully.")
            from android import activity
            activity.bind(on_new_intent=self.on_new_intent)

        # Dynamically set the rootpath for the FileChooserListView
        self.root = Builder.load_file("layout.kv")  # Load the root widget from the KV file
        saved_cartridges_screen = self.root.ids.screen_manager.get_screen("saved_cartridges")
        csv_directory = self.ensure_csv_directory()

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

    def clear_table_data(self):
        """Clear the data in the table and update the UI."""
        self.current_data = []
        home_screen = self.root.ids.home_screen
        table_container = home_screen.ids.table_container
        table_container.clear_widgets()
        # Clear the cartridge name and cartridge notes fields
        try:
            home_screen.ids.cartridge_name_field.text = ""
            home_screen.ids.cartridge_notes_field.text = ""
            print("cartridge name and cartridge notes fields cleared.")
        except Exception as e:
            print(f"Error clearing cartridge name or notes: {e}")
        print("Data table cleared.")
        self.show_manual_data_input()  # Show manual data input fields again

        
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
        if selection:
            selected_path = selection[0]
            if os.path.isdir(selected_path):
                # If it's a folder, show its contents
                self.populate_swipe_file_list(selected_path)
                return
            # Extract the file name and set it to the cartridge_name_field
            file_name = os.path.basename(selected_path)
            self.root.ids.home_screen.ids.cartridge_name_field.text = os.path.splitext(file_name)[0]
            # If the selected file is a CSV, extract the cartridge notes footer and display it in the cartridge_notes_field
            if selected_path.endswith(".csv"):
                try:
                    with open(selected_path, mode="r", encoding="utf-8") as csv_file:
                        lines = csv_file.readlines()
                        # Look for the "cartridge Notes:" footer and extract the notes
                        for i, line in enumerate(lines):
                            if line.strip().lower() == "cartridge notes:":
                                cartridge_notes = "".join(lines[i + 1:]).strip()
                                self.root.ids.home_screen.ids.cartridge_notes_field.text = cartridge_notes
                                break
                except Exception as e:
                    print(f"Error extracting cartridge notes: {e}")
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
                    saved_cartridges_screen = self.root.ids.screen_manager.get_screen("saved_cartridges")

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
        headers = ["Projectile", "Powder", "Charge", "Primer", "Brass", "Headspace", "Ogive", "OAL", "Velocity"]
        data = []
        try:
            print(f"Reading CSV: {file_or_path}")
            if isinstance(file_or_path, str):
                csv_file = open(file_or_path, mode="r", encoding="utf-8")
                close_after = True
            else:
                csv_file = file_or_path
                close_after = False

            reader = csv.reader(csv_file)
            # Find the header row (skip empty lines)
            for row in reader:
                if row and row[0].strip().lower() == "projectile":
                    break
            else:
                print("Header row not found!")
                if close_after:
                    csv_file.close()
                return []

            # Read data rows until "Cartridge Notes:" or empty
            for row in reader:
                if not row or (row[0].strip().lower() == "cartridge notes:"):
                    break
                # Skip empty or short rows
                if all(cell.strip() == "" for cell in row):
                    continue
                mapped_row = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
                data.append(mapped_row)
            if close_after:
                csv_file.close()
            print(f"CSV data read successfully: {data}")
        except Exception as e:
            print(f"Error reading CSV file: {e}")
        return data

    def preprocess_data(self, data):
        """Preprocess data for reloading table. No shifting needed for reloading headers."""
        # Only keep the relevant headers and preserve order
        headers = ["Projectile", "Powder", "Charge", "Primer", "Brass", "Headspace", "Ogive", "OAL", "Velocity"]
        processed_data = []
        for row in data:
            processed_row = {header: row.get(header, "") for header in headers}
            processed_data.append(processed_row)
        return processed_data

    def display_table(self, data):
        # Check if data is empty
        if not data:
            print("No data to display.")
            return

        # --- Use the same headers as display_table ---
        headers = ["Projectile", "Powder", "Charge", "Primer", "Brass", "Headspace", "Ogive", "OAL", "Velocity"]

        # Transpose data for column display (each field is a row, each value is a column)
        table_rows = []
        for header in headers:
            row = [header] + [str(row.get(header, "")) for row in data]
            table_rows.append(row)

        # Calculate the maximum width for each column
        num_columns = max(len(row) for row in table_rows)
        column_widths = [0] * num_columns
        for row in table_rows:
            for i, cell in enumerate(row):
                column_widths[i] = max(column_widths[i], len(cell))

        # Build the table as a string
        table_text = ""
        for row in table_rows:
            row_text = " | ".join(
                f"{cell:<{column_widths[i]}}" for i, cell in enumerate(row)
            )
            table_text += row_text + "\n"

        # Add the text to the table_container in Home Screen
        home_screen = self.root.ids.home_screen
        table_container = home_screen.ids.table_container
        table_container.clear_widgets()

        # Create a Label to display the table text
        table_label = Label(
            text=table_text,
            halign="center",
            valign="center",
            size_hint=(1, 1),
            text_size=(table_container.width, None),
            color=(0, 0, 0, 1),
            font_name="assets/fonts/RobotoMono-Regular.ttf",
        )
        table_container.add_widget(table_label)

    def on_dots_press(self, instance):
       
        # Define menu items
        menu_items = [
            {"text": "Settings", "on_release": lambda: self.menu_callback("Settings")},
        ]

        # Create the dropdown menu
        self.menu = MDDropdownMenu(
            caller=instance,
            items=menu_items,
        )
        self.menu.open()

    def menu_callback(self, option):
        if option == "Settings":
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

    def on_fab_press(self):
        """Handle the floating action button press."""
        # Get the cartridge name from the text field
        cartridge_name = self.root.ids.home_screen.ids.cartridge_name_field.text.strip()
        if not cartridge_name:
            toast("cartridge Name required for Save")
            return  # Do not open the save dialog

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
                    text_input.disabled = True  # Disable it
                    self.selected_save_folder = os.path.join(csv_directory, selected_option)

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
                    MDFlatButton(
                        text="SAVE",
                        on_release=lambda x: (
                            self.save_data(new_event_name=text_input.text.strip() if text_input.text.strip() else None),
                            self.dialog.dismiss()  # Automatically close the dialog after saving
                        ),
                        theme_text_color="Custom",          # Make the text color custom
                        text_color=(0, 0.4, 1, 1)           # Blue color for SAVE button
                    ),
                ],
            )

        self.dialog.open()

    def save_data(self, new_event_name=None):
        if hasattr(self, "current_data") and self.current_data:
            # Filter out rows where all values after "Target" are "---"
            header = self.current_data[0]
            filtered_data = [header]
            for row in self.current_data[1:]:
                values_after_target = [v for k, v in row.items() if k != "Target"]
                if not all(str(v).strip() == "---" for v in values_after_target):
                    filtered_data.append(row)
            self.current_data = filtered_data
            # Determine the private storage path
            storage_path = self.get_private_storage_path()
            if storage_path:
                try:
                    # Ensure the CSV folder exists
                    csv_folder_path = os.path.join(storage_path, "CSV")
                    if not os.path.exists(csv_folder_path):
                        os.makedirs(csv_folder_path)

                    # Construct the file name and path
                    file_name = f"{self.root.ids.home_screen.ids.cartridge_name_field.text}.csv"
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
                        toast("No folder selected or created. Cannot save data.")
                        return

                    # Write the data to the CSV file
                    with open(file_path, mode="w", encoding="utf-8", newline="") as csv_file:
                        writer = csv.writer(csv_file)

                        # Add 6 empty rows as the header
                        for _ in range(5):
                            writer.writerow([])

                        # Write the headers
                        headers = ["Projectile", "Powder", "Charge", "Primer", "Brass", "Headspace", "Ogive", "OAL", "Velocity"]
                        writer.writerow(headers)

                        # Write the data rows
                        for row in self.current_data:
                            writer.writerow([row.get(h, "") for h in headers])

                        # Write the Cartridge notes as the footer
                        cartridge_notes = self.root.ids.home_screen.ids.cartridge_notes_field.text.strip()
                        if cartridge_notes:
                            writer.writerow([])  # Add an empty row before the footer
                            writer.writerow(["Cartridge Notes:"])
                            writer.writerow([cartridge_notes])

                        print(f"Data saved to: {file_path}")
                        toast(f"Data saved")

                        # Refresh the FileChooserListView
                        saved_cartridges_screen = self.root.ids.screen_manager.get_screen("saved_cartridges")
                        self.populate_swipe_file_list()
                        print("File and folder list refreshed.")
                except Exception as e:
                    print(f"Error saving data to CSV: {e}")
                    toast(f"Error saving data: {e}")
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
            self.config_parser.set("Settings", "display_model", self.selected_display)
            self.config_parser.set("Settings", "orientation", self.selected_orientation)
            self.config_parser.set("Settings", "standalone_mode", str(self.standalone_mode_enabled))
            # Save sort settings
            self.config_parser.set("Settings", "sort_type", getattr(self, "sort_type", "date"))
            self.config_parser.set("Settings", "sort_order", getattr(self, "sort_order", "asc"))
            self.config_parser.set("Settings", "delete_folders_after", getattr(self, "delete_folders_after", "never"))
            self.config_parser.set("Settings", "manage_data_dialog_shown", str(getattr(self, "manage_data_dialog_shown", False)))
            with open(self.config_file, "w") as config_file:
                self.config_parser.write(config_file)
            print("Settings saved successfully.")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_settings(self):
        try:
            self.config_parser.read(self.config_file)
            if self.config_parser.has_option("Settings", "display_model"):
                self.selected_display = self.config_parser.get("Settings", "display_model")
            if self.config_parser.has_option("Settings", "orientation"):
                self.selected_orientation = self.config_parser.get("Settings", "orientation")
            # Set native_resolution and selected_resolution based on loaded display/orientation
            display_resolutions = {
                "Good Display 3.7-inch": (240, 416),
                "Good Display 4.2-inch": (300, 400),
                "Good Display 2.9-inch": (128, 296),
            }
            self.native_resolution = display_resolutions.get(self.selected_display, (240, 416))
            self.selected_resolution = self.native_resolution  # Always portrait
            print(f"Loaded settings: display_model={self.selected_display}, orientation={self.selected_orientation}, ...")
            print(f"Loaded native_resolution: {self.native_resolution}, selected_resolution: {self.selected_resolution}")
        except Exception as e:
            print(f"Error loading settings: {e}")
        self.delete_folders_after = self.config_parser.get("Settings", "delete_folders_after", fallback="never")
        labels = {
            "week": "After 1 week",
            "month": "After 1 month",
            "year": "After 1 year",
            "never": "Never",
        }
        self.delete_option_label = labels.get(self.delete_folders_after, "Delete Folders After")
        # Load sort settings
        self.sort_type = self.config_parser.get("Settings", "sort_type", fallback="date")
        self.sort_order = self.config_parser.get("Settings", "sort_order", fallback="asc")
        print(f"Loaded sort_type: {self.sort_type}, sort_order: {self.sort_order}")

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
            display_width, display_height = 240, 416

            # Load the font file (ensure the font file is in the correct path)
            font_path = os.path.join(os.path.dirname(__file__), "assets", "fonts", "RobotoMono-Regular.ttf")
            font = ImageFont.truetype(font_path, 20)  # Load the font file

            # 1. Always draw at portrait base size
            base_width, base_height = 240, 416
            image = Image.new("RGB", (base_width, base_height), "white")
            draw = ImageDraw.Draw(image)

            # Add the cartridge name at the top
            cartridge_name = self.root.ids.home_screen.ids.cartridge_name_field.text  # Get the cartridge name from the text field
            y = 10  # Starting vertical position
            text_bbox = draw.textbbox((0, 0), cartridge_name, font=font)  # Get the bounding box of the text
            text_width = text_bbox[2] - text_bbox[0]  # Calculate the text width
            x = (base_width - text_width) // 2  # Center the text horizontally
            draw.text((x, y), cartridge_name, fill="black", font=font)
            y += 20  # Add some spacing after the cartridge name

            # Draw a horizontal line under the cartridge name
            draw.line((10, y, base_width - 10, y), fill="black", width=1)
            y += 20  # Add some spacing after the line

            # --- Use the same headers as display_table ---
            headers = ["Projectile", "Powder", "Charge", "Primer", "Brass", "Headspace", "Ogive", "OAL", "Velocity"]

            # Transpose data for column display (each field is a row, each value is a column)
            table_rows = []
            for header in headers:
                row = [header] + [str(row.get(header, "")) for row in csv_data]
                table_rows.append(row)

            # Calculate the maximum width for each column
            num_columns = max(len(row) for row in table_rows)
            column_widths = [0] * num_columns
            for row in table_rows:
                for i, cell in enumerate(row):
                    column_widths[i] = max(column_widths[i], len(cell))

            # Draw the table as columns (vertical) onto the bitmap
            for row in table_rows:
                row_text = " | ".join(
                    f"{cell:<{column_widths[i]}}" for i, cell in enumerate(row)
                )
                text_bbox = draw.textbbox((0, 0), row_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                x = (base_width - text_width) // 2
                draw.text((x, y), row_text, fill="black", font=font)
                y += 20  # Move down for the next row

            # Get the cartridge notes from the UI
            cartridge_notes = self.root.ids.home_screen.ids.cartridge_notes_field.text.strip()

            # Add spacing before notes
            y += 10

            # Draw a horizontal line before notes
            draw.line((10, y, base_width - 10, y), fill="black", width=1)
            y += 10

            # Draw the "Cartridge Notes:" header
            notes_header = "Cartridge Notes:"
            text_bbox = draw.textbbox((0, 0), notes_header, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            x = (base_width - text_width) // 2
            draw.text((x, y), notes_header, fill="black", font=font)
            y += 20

            # Draw the notes text, wrapping if needed
            if cartridge_notes:
                import textwrap
                wrapped_lines = textwrap.wrap(cartridge_notes, width=38)  # Adjust width as needed
                for line in wrapped_lines:
                    text_bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    x = (base_width - text_width) // 2
                    draw.text((x, y), line, fill="black", font=font)
                    y += 18  # Adjust line spacing as needed

            # 2. Determine the final output size based on orientation and selected display
            portrait_resolution = self.selected_resolution  # e.g., (240, 416) for 3.7"
            if self.selected_orientation == "Landscape":
                final_resolution = (portrait_resolution[1], portrait_resolution[0])  # e.g., (416, 240)
            else:
                final_resolution = portrait_resolution  # e.g., (240, 416)
    
            # 3. Resize to the final resolution (this will stretch/squash if needed)
            image = image.resize(final_resolution, Image.LANCZOS)
    
            # Save the resized image as a bitmap
            bw_image = image.convert("1")  # Convert to 1-bit pixels
            bw_image.save(output_path)
            print(f"Bitmap saved to {output_path}")
            print(f"Bitmap dimensions: {bw_image.size}")
            return output_path
        except Exception as e:
            print(f"Error converting CSV to bitmap: {e}")
            return None
    def navigate_to_home(self):
        """Navigate back to the home screen."""
        self.root.ids.screen_manager.current = "home"

    # search functionality below
    def on_search_entered(self, search_text):
        """Filter the swipe-to-delete file list based on the search input."""
        self.search_text = search_text.strip().lower() if search_text else ""
        self.populate_swipe_file_list()

    def limit_cartridge_notes(self, text_field):
        """Limit the cartridge notes to 2 lines."""
        max_lines = 2
        lines = text_field.text.split("\n")
        if len(lines) > max_lines:
            # Trim the text to the first 2 lines
            text_field.text = "\n".join(lines[:max_lines])
            text_field.cursor = (len(text_field.text), 0)  # Reset the cursor position

    def open_display_dropdown(self, button):
        """Open the dropdown menu for selecting a display model."""
        # Define the available display models with their resolutions (always portrait)
        display_models = [
            {"text": "Good Display 3.7-inch", "resolution": (240, 416),
             "on_release": lambda: self.set_display_model("Good Display 3.7-inch", (240, 416))},
            {"text": "Good Display 4.2-inch", "resolution": (300, 400),
             "on_release": lambda: self.set_display_model("Good Display 4.2-inch", (300, 400))},
            {"text": "Good Display 2.9-inch", "resolution": (128, 296),
             "on_release": lambda: self.set_display_model("Good Display 2.9-inch", (128, 296))},
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
        self.selected_display = model
        self.native_resolution = resolution  # Always portrait, e.g., (128, 296)
        self.selected_resolution = resolution  # Always portrait
        self.root.ids.settings_screen.ids.display_dropdown_button.text = f"{model}"
        print(f"Selected display model: {model} with native resolution {self.selected_resolution}")
        self.save_settings()
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
        self.selected_orientation = orientation
        self.root.ids.settings_screen.ids.orientation_dropdown_button.text = orientation
        print(f"Selected orientation: {orientation}")
        # Always keep selected_resolution as portrait
        display_resolutions = {
            "Good Display 3.7-inch": (240, 416),
            "Good Display 4.2-inch": (300, 400),
            "Good Display 2.9-inch": (128, 296),
        }
        if not hasattr(self, "native_resolution") or self.native_resolution is None:
            self.native_resolution = display_resolutions.get(self.selected_display, (240, 416))
        self.selected_resolution = self.native_resolution  # Always portrait
        self.save_settings()
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
        """Handle NFC tags."""
        if is_android() and autoclass:
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
                    tag = cast('android.nfc.Tag', tag)
                    tech_list = tag.getTechList()
                    print("Tag technologies detected by Android:")
                    for tech in tech_list:
                        print(f" - {tech}")
                        home_screen = self.root.ids.home_screen
                    table_container = home_screen.ids.table_container
                    # If manual data input is displayed (BoxLayout with MDRaisedButton "ADD" present)
                    if (
                        table_container.children
                        and hasattr(self, "manual_data_rows")
                        and self.manual_data_rows
                        and any(
                            any(field.text.strip() for field in row_fields.values())
                            for row_fields in self.manual_data_rows
                        )
                    ):
                        print("Manual data input detected, adding manual data before NFC transfer.")
                        self.add_manual_data()
                    Clock.schedule_once(lambda dt: self.show_nfc_progress_dialog("Transferring data to NFC tag..."))
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

                    # NEW: Get the tag ID and UID
                    if tag:
                        tag_id = tag.getId()
                        tag_uid = ''.join('{:02X}'.format (byte) for byte in tag_id)
                        print(f"Tag UID: {tag_uid}")
                        # Optionally update a label in your UI

                    self.send_csv_bitmap_via_nfc(intent)
                    return  # Optionally return here if you don't want to process further

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
            base_dir = os.path.abspath(self.get_private_storage_path())
            abs_path = os.path.abspath(path)
            saved_cartridges_screen = self.root.ids.screen_manager.get_screen("saved_cartridges")

            # If deleting a folder or a non-csv file, always go to assets/CSV first
            if not abs_path.lower().endswith(".csv"):
                csv_root = self.ensure_csv_directory()
                self.populate_swipe_file_list()

            if os.path.exists(abs_path):
                if os.path.isdir(abs_path):
                    shutil.rmtree(abs_path)  # Recursively delete folder and contents
                    print(f"Deleted folder: {abs_path}")
                    toast("Folder deleted successfully.")
                else:
                    os.remove(abs_path)
                    print(f"Deleted file: {abs_path}")
                    toast("File deleted successfully.")

                # Refresh the swipe-to-delete file list
                self.populate_swipe_file_list()
                print("File and folder list refreshed.")

                self.clear_table_data()
                self.root.ids.screen_manager.current = "saved_cartridges"
            else:
                print(f"Path does not exist: {abs_path}")
        except Exception as e:
            print(f"Error deleting file or folder: {e}")

    def populate_swipe_file_list(self, target_dir=None, sort_by=None, reverse=None):
        saved_cartridges_screen = self.root.ids.screen_manager.get_screen("saved_cartridges")
        swipe_file_list = saved_cartridges_screen.ids.swipe_file_list
        swipe_file_list.clear_widgets()

        if target_dir is None:
            target_dir = self.ensure_csv_directory()

        # Add parent directory entry if not at root
        root_dir = self.ensure_csv_directory()
        if os.path.abspath(target_dir) != os.path.abspath(root_dir):
            parent_dir = os.path.abspath(os.path.join(target_dir, ".."))
            item = Builder.load_string(f'''
SwipeFileItem:
    file_path: r"{parent_dir}"
    icon: "arrow-left"
    file_size: ""
    display_name: "Back"
''')
            swipe_file_list.add_widget(item)

        entries = []
        for fname in os.listdir(target_dir):
            if fname.startswith('.'):
                continue  # Skip hidden files/folders
            # --- Filter by search_text ---
            if self.search_text and self.search_text not in fname.lower():
                continue
            fpath = os.path.abspath(os.path.join(target_dir, fname))
            is_dir = os.path.isdir(fpath)
            size = "" if is_dir else str(os.path.getsize(fpath))
            icon = "folder" if is_dir else "file"
            entries.append((fpath, icon, size, fname))

        # Sorting logic
        if sort_by == "name":
            entries.sort(key=lambda x: (x[1] != "folder", x[3].lower()), reverse=reverse)
        elif sort_by == "date":
            entries.sort(key=lambda x: (x[1] != "folder", os.path.getmtime(x[0])), reverse=reverse)
        elif sort_by == "type":
            entries.sort(key=lambda x: (x[1] != "folder", os.path.splitext(x[3])[1].lower(), x[3].lower()), reverse=reverse)

        for fpath, icon, size, fname in entries:
            item = Builder.load_string(f'''
SwipeFileItem:
    file_path: r"{fpath}"
    icon: "{icon}"
    file_size: "{size}"
''')
            swipe_file_list.add_widget(item)

    def show_manual_data_input(self):
        """Display manual data input fields for reloading data."""
        home_screen = self.root.ids.home_screen
        table_container = home_screen.ids.table_container
        table_container.clear_widgets()

        # Define fields
        reloading_fields = {
            "Projectile": {"hint_text": "Projectile", "show": True},
            "Powder": {"hint_text": "Powder", "show": True},
            "Charge": {"hint_text": "Charge (gr)", "show": True},
            "Primer": {"hint_text": "Primer", "show": True},
            "Brass": {"hint_text": "Brass", "show": True},
            "Headspace": {"hint_text": "Headspace (in)", "show": True},
            "Ogive": {"hint_text": "Ogive (in)", "show": True},
            "OAL": {"hint_text": "OAL (in)", "show": True},
            "Velocity": {"hint_text": "Velocity (fps)", "show": True},
        }
        self.available_fields = reloading_fields

        # Create a main layout for all manual data rows and buttons
        main_layout = BoxLayout(orientation="vertical", spacing="10dp", size_hint=(1, None))
        main_layout.bind(minimum_height=main_layout.setter("height"))

        # Add the first row of input fields to main_layout
        self.add_data_row(main_layout)

        # Add buttons for adding/deleting rows as before...
        add_row_layout = BoxLayout(
            orientation="horizontal",
            spacing="10dp",
            size_hint=(None, None),
            height=dp(50),
        )
        add_row_layout.width = dp(260)
        add_row_layout.pos_hint = {"center_x": 0.5}
        main_layout.add_widget(add_row_layout)

        # Add main_layout to the scrollable table_container
        table_container.add_widget(main_layout)

    def add_data_row(self, parent_layout):
        """Add a new row of data fields as a vertical column, centered."""
        row_fields = {}
        for field_name, field_options in self.available_fields.items():
            if field_options["show"]:
                text_field = MDTextField(
                    hint_text=field_options["hint_text"],
                    multiline=False,
                    size_hint_x=0.8,
                    pos_hint={"center_x": 0.5},
                )
                row_fields[field_name] = text_field
                parent_layout.add_widget(text_field)  # <-- Add directly to parent_layout

        if not hasattr(self, "manual_data_rows"):
            self.manual_data_rows = []
        self.manual_data_rows.append(row_fields)

        # Insert above the button layout
        button_index = 0
        for i, child in enumerate(reversed(parent_layout.children)):
            if isinstance(child, BoxLayout) and any(
                    isinstance(widget, MDRaisedButton) or isinstance(widget, MDFlatButton) for widget in child.children):
                button_index = len(parent_layout.children) - i
                break

    def add_manual_data(self):
        """Add the manually entered reloading data to the current data and display it."""
        try:
            for row_fields in self.manual_data_rows:
                # Initialize the row with all columns, defaulting to empty string
                manual_data = {key: "" for key in self.available_fields.keys()}

                # Populate the row with data from the input fields
                for key, field in row_fields.items():
                    manual_data[key] = field.text.strip()

                # Validate the data (optional, e.g., Powder and Charge required)
                if not manual_data["Powder"] or not manual_data["Charge"]:
                    toast("Powder and Charge are required.")
                    return

                # Add the data to the current data
                if not hasattr(self, "current_data") or not self.current_data:
                    self.current_data = []
                self.current_data.append(manual_data)

            # Display the updated data
            self.display_table(self.current_data)

            # Clear the input fields
            self.cancel_manual_data_input()
            print("Manual reloading data added:", self.current_data)
        except Exception as e:
            print(f"Error adding manual reloading data: {e}")

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
                    # Recursively copy the directory
                    self.copy_directory_from_assets(asset_manager, sub_source_path, sub_dest_path)
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
                    print(f"Copied file: {sub_src_path} to {dest_path}")
        except Exception as e:
            print(f"Error copying directory locally: {e}")

    def hide_nfc_progress_dialog(self):
        if hasattr(self, "nfc_progress_dialog") and self.nfc_progress_dialog:
            self.nfc_progress_dialog.dismiss()
            self.nfc_progress_dialog = None
        # Call self.hide_nfc_progress_dialog() at the end of your NFC transfer logic
    def update_nfc_progress(self, percent):
        if hasattr(self, "nfc_progress_bar") and self.nfc_progress_bar:
            # If percent is 100, delay the update by 3 seconds
            if percent >= 100:
                Clock.schedule_once(lambda dt: self._finish_nfc_progress(), 3)
            else:
                self.nfc_progress_bar.value = percent

    def _finish_nfc_progress(self):
        if hasattr(self, "nfc_progress_bar") and self.nfc_progress_bar:
            self.nfc_progress_bar.value = 100
        if hasattr(self, "nfc_progress_label"):
            self.nfc_progress_label.text = "Transfer successful!"
            self.nfc_progress_label.color = (0, 0.6, 0, 1)
        Clock.schedule_once(lambda dt: self.hide_nfc_progress_dialog(), 1.5)
        self.clear_table_data()  # Clear the table data after transfer

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


s = MainApp.EPD_INIT_MAP["Good Display 3.7-inch"][0]
print("Length:", len(s))
for i, c in enumerate(s):
    if not c.isalnum():
        print(f"Non-alphanumeric at {i}: {repr(c)}")
for i in range(0, len(s), 40):
    print(f"{i:03d}: {s[i:i+40]}")

def pack_image_column_major(img):
    """Convert a 1bpp PIL image to column-major, 8-pixels-per-byte format."""
    width, height = img.size
    pixels = img.load()
    packed = bytearray()
    for x in range(width-1, -1, -1):  # right-to-left to match demo
        for y_block in range(0, height, 8):
            byte = 0
            for bit in range(8):
                y = y_block + bit
                if y >= height:
                    continue
                # In '1' mode, 0=black, 255=white
                if pixels[x, y] == 0:
                    byte |= (1 << (7 - bit))
            packed.append(byte)
    return bytes(packed)
if __name__ == "__main__":
    MainApp().run()