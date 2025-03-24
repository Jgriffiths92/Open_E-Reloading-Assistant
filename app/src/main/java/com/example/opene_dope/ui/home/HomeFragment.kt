package com.example.opene_dope.ui.home

import android.app.AlertDialog
import android.content.ContentValues.TAG
import android.content.DialogInterface
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.View.GONE
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TableLayout
import android.widget.TableRow
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import com.example.opene_dope.R
import com.example.opene_dope.databinding.FragmentHomeBinding
import java.io.BufferedReader

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null

    // This property is only valid between onCreateView and
    // onDestroyView.
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        val homeViewModel =
            ViewModelProvider(this)[HomeViewModel::class.java]

        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        val root: View = binding.root

        val tableLayout: TableLayout = binding.textHome
        homeViewModel.text.observe(viewLifecycleOwner) {
           // textView.TableLayout = it

            val data: List<List<String>> = try {
                val inputStream = resources.openRawResource(R.raw.rc)
                val reader = BufferedReader(inputStream.reader())
                val lines = reader.readLines()
                val csvData = mutableListOf<List<String>>()

                // Skip the first 5 lines
                val dataLines = lines.drop(5)
                for (line in dataLines) {
                    val row = line.split(",").map { it.trim() }.take(6)
                    csvData.add(row)
                }

                reader.close()
                csvData
            } catch (e: Exception) {
                Log.e(TAG, "Error reading CSV file: ${e.message}")
                // Return an empty list or a default data set in case of an error
                listOf(
                    listOf("Error", "Error", "Error"),
                    listOf("Error", "Error", "Error"),
                    listOf("Error", "Error", "Error")
                )
            }

            tableLayout.removeAllViews()

            for (row in data) {
                val tableRow = TableRow(requireContext())
                for (cell in row) {
                    val textView = TextView(requireContext())
                    textView.text = cell
                    textView.gravity = Gravity.CENTER
                    TableRow.LayoutParams(
                        TableRow.LayoutParams.WRAP_CONTENT,
                        TableRow.LayoutParams.WRAP_CONTENT,
                        1.0f
                    )
                    textView.setPadding(10, 10, 10, 10)
                    textView.setBackgroundResource(R.drawable.cell_border)
                    tableRow.addView(textView)
                }
                tableLayout.addView(tableRow)
            }

        }
        binding.fab.setOnClickListener {
            val layout = LinearLayout(requireContext())
            layout.orientation = LinearLayout.VERTICAL

            val title = TextView(requireContext())
            title.text = getString(R.string.event_name)
            layout.addView(title)

            val spinner = Spinner(requireContext())
            val spinnerItems = arrayOf("Create New Event", "Event 1", "Event 2", "Event 3") // Replace with your items
            val editText = EditText(requireContext())
            editText.hint = "Event Title"
            editText.visibility = GONE

            val spinnerAdapter = android.widget.ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, spinnerItems)
            spinnerAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) // Corrected typo
            spinner.adapter = spinnerAdapter
            spinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, position: Int, id: Long) {
                    if (spinnerItems[position] == "New Event") {
                        editText.visibility = View.VISIBLE
                    } else {
                        editText.visibility = GONE
                    }
                }
                override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
            }
            layout.addView(spinner)
            layout.addView(editText)
            val input = EditText(requireContext())
            input.hint = "Data Card Name"
            layout.addView(input)

            val builder = AlertDialog.Builder(requireContext())

            builder.setView(layout)

            builder.setTitle("Save Data Card")


                .setPositiveButton("Save") { dialog: DialogInterface, _: Int ->
                    dialog.dismiss()
                }
                .setNegativeButton("Cancel") { dialog: DialogInterface, _: Int ->
                    dialog.cancel()
                }

            val dialog = builder.create()
            dialog.show()

        }
        return root
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}