package com.example.opene_dope.ui.home

import android.app.AlertDialog
import android.content.DialogInterface
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.View.GONE
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import com.example.opene_dope.R
import com.example.opene_dope.databinding.FragmentHomeBinding

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

        val textView: TextView = binding.textHome
        homeViewModel.text.observe(viewLifecycleOwner) {
            textView.text = it
        }
        binding.fab.setOnClickListener {
            val layout = LinearLayout(requireContext())
            layout.orientation = LinearLayout.VERTICAL

            val title = TextView(requireContext())
            title.text = getString(R.string.event_name)
            layout.addView(title)

            val spinner = Spinner(requireContext())
            val spinnerItems = arrayOf("Create New Event...", "Event 1", "Event 2", "Event 3") // Replace with your items
            val editText = EditText(requireContext())
            editText.hint = "Event Title"
            editText.visibility = GONE

            val spinnerAdapter = android.widget.ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, spinnerItems)
            spinnerAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            spinner.adapter = spinnerAdapter
            spinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, position: Int, id: Long) {
                    if (spinnerItems[position] == "Create New Event...") {
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