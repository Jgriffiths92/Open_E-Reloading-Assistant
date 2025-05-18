package com.example.myapplication

import android.content.Intent
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.NfcA
import android.os.Parcelable
import android.util.Log

var data_DB = "F0DB000069";//10    var data_DB = "F0DB000069"; //10  The prefix number is the sum of all the data that follows.
var start = "A00603300190012C";//16  var start = "A00603300190012C"; // 16   4.2-inch monochrome 400x300
var RST = "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40103"; // 48 +56  var RST = "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40108" + "A502000A" + "A4010C" + "A502000A" + "A40103" // 48 +56   Reset repeated three times
var set_wf = "A102000F";//8  //0x00 0F
var set_power = "A10104" + "A40103";//12  //0x04  busy
var set_resolution = "A105610190012C";//14   //0x61 01 90 01 2C
var set_border = "A1025097";//8  //0x50 97
var write_BW = "A3021013"; //6    //0x10
var write_BWR = "A3021013"; //8   //0x13
var update = "A20112" + "A502000A" + "A40103";//20  //0x12 delay  busy
var sleep = "A20102" + "A40103" + "A20207A5"; //20 //0x02 busy 07 A5
val epd_init: Array<String> = arrayOf(
    data_DB + start + RST + set_wf + set_resolution + set_border + set_power + write_BWR + update + sleep, data_DB + start + RST + set_wf + set_resolution + set_border + set_power + write_BWR + update + sleep, //16+104+8+12+14+8+8+20+20=152   210/2=0x69 //Screen initialization
    "F0DA000003F00330" //10    "F0DA000003F00330" //10    Screen parameter 0000  Data length 03   Custom screen F0    Screen size resolution 12   Screen color 20   (Screen resolution and color are set with A0 command)
)

object NfcHelper {
    @JvmStatic
    fun processNfcIntent(intent: Intent, width0: Int, height0: Int, image_buffer: ByteArray, epd_init: Array<String>) {
        val p: Parcelable = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG) ?: return
        val tag = p as Tag
        val nfcA = NfcA.get(tag)
        if (nfcA != null) {
            try {
                Log.e("debug", "intent")
                nfcA.connect()
                var cmd: ByteArray
                var response: ByteArray
                nfcA.timeout = 60000

                cmd = hexStringToBytes(epd_init[0])
                response = nfcA.transceive(cmd)
                Log.e("epdinit_state", HexToString(response))

                cmd = hexStringToBytes(epd_init[1])
                response = nfcA.transceive(cmd)
                Log.e("epdinit_state", HexToString(response))

                val datas = width0 * height0 / 8
                for (i in 0 until datas / 250) {
                    cmd = ByteArray(255)
                    cmd[0] = 0xF0.toByte()
                    cmd[1] = 0xD2.toByte()
                    cmd[2] = 0x00
                    cmd[3] = i.toByte()
                    cmd[4] = 0xFA.toByte()
                    for (j in 0 until 250) {
                        cmd[j + 5] = image_buffer[j + 250 * i]
                    }
                    response = nfcA.transceive(cmd)
                    Log.e("${i + 1} sendData_state:", HexToString(response))
                }

                val refreshCmd = byteArrayOf(0xF0.toByte(), 0xD4.toByte(), 0x05, 0x80.toByte(), 0x00)
                response = nfcA.transceive(refreshCmd)
                Log.e("RefreshData1_state:", HexToString(response))
                if (response[0] != 0x90.toByte()) {
                    response = nfcA.transceive(refreshCmd)
                    Log.e("RefreshData2_state:", HexToString(response))
                }
            } catch (e: Exception) {
                e.printStackTrace()
                Log.e("debug", "Exception in processNfcIntent: $e")
            } finally {
                nfcA.close()
            }
        }
    }

    // Add hexStringToBytes and HexToString utility functions here
}

override fun onNewIntent(intent: Intent?) {
    super.onNewIntent(intent)
    val p: Parcelable = intent?.getParcelableExtra(NfcAdapter.EXTRA_TAG) ?: return

    val tag = p as Tag
    val nfcA = NfcA.get(tag)
    if(nfcA != null) {
        try {
            Log.e("debug", "intent")

            nfcA.connect()
            var cmd: ByteArray
            var response: ByteArray
            nfcA.timeout = 60000
            
            cmd = hexStringToBytes(epd_init[0])
            response = nfcA.transceive(cmd)
            Log.e("epdinit_state", HexToString(response))

            cmd = hexStringToBytes(epd_init[1])
            response = nfcA.transceive(cmd)
            Log.e("epdinit_state", HexToString(response))

            //image_buffer is set to half white half black 400x300 image
            val datas = width0 * height0 / 8
            for (i in 0 until datas / 250) {
                cmd = byteArrayOf(0xF0.toByte(), 0xD2.toByte(), 0x00, i.toByte(), 0xFA.toByte())
                for (j in 0 until 250) {
                    cmd[j + 5] = image_buffer[j + 250 * i]
                }
                response = nfcA.transceive(cmd) // Send black and white data
                Log.e("${i + 1} sendData_state:", HexToString(response)) // Feedback data display, 9000 is Ok

                // Data mantissa sending
                if (i == datas / 250 - 1 && datas % 250 != 0) {
                    cmd = byteArrayOf(0xF0.toByte(), 0xD2.toByte(), 0x00, (i + 1).toByte(), 0xFA.toByte())
                    for (j in 0 until 250) {
                        cmd[j + 5] = image_buffer[j + 250 * (datas / 250)]
                    }
                    response = nfcA.transceive(cmd) // Send black and white data
                }
                Log.e("${i + 1} sendData_state:", HexToString(response)) // Feedback data display, 9000 is Ok
            }

            val refreshCmd = byteArrayOf(0xF0.toByte(), 0xD4.toByte(), 0x05, 0x80.toByte(), 0x00)
            response = nfcA.transceive(refreshCmd) // Send e-paper refresh command
            Log.e("RefreshData1_state:", HexToString(response)) // Feedback data display, 9000 is Ok
            if (response[0] != 0x90.toByte()) {
                response = nfcA.transceive(refreshCmd) // Send black and white refresh command
                Log.e("RefreshData2_state:", HexToString(response))
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Log.e("debug", "Exception in onNewIntent: $e")
        } finally {
            nfcA.close()
        }
    }
}