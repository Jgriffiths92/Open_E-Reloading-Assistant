package com.openedope.open_edope;

import android.content.Intent;
import android.util.Log;

public class NfcIntentHandler extends PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent); // Always call super

        // Logging/debugging as before
        Log.d("NfcIntentHandler", "onNewIntent received action: " + intent.getAction());

        // Do NOT call Python.getInstance()...
        // Instead, rely on existing bridges or handlers
        // Example: If you have a method in Python exposed via JNI, call it here using the correct API.
    }
}