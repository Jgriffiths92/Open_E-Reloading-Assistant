package com.openedope.open_edope;

import org.kivy.android.PythonActivity;
import org.kivy.android.PythonUtil; // Add this import
import android.content.Intent;
import android.os.Bundle;

public class MyNfcActivity extends PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        // Use PythonUtil to get the Python instance
        PythonUtil.getInstance().callAttr("on_new_nfc_intent_from_java", intent);
    }
}