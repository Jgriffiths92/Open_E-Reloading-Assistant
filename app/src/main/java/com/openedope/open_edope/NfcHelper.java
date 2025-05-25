package com.openedope.open_edope;


import android.content.Intent;
import android.nfc.NfcAdapter;
import android.nfc.Tag;
import android.nfc.tech.NfcA;
import android.os.Parcelable;
import android.util.Log;

public class NfcHelper {

    public static String data_DB = "F0DB000069";
    public static String start = "A00603300190012C";
    public static String RST = "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40108" + "A502000A"
            + "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40103";
    public static String set_wf = "A102000F";
    public static String set_power = "A10104" + "A40103";
    public static String set_resolution = "A105610190012C";
    public static String set_border = "A1025097";
    public static String write_BW = "A3021013";
    public static String write_BWR = "A3021013";
    public static String update = "A20112" + "A502000A" + "A40103";
    public static String sleep = "A20102" + "A40103" + "A20207A5";

    public static String[] epd_init = new String[]{
            data_DB + start + RST + set_wf + set_resolution + set_border + set_power + write_BWR + update + sleep,
            data_DB + start + RST + set_wf + set_resolution + set_border + set_power + write_BWR + update + sleep,
            "F0DA000003F00330"
    };

    public static void processNfcIntent(Intent intent, int width, int height, byte[] imageBuffer, String[] epdInit) {
          Log.e("NfcHelper", "processNfcIntent CALLED");
        Parcelable p = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG);
        if (p == null) return;
        Tag tag = (Tag) p;
        NfcA nfcA = NfcA.get(tag);
        if (nfcA != null) {
            try {
                Log.e("debug", "intent");
                nfcA.connect();
                byte[] cmd;
                byte[] response;
                nfcA.setTimeout(60000);

                cmd = hexStringToBytes(epdInit[0]);
                response = nfcA.transceive(cmd);
                Log.e("epdinit_state", hexToString(response));

                cmd = hexStringToBytes(epdInit[1]);
                response = nfcA.transceive(cmd);
                Log.e("epdinit_state", hexToString(response));

                int datas = width0 * height0 / 8;
                for (int i = 0; i < datas / 250; i++) {
                    cmd = new byte[255];
                    cmd[0] = (byte) 0xF0;
                    cmd[1] = (byte) 0xD2;
                    cmd[2] = 0x00;
                    cmd[3] = (byte) i;
                    cmd[4] = (byte) 0xFA;
                    for (int j = 0; j < 250; j++) {
                        cmd[j + 5] = imageBuffer[j + 250 * i];
                    }
                    response = nfcA.transceive(cmd);
                    Log.e((i + 1) + " sendData_state:", hexToString(response));
                }

                byte[] refreshCmd = new byte[]{(byte) 0xF0, (byte) 0xD4, 0x05, (byte) 0x80, 0x00};
                response = nfcA.transceive(refreshCmd);
                Log.e("RefreshData1_state:", hexToString(response));
                if (response[0] != (byte) 0x90) {
                    response = nfcA.transceive(refreshCmd);
                    Log.e("RefreshData2_state:", hexToString(response));
                }
            } catch (Exception e) {
                e.printStackTrace();
                Log.e("debug", "Exception in processNfcIntent: " + e);
            } finally {
                try {
                    nfcA.close();
                } catch (Exception ignored) {}
            }
        }
    }

    // Utility: Convert hex string to byte array
    public static byte[] hexStringToBytes(String s) {
        int len = s.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(s.charAt(i), 16) << 4)
                    + Character.digit(s.charAt(i+1), 16));
        }
        return data;
    }

    // Utility: Convert byte array to hex string
    public static String hexToString(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02X", b));
        }
        return sb.toString();
    }
}