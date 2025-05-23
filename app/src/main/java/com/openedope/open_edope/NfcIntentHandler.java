package com.openedope.open_edope;

import android.content.Intent;
import org.kivy.android.PythonActivity;

public class NfcIntentHandler extends PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent); // Always call super

        // If you need to notify Python code, use JNI, services, or a Python event
        // Example (if mService exists):
        // mService.postToPython("on_new_intent", intent);
    }
}