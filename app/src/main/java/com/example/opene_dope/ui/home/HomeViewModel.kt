package com.example.opene_dope.ui.home

import android.app.Application
import android.content.Context
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import java.io.BufferedReader
import java.io.InputStreamReader

class HomeViewModel(application: Application) : AndroidViewModel(application) {

    private val _text = MutableLiveData<String>().apply {
        value = loadCsvData(application.applicationContext)
    }
    val text: LiveData<String> = _text

    /**
     * Loads data from a CSV file located in the raw resources directory.
     *
     * This function reads a CSV file named "rc" (com.example.opene_dope.R.raw.rc) from the
     * application's raw resources, skips the first five lines, and then reads the rest of the file
     * line by line, appending each line to a StringBuilder. Finally, it returns the entire
     * content of the file as a single String.
     *
     * @param context The application context, needed to access the resources.
     * @return A String containing the content of the CSV file (excluding the first five lines),
     *         or an error message if there was a problem reading the file.
     * @throws Exception if an error occurs while reading the file. Errors are logged to the console.
     */
    private fun loadCsvData(context: Context): String {
        val stringBuilder = StringBuilder()
        try {
            val inputStream = context.resources.openRawResource(com.example.opene_dope.R.raw.rc)
            val reader = BufferedReader(InputStreamReader(inputStream))

            // Skip the first five lines using a loop
            repeat(5) {
                reader.readLine()
            }

            var line: String? = reader.readLine()
            while (line != null) {
                val values = line.split(",")
                if (values.size >= 14) {
                    val modifiedLine = listOf(
                        values[0], // keep Target ID Value
                        values[1], // keep Range Value
                        values[2], // keep Elevation Value
                        values[3], // keep Wind 1 Value
                        values[4], // keep Wind 2 Value
                        values[5], // keep Lead Value


                    ).joinToString("|")
                    stringBuilder.append(modifiedLine).append("\n")
                }
                line = reader.readLine()
            }
             reader.close()
        } catch (e: Exception) {
            Log.e("HomeViewModel", "Error reading CSV", e)
            return "Error loading data: ${e.message}"
        }
        return stringBuilder.toString()
    }
}
