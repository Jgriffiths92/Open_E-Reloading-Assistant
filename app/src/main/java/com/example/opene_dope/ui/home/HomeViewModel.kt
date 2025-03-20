package com.example.opene_dope.ui.home

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
class HomeViewModel : ViewModel() {

    private val _text = MutableLiveData<String>().apply {
        value = "Current Data Card Will Be Displayed Here"
    }
    val text: LiveData<String> = _text
}