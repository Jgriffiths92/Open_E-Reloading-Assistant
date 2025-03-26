package com.example.opene_dope.ui.home

import android.app.Application
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import java.io.BufferedReader
import java.io.InputStreamReader

data class TableRow(val target: String, val range: String, val elevation: String, val wind1: String, val wind2: String, val lead: String)
data class TableData(val rows: List<TableRow>)
class HomeViewModel(application: Application) : AndroidViewModel(application) {

    private val _text = MutableLiveData<String>().apply {
        value = loadCsvData(application.applicationContext).toString()
    }

    private val _intent = MutableLiveData<Intent?>().apply {
        value = null
    }


    val intent: LiveData<Intent?> = _intent

    fun onIntent(intent: Intent) {
        Log.d("HomeViewModel", "Intent received: $intent")
        if(intent.action == Intent.ACTION_SEND) {
            if ("text/plain" == intent.type) {
                val text = intent.getStringExtra(Intent.EXTRA_TEXT)
                _text.value = text ?: "No data received"
            }
        } else {
            _intent.value = intent
            // reset the intent after processing
            _intent.value = null
        }
    }

   val text: LiveData<String> = _text

    // Helper function to populate TableData
    private fun loadCsvData(context: Context): TableData {
        val tableRows = mutableListOf<TableRow>()
        try {
            val inputStream = context.resources.openRawResource(com.example.opene_dope.R.raw.rc)
            val reader = BufferedReader(InputStreamReader(inputStream))

            // Skip the first five lines
            repeat(5) {
                reader.readLine()
            }

            var line: String? = reader.readLine()
            while (line != null) {
                val values = line.split(",")
                if (values.size >= 14) {
                    val row = TableRow(
                        values[0], // Target ID Value
                        values[1], // Range Value
                        values[2], // Elevation Value
                        values[3], // Wind 1 Value
                        values[4], // Wind 2 Value
                        values[5]  // Lead Value
                    )
                    tableRows.add(row)
                }
                line = reader.readLine()
            }
            reader.close()
        } catch (e: Exception) {
            Log.e("HomeViewModel", "Error reading CSV", e)
            // Handle the error by adding an error row
            val errorRow = TableRow("Error", "Error", "Error", "Error", "Error", "Error")
            tableRows.add(errorRow)

        }
        return TableData(tableRows)
    }
}




