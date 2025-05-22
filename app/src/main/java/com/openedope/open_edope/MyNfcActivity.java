package com.openedope.open_edope;

import org.kivy.android.PythonActivity;
import android.content.Intent;
import android.os.Bundle;

public class MyNfcActivity extends PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        // Call Python code via PythonActivity's Python instance
        org.kivy.android.PythonActivity.mService.getPython().callAttr("on_new_nfc_intent_from_java", intent);
    }
}