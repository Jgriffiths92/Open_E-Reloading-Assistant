package com.openedope.open_edope;

import android.content.Intent;
import org.kivy.android.PythonActivity;

public class NfcIntentHandler extends PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent); // Always call super

        // Debug logging for received intent
        if (intent == null) {
            Log.d("NfcIntentHandler", "onNewIntent called with null intent");
            return;
        }

        String action = intent.getAction();
        Log.d("NfcIntentHandler", "onNewIntent received action: " + action);

        // Log extras if any
        if (intent.getExtras() != null) {
            Log.d("NfcIntentHandler", "Extras: " + intent.getExtras().toString());
        } else {
            Log.d("NfcIntentHandler", "No extras in intent");
        }

        // Log NFC tag info if present
        android.os.Parcelable tag = intent.getParcelableExtra("android.nfc.extra.TAG");
        if (tag != null) {
            Log.d("NfcIntentHandler", "TAG extra found in intent: " + tag.toString());
        } else {
            Log.d("NfcIntentHandler", "No TAG extra in intent");
        }

        // Place for further intent handling or Python call
        // Example: if mService exists
        mService.postToPython("on_new_intent", intent);
    }
}