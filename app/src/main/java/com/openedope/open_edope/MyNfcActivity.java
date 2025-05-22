package com.openedope.open_edope;

import org.kivy.android.PythonActivity;
import org.kivy.android.PythonUtil;
import android.content.Intent;

public class MyNfcActivity extends PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        PythonUtil.callPython("on_new_nfc_intent_from_java", intent);
    }
}