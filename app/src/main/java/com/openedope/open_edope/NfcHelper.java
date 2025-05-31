package com.openedope.open_edope;


import android.content.Intent;
import android.nfc.NfcAdapter;
import android.nfc.Tag;
import android.nfc.tech.IsoDep;
import android.nfc.tech.NfcA;
import android.os.Parcelable;
import android.util.Log;

public class NfcHelper {

    private static PythonCallback progressCallback = null;

    // The following static fields and epd_init array are not used anywhere in this file.
    // If you do not reference them from other files, you can safely delete them.

    // public static String data_DB = "F0DB000069";
    // public static String start = "A00603300190012C";
    // public static String RST = "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40108" + "A502000A"
    //         + "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40103";
    // public static String set_wf = "A102000F";
    // public static String set_power = "A10104" + "A40103";
    // public static String set_resolution = "A105610190012C";
    // public static String set_border = "A1025097";
    // public static String write_BW = "A3021013";
    // public static String write_BWR = "A3021013";
    // public static String update = "A20112" + "A502000A" + "A40103";
    // public static String sleep = "A20102" + "A40103" + "A20207A5";

    // public static String[] epd_init = new String[]{
    //         data_DB + start + RST + set_wf + set_resolution + set_border + set_power + write_BWR + update + sleep,
    //         data_DB + start + RST + set_wf + set_resolution + set_border + set_power + write_BWR + update + sleep,
    //         "F0DA000003F00330"
    // };

