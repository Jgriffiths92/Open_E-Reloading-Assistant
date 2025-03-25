package com.example.opene_dope

import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.drawerlayout.widget.DrawerLayout
import androidx.navigation.findNavController
import androidx.navigation.ui.AppBarConfiguration
import androidx.navigation.ui.navigateUp
import androidx.navigation.ui.setupActionBarWithNavController
import androidx.navigation.ui.setupWithNavController
import com.example.opene_dope.databinding.ActivityMainBinding
import com.google.android.material.navigation.NavigationView

class MainActivity : AppCompatActivity() {

    private lateinit var appBarConfiguration: AppBarConfiguration
    private lateinit var binding: ActivityMainBinding
    private var isLeadVisible = false
    private var isWindHold1Visible = true

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.appBarMain.toolbar)

        val drawerLayout: DrawerLayout = binding.drawerLayout
        val navView: NavigationView = binding.navView
        val navController = findNavController(R.id.nav_host_fragment_content_main)
        // Passing each menu ID as a set of Ids because each
        // menu should be considered as top level destinations.
        appBarConfiguration = AppBarConfiguration(
            setOf(
                R.id.nav_home, R.id.nav_gallery, R.id.nav_manage
            ), drawerLayout
        )
        setupActionBarWithNavController(navController, appBarConfiguration)
        navView.setupWithNavController(navController)
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        // Inflate the menu; this adds items to the action bar if it is present.
        menuInflater.inflate(R.menu.main, menu)
        // Update the menu item text
        val showHideLeadMenuItem = menu.findItem(R.id.show_hide_lead)
        if(isLeadVisible){
            showHideLeadMenuItem.title = "Hide Lead"
        }else{
            showHideLeadMenuItem.title = "Show Lead" }

        val showHideWindHoldMenuItem = menu.findItem(R.id.show_1_or_2_wind_values)
        if(isWindHold1Visible){
            showHideWindHoldMenuItem.title = "Show 2 Wind Holds"
        }else{
            showHideWindHoldMenuItem.title = "Show 1 Wind Hold" }
        return true

    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when(item.itemId) {
             R.id.action_settings -> {
                // Handle the settings action
                val navController = findNavController(R.id.nav_host_fragment_content_main)
                // Navigate to the settings fragment
                navController.navigate(R.id.nav_settings)
                return true
            }
            R.id.show_hide_lead -> {
                isLeadVisible = !isLeadVisible
                if (isLeadVisible){
                    Toast.makeText(this, "Lead column is now visible", Toast.LENGTH_SHORT).show()
                }else {
                    Toast.makeText(this, "Lead column is now hidden", Toast.LENGTH_SHORT).show()
                }
                invalidateOptionsMenu()
                return true

            }
            R.id.show_1_or_2_wind_values->{
                isWindHold1Visible = !isWindHold1Visible
                if (isWindHold1Visible){
                    Toast.makeText(this, "Show 1 wind hold", Toast.LENGTH_SHORT).show()
                }else {
                    Toast.makeText(this, "Show 2 wind holds", Toast.LENGTH_SHORT).show()

                }
                invalidateOptionsMenu()
                return true
            }

            else -> super.onOptionsItemSelected(item)
        }

    }

    override fun onSupportNavigateUp(): Boolean {
        val navController = findNavController(R.id.nav_host_fragment_content_main)
        return navController.navigateUp(appBarConfiguration) || super.onSupportNavigateUp()
    }

}