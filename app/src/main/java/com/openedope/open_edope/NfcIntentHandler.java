package com.openedope.open_edope;

import android.content.Intent;
import android.util.Log;
import org.kivy.android.PythonActivity;    // import this if not already imported
import org.kivy.android.PythonUtil;        // may be used for calling Python code

public class NfcIntentHandler extends PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);

        // Logging/debugging
        Log.d("NfcIntentHandler", "onNewIntent received action: " + intent.getAction());

        // Send a custom broadcast with the NFC intent
        Intent broadcast = new Intent("com.openedope.open_edope.NFC_EVENT");
        broadcast.putExtra("action", intent.getAction());
        // You can add more extras as needed
        sendBroadcast(broadcast);
    }
}