    public static void processNfcIntent(Intent intent, int width0, int height0, byte[] image_buffer, String[] epd_init) {
        Log.e("NfcHelper", "processNfcIntent CALLED");
        Log.e("NfcHelper", "image_buffer class in processNfcIntent: " + image_buffer.getClass().getName());
        Parcelable p = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG);
        if (p == null) {
            Log.e("NfcHelper", "No NFC tag found in intent!");
            return;
        }
        Tag tag = (Tag) p;
        IsoDep isoDep = IsoDep.get(tag);
        if (isoDep != null) {
            try {
                isoDep.connect();
                Log.e("NfcHelper", "IsoDep connected: " + isoDep.isConnected());
                isoDep.setTimeout(60000);

                // Send DIY command before init
                byte[] diyCmd = hexStringToBytes("F0DB020000");
                byte[] response = isoDep.transceive(diyCmd);
                Log.e("diy_state", hexToString(response));

                // Now send the main init command as before
                byte[] cmd = hexStringToBytes(epd_init[0]);
                response = isoDep.transceive(cmd);
                Log.e("epdinit_state", hexToString(response));
                // Check for success (0x90 at end)
                if (response.length >= 2 && response[response.length - 2] == (byte) 0x90 && response[response.length - 1] == (byte) 0x00) {
                    Log.e("NfcHelper", "Init command success");
                } else {
                    Log.e("NfcHelper", "Init command failed");
                }

                cmd = hexStringToBytes(epd_init[1]);
                response = isoDep.transceive(cmd);
                Log.e("epdinit_state", hexToString(response));

                int datas = width0 * height0 / 8;
                int chunkSize = 250; // Increased chunk size to 250
                int maxRetries = 3;
                // Send BW buffer
                for (int i = 0; i < (datas + chunkSize - 1) / chunkSize; i++) {
                    int len = Math.min(chunkSize, datas - i * chunkSize);
                    cmd = new byte[5 + chunkSize];
                    cmd[0] = (byte) 0xF0;
                    cmd[1] = (byte) 0xD2;
                    cmd[2] = 0x00; // or 0x01 for R buffer
                    cmd[3] = (byte) i;
                    cmd[4] = (byte) chunkSize;
                    for (int j = 0; j < chunkSize; j++) {
                        if (j < len) {
                            cmd[j + 5] = image_buffer[j + chunkSize * i];
                        } else {
                            cmd[j + 5] = 0; // pad with zeros
                        }
                    }
                    int attempt = 0;
                    boolean success = false;
                    while (attempt < maxRetries && !success) {
                        try {
                            response = isoDep.transceive(cmd);
                            Log.e((i + 1) + " sendData_state:", hexToString(response));
                            success = true;
                            // --- ADD THIS ---
                            if (progressCallback != null) {
                                float progress = ((float)(i + 1) / (datas / chunkSize)) * 100f;
                                progressCallback.callback(progress);
                            }
                        } catch (Exception e) {
                            attempt++;
                            Log.e("NfcHelper", "Retry " + attempt + " for chunk " + i + ": " + e);
                            if (attempt == maxRetries) throw e;
                        }
                    }
                }

                // Send R buffer (inverted)
                for (int i = 0; i < (datas + chunkSize - 1) / chunkSize; i++) {
                    int len = Math.min(chunkSize, datas - i * chunkSize);
                    cmd = new byte[5 + chunkSize];
                    cmd[0] = (byte) 0xF0;
                    cmd[1] = (byte) 0xD2;
                    cmd[2] = 0x01; // R index
                    cmd[3] = (byte) i;
                    cmd[4] = (byte) chunkSize;
                    for (int j = 0; j < chunkSize; j++) {
                        if (j < len) {
                            cmd[j + 5] = (byte) ~image_buffer[j + chunkSize * i];
                        } else {
                            cmd[j + 5] = 0; // pad with zeros
                        }
                    }
                    int attempt = 0;
                    boolean success = false;
                    while (attempt < maxRetries && !success) {
                        try {
                            response = isoDep.transceive(cmd);
                            Log.e((i + 1) + " sendData_state:", hexToString(response));
                            success = true;
                        } catch (Exception e) {
                            attempt++;
                            Log.e("NfcHelper", "Retry " + attempt + " for chunk " + i + ": " + e);
                            if (attempt == maxRetries) throw e;
                        }
                    }
                }

                // Java, after the main chunk loop
                int tail = datas % chunkSize;
                if (tail != 0) {
                    cmd = new byte[5 + chunkSize];
                    cmd[0] = (byte) 0xF0;
                    cmd[1] = (byte) 0xD2;
                    cmd[2] = 0x00;
                    cmd[3] = (byte) (datas / chunkSize);
                    cmd[4] = (byte) chunkSize;
                    for (int j = 0; j < chunkSize; j++) {
                        if (j < tail) {
                            cmd[j + 5] = image_buffer[j + chunkSize * (datas / chunkSize)];
                        } else {
                            cmd[j + 5] = 0; // pad with zeros
                        }
                    }
                    response = isoDep.transceive(cmd);
                }

                // Send refresh command and check response
                byte[] refreshCmd = new byte[] {(byte)0xF0, (byte)0xD4, (byte)0x05, (byte)0x80, (byte)0x00};
                response = isoDep.transceive(refreshCmd);
                Log.e("RefreshData1_state:", hexToString(response));
                if (response.length >= 2 && response[response.length - 2] == (byte) 0x90 && response[response.length - 1] == (byte) 0x00) {
                    Log.e("NfcHelper", "Refresh command success");
                } else {
                    Log.e("NfcHelper", "Refresh command failed");
                }
                if (progressCallback != null) {
                    progressCallback.callback(100f);
                }
            } catch (Exception e) {
                Log.e("NfcHelper", "IsoDep Exception: " + e);
            } finally {
                try {
                    isoDep.close();
                } catch (Exception ignored) {}
            }
        } else {
            Log.e("NfcHelper", "IsoDep not supported, falling back to NfcA");
            NfcA nfcA = NfcA.get(tag);
            if (nfcA != null) {
                try {
                    int datas = width0 * height0 / 8; // <-- ADD THIS LINE
                    Log.e("NfcHelper", "Before connect, isConnected: " + nfcA.isConnected());
                    Log.e("NfcHelper", "Attempting to connect to NFC tag...");
                    nfcA.connect();
                    Log.e("NfcHelper", "After connect, isConnected: " + nfcA.isConnected());
                    Log.e("NfcHelper", "NFC tag connected: " + nfcA.toString());
                    Log.e("NfcHelper", "Tag timeout (ms): " + nfcA.getTimeout());
                    byte[] cmd;
                    byte[] response;
                    nfcA.setTimeout(60000);

                    // Send DIY command before init
                    byte[] diyCmd = hexStringToBytes("F0DB020000");
                    response = nfcA.transceive(diyCmd);
                    Log.e("diy_state", hexToString(response));

                    // Now send the main init command as before
                    cmd = hexStringToBytes(epd_init[0]);
                    response = nfcA.transceive(cmd);
                    Log.e("epdinit_state", hexToString(response));

                    cmd = hexStringToBytes(epd_init[1]);
                    response = nfcA.transceive(cmd);
                    Log.e("epdinit_state", hexToString(response));

                    if (image_buffer.length != datas) {
                        Log.e("NfcHelper", "WARNING: Image buffer size (" + image_buffer.length +
                              ") does not match expected size (" + datas + ") for " +
                              width0 + "x" + height0 + " display.");
                    }
                    int chunkSize = 250; // Increased chunk size to 250
                    int maxRetries = 3;
                    // Send BW buffer
                    for (int i = 0; i < (datas + chunkSize - 1) / chunkSize; i++) {
                        int len = Math.min(chunkSize, datas - i * chunkSize);
                        cmd = new byte[5 + chunkSize];
                        cmd[0] = (byte) 0xF0;
                        cmd[1] = (byte) 0xD2;
                        cmd[2] = 0x00; // BW index
                        cmd[3] = (byte) i;
                        cmd[4] = (byte) chunkSize;
                        for (int j = 0; j < chunkSize; j++) {
                            cmd[j + 5] = image_buffer[j + chunkSize * i];
                        }
                        int attempt = 0;
                        boolean success = false;
                        while (attempt < maxRetries && !success) {
                            try {
                                response = nfcA.transceive(cmd);
                                Log.e((i + 1) + " sendData_state:", hexToString(response));
                                success = true;
                                // --- ADD THIS ---
                                if (progressCallback != null) {
                                    float progress = ((float)(i + 1) / (datas / chunkSize)) * 100f;
                                    progressCallback.callback(progress);
                                }
                            } catch (Exception e) {
                                attempt++;
                                Log.e("NfcHelper", "Retry " + attempt + " for chunk " + i + ": " + e);
                                if (attempt == maxRetries) throw e;
                            }
                        }
                    }

                    // Send R buffer (inverted)
                    for (int i = 0; i < (datas + chunkSize - 1) / chunkSize; i++) {
                        int len = Math.min(chunkSize, datas - i * chunkSize);
                        cmd = new byte[5 + chunkSize];
                        cmd[0] = (byte) 0xF0;
                        cmd[1] = (byte) 0xD2;
                        cmd[2] = 0x01; // R index
                        cmd[3] = (byte) i;
                        cmd[4] = (byte) chunkSize;
                        for (int j = 0; j < chunkSize; j++) {
                            cmd[j + 5] = (byte) ~image_buffer[j + chunkSize * i];
                        }
                        int attempt = 0;
                        boolean success = false;
                        while (attempt < maxRetries && !success) {
                            try {
                                response = nfcA.transceive(cmd);
                                Log.e((i + 1) + " sendData_state:", hexToString(response));
                                success = true;
                            } catch (Exception e) {
                                attempt++;
                                Log.e("NfcHelper", "Retry " + attempt + " for chunk " + i + ": " + e);
                                if (attempt == maxRetries) throw e;
                            }
                        }
                    }

                    // Java, after the main chunk loop
                    int tail = datas % chunkSize;
                    if (tail != 0) {
                        cmd = new byte[5 + chunkSize];
                        cmd[0] = (byte) 0xF0;
                        cmd[1] = (byte) 0xD2;
                        cmd[2] = 0x00;
                        cmd[3] = (byte) (datas / chunkSize);
                        cmd[4] = (byte) chunkSize;
                        for (int j = 0; j < chunkSize; j++) {
                            if (j < tail) {
                                cmd[j + 5] = image_buffer[j + chunkSize * (datas / chunkSize)];
                            } else {
                                cmd[j + 5] = 0; // pad with zeros
                            }
                        }
                        response = nfcA.transceive(cmd);
                    }

                    // Send refresh command and check response
                    byte[] refreshCmd = new byte[] {(byte)0xF0, (byte)0xD4, (byte)0x05, (byte)0x80, (byte)0x00};
                    response = nfcA.transceive(refreshCmd);
                    Log.e("RefreshData1_state:", hexToString(response));
                    if (response.length >= 2 && response[response.length - 2] == (byte) 0x90 && response[response.length - 1] == (byte) 0x00) {
                        Log.e("NfcHelper", "Refresh command success");
                    } else {
                        Log.e("NfcHelper", "Refresh command failed");
                    }
                    // --- Add this for progress bar completion ---
                    if (progressCallback != null) {
                        progressCallback.callback(100f);
                    }
                } catch (Exception e) {
                    Log.e("NfcHelper", "NfcA Exception: " + e);
                } finally {
                    try {
                        nfcA.close();
                    } catch (Exception ignored) {}
                }
            }
        }
    }

    public static void processNfcIntentByteBufferAsync(final Intent intent, final int width0, final int height0, final java.nio.ByteBuffer buffer, final String[] epd_init) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                processNfcIntentByteBuffer(intent, width0, height0, buffer, epd_init);
            }
        }).start();
    }

    public static void processNfcIntentByteBuffer(Intent intent, int width0, int height0, java.nio.ByteBuffer buffer, String[] epd_init) {
        byte[] image_buffer = new byte[buffer.remaining()];
        buffer.get(image_buffer);
        processNfcIntent(intent, width0, height0, image_buffer, epd_init);
    }

    public static byte[] hexStringToBytes(String hexString) {
        int len = hexString.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(hexString.charAt(i), 16) << 4)
                                 + Character.digit(hexString.charAt(i+1), 16));
        }
        return data;
    }

    public static String hexToString(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02X ", b));
        }
        return sb.toString();
    }

    public static byte[] transceive(Intent intent, byte[] command) {
        try {
            Tag tag = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG);
            IsoDep isoDep = IsoDep.get(tag);
            isoDep.connect();
            byte[] response = isoDep.transceive(command);
            isoDep.close();
            return response;
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    // Add this setter method to allow Python to register the callback:
    public static void setProgressCallback(PythonCallback callback) {
        progressCallback = callback;
    }
}