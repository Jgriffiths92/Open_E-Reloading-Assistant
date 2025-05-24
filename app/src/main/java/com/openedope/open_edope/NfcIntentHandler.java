package com.openedope.open_edope;

import android.content.Intent;
import android.util.Log;
import org.kivy.android.PythonActivity;    // import this if not already imported
import org.kivy.android.PythonUtil;        // may be used for calling Python code

public class NfcIntentHandler extends PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent); // Always call super

        // Logging/debugging
        Log.d("NfcIntentHandler", "onNewIntent received action: " + intent.getAction());

        // Call Python function on_new_intent with the Intent action
        PythonActivity pythonActivity = (PythonActivity) this;
        // Chaquopy way:
        // pythonActivity.getPython().getModule("main").callAttr("on_new_intent", intent.getAction());

        // PyJNIus way:
        try {
            // Get the Python instance
            org.kivy.android.Python py = org.kivy.android.Python.getInstance();
            // Get the main Python module (usually "main")
            py.getModule("main").callAttr("on_new_intent", intent);
        } catch (Exception e) {
            Log.e("NfcIntentHandler", "Failed to call on_new_intent", e);
        }
    }
}