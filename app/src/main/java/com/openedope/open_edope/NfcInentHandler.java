import android.content.Intent;

public class MyActivity extends org.kivy.android.PythonActivity {
    @Override
    public void onNewIntent(Intent intent) {
        // Pass intent to Python
        PythonActivity.mService.postToPython("on_new_intent", intent);
        super.onNewIntent(intent);
    }
}