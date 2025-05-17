package com.openedope.NfcImageSender;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.nfc.NfcAdapter;
import android.nfc.Tag;
import android.nfc.tech.IsoDep;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;

import java.io.IOException;
import java.io.InputStream;

public class NfcImageSender {
    private NfcAdapter mNfcAdapter;
    private PendingIntent mNfcPendingIntent;
    private IntentFilter[] mWriteTagFilters;
    private Activity activity;
    private TextView resultTextView; // Optional: for UI feedback

    public NfcImageSender(Activity activity, TextView resultTextView) {
        this.activity = activity;
        this.resultTextView = resultTextView;
        mNfcAdapter = NfcAdapter.getDefaultAdapter(activity);
        IntentFilter tagDetected = new IntentFilter(NfcAdapter.ACTION_TAG_DISCOVERED);
        mWriteTagFilters = new IntentFilter[]{tagDetected};
        mNfcPendingIntent = PendingIntent.getActivity(activity, 0,
                new Intent(activity, activity.getClass()).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP), PendingIntent.FLAG_MUTABLE);
    }

    public void enableForegroundDispatch() {
        if (mNfcAdapter != null)
            mNfcAdapter.enableForegroundDispatch(activity, mNfcPendingIntent, mWriteTagFilters, null);
    }

    public void disableForegroundDispatch() {
        if (mNfcAdapter != null)
            mNfcAdapter.disableForegroundDispatch(activity);
    }

    public void onNewIntent(Intent intent, Bitmap bitmap, int epdColor, int epdInch, int epdIC) {
        if (NfcAdapter.ACTION_TAG_DISCOVERED.equals(intent.getAction())) {
            Tag detectedTag = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG);
            new Thread(() -> writeTag(detectedTag, bitmap, epdColor, epdInch, epdIC)).start();
        }
    }

    private void writeTag(Tag tag, Bitmap bitmap, int epdColor, int epdInch, int epdIC) {
        String[] tech = tag.getTechList();
        if (tech.length == 0 || !tech[0].equals("android.nfc.tech.IsoDep")) return;
        IsoDep isodep = IsoDep.get(tag);
        try {
            isodep.setTimeout(50000);
            if (!isodep.isConnected()) isodep.connect();
            if (isodep.isConnected()) {
                // 1. IC DIY DB instruction
                byte[] cmd = HexString2Bytes("F0DB020000");
                byte[] response = isodep.transceive(cmd);

                // 2. Electronic paper parameter writing
                cmd = HexString2Bytes(data.setEpdInit(epdColor, epdInch)[0]);
                response = isodep.transceive(cmd);

                // 3. Screen cutting
                cmd = HexString2Bytes(data.setEpdInit(epdColor, epdInch)[1]);
                response = isodep.transceive(cmd);

                // 4. Image transmission (example for BW, adapt for color as needed)
                bitmap = activity_imageview.rotateBitmap(bitmap, 90); // Rotate if needed
                int width0 = bitmap.getWidth();
                int height0 = bitmap.getHeight();
                byte[] image_buffer = activity_imageview.GetPictureData_SSD(bitmap, 0); // mode=0 for BW

                int datas = width0 * height0 / 8;
                int ScreenIndex_BW = 0;
                for (int i = 0; i < datas / 250; i++) {
                    cmd = new byte[255];
                    cmd[0] = (byte) 0xF0;
                    cmd[1] = (byte) 0xD2;
                    cmd[2] = (byte) ScreenIndex_BW;
                    cmd[3] = (byte) i;
                    cmd[4] = (byte) 0xFA;
                    System.arraycopy(image_buffer, i * 250, cmd, 5, 250);
                    response = isodep.transceive(cmd);
                }
                // Send tail if needed
                if (datas % 250 != 0) {
                    int i = datas / 250;
                    cmd = new byte[255];
                    cmd[0] = (byte) 0xF0;
                    cmd[1] = (byte) 0xD2;
                    cmd[2] = (byte) ScreenIndex_BW;
                    cmd[3] = (byte) i;
                    cmd[4] = (byte) 0xFA;
                    System.arraycopy(image_buffer, i * 250, cmd, 5, datas % 250);
                    response = isodep.transceive(cmd);
                }

                // 5. Refresh command
                byte[] refreshcmd = new byte[5];
                refreshcmd[0] = (byte) 0xF0;
                refreshcmd[1] = (byte) 0xD4;
                refreshcmd[2] = (byte) 0x05;
                refreshcmd[3] = (byte) 0x80;
                refreshcmd[4] = (byte) 0x00;
                response = isodep.transceive(refreshcmd);

                // UI feedback (optional)
                if (resultTextView != null) {
                    new Handler(Looper.getMainLooper()).post(() ->
                            resultTextView.setText("NFC transfer complete!"));
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            try { isodep.close(); } catch (Exception ignored) {}
        }
    }

    // Utility: Convert hex string to byte array
    public static byte[] HexString2Bytes(String hexstr) {
        char[] charArray = hexstr.toCharArray();
        byte[] b = new byte[hexstr.length() / 2];
        int j = 0;
        for (int i = 0; i < b.length; i++) {
            char c0 = charArray[j++];
            char c1 = charArray[j++];
            b[i] = (byte) ((parse(c0) << 4) | parse(c1));
        }
        return b;
    }
    private static int parse(char c) {
        if (c >= 'a') return (c - 'a' + 10) & 0x0f;
        if (c >= 'A') return (c - 'A' + 10) & 0x0f;
        return (c - '0') & 0x0f;
    }

    // MainActivity inner class or separate file
    public static class MainActivity extends Activity {
        private NfcImageSender nfcImageSender;

        @Override
        protected void onCreate(Bundle savedInstanceState) {
            super.onCreate(savedInstanceState);
            // ...your existing setup...

            // Example: Load output.bmp from assets/bitmap
            Bitmap outputBitmap = loadBitmapFromAssets("bitmap/output.bmp");

            // Initialize NfcImageSender (pass null if you don't use a TextView for feedback)
            nfcImageSender = new NfcImageSender(this, null);

            // Example: When you want to send via NFC, call:
            // nfcImageSender.onNewIntent(intent, outputBitmap, epdColor, epdInch, epdIC);
        }

        private Bitmap loadBitmapFromAssets(String assetPath) {
            try {
                AssetManager assetManager = getAssets();
                InputStream istr = assetManager.open(assetPath);
                Bitmap bitmap = BitmapFactory.decodeStream(istr);
                istr.close();
                return bitmap;
            } catch (Exception e) {
                e.printStackTrace();
                return null;
            }
        }

        // When you receive an NFC intent:
        @Override
        protected void onNewIntent(Intent intent) {
            super.onNewIntent(intent);
            Bitmap outputBitmap = loadBitmapFromAssets("bitmap/output.bmp");
            // Set your e-paper parameters as needed
            int epdColor = 0, epdInch = 0, epdIC = 0;
            nfcImageSender.onNewIntent(intent, outputBitmap, epdColor, epdInch, epdIC);
        }
    }
}