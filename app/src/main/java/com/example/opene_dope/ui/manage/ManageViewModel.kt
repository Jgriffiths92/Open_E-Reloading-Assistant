package com.example.opene_dope.ui.manage

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel

class ManageViewModel : ViewModel() {

    private val _text = MutableLiveData<String>().apply {
        value = "This is the Data Management Page"
    }
    val text: LiveData<String> = _text
}