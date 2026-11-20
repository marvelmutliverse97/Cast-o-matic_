package com.castomatic.nativeapp

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.le.*
import android.content.*
import android.content.pm.PackageManager
import android.net.wifi.p2p.WifiP2pConfig
import android.net.wifi.p2p.WifiP2pDevice
import android.net.wifi.p2p.WifiP2pManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.util.UUID

class MainActivity : ComponentActivity() {

    private lateinit var status: TextView
    private lateinit var devicesBox: LinearLayout
    private lateinit var webView: WebView
    private lateinit var nearby: NearbyManager

    private val permissionRequest = 4101

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        requestNearbyPermissions()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 28, 24, 16)
        }

        val title = TextView(this).apply {
            text = "CAST-O-MATIC"
            textSize = 28f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }

        val subtitle = TextView(this).apply {
            text = "Wireless presentation • nearby sharing • projector receiver"
            textSize = 14f
            setPadding(0, 6, 0, 18)
        }

        status = TextView(this).apply {
            text = "Preparing nearby discovery..."
            textSize = 14f
        }

        val scan = Button(this).apply {
            text = "Find Nearby Devices"
            setOnClickListener { startNearby() }
        }

        val web = Button(this).apply {
            text = "Open Web Cast-O-Matic"
            setOnClickListener {
                webView.visibility = View.VISIBLE
                webView.loadUrl(BuildConfig.WEB_APP_URL)
            }
        }

        val projector = Button(this).apply {
            text = "Projector / Display Receiver"
            setOnClickListener {
                webView.visibility = View.VISIBLE
                webView.loadUrl(BuildConfig.WEB_APP_URL + "/receiver")
            }
        }

        devicesBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        webView = WebView(this).apply {
            visibility = View.GONE
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.mediaPlaybackRequiresUserGesture = false
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()
        }

        root.addView(title)
        root.addView(subtitle)
        root.addView(status)
        root.addView(scan)
        root.addView(web)
        root.addView(projector)
        root.addView(devicesBox, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(webView, LinearLayout.LayoutParams(-1, 0, 2f))

        setContentView(root)
    }

    private fun requestNearbyPermissions() {
        val permissions = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= 31) {
            permissions += Manifest.permission.BLUETOOTH_SCAN
            permissions += Manifest.permission.BLUETOOTH_CONNECT
            permissions += Manifest.permission.BLUETOOTH_ADVERTISE
            permissions += Manifest.permission.NEARBY_WIFI_DEVICES
        } else {
            permissions += Manifest.permission.ACCESS_FINE_LOCATION
        }

        val missing = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missing.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, missing.toTypedArray(), permissionRequest)
        } else {
            startNearby()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, results: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, results)
        if (requestCode == permissionRequest) startNearby()
    }

    @SuppressLint("MissingPermission")
    private fun startNearby() {
        nearby = NearbyManager(this) { device ->
            runOnUiThread {
                status.text = "Nearby discovery active"
                addDevice(device)
            }
        }
        nearby.start()
        status.text = "Scanning for Cast-O-Matic devices..."
    }

    private fun addDevice(device: BluetoothDevice) {
        val id = device.address
        if (devicesBox.findViewWithTag<View>(id) != null) return

        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 12, 0, 12)
            tag = id
        }

        val name = TextView(this).apply {
            text = try { device.name ?: "Nearby Cast-O-Matic device" } catch (_: SecurityException) {
                "Nearby Cast-O-Matic device"
            }
            textSize = 16f
            layoutParams = LinearLayout.LayoutParams(0, -2, 1f)
        }

        val connect = Button(this).apply {
            text = "Pair"
            setOnClickListener {
                Toast.makeText(
                    this@MainActivity,
                    "Device discovered. Use the Cast-O-Matic receiver to complete the Wi-Fi/WebRTC connection.",
                    Toast.LENGTH_LONG
                ).show()
            }
        }

        row.addView(name)
        row.addView(connect)
        devicesBox.addView(row)
    }

    override fun onDestroy() {
        if (::nearby.isInitialized) nearby.stop()
        super.onDestroy()
    }
}

private class NearbyManager(
    private val context: Context,
    private val onDevice: (BluetoothDevice) -> Unit
) {
    companion object {
        private val SERVICE_UUID =
            UUID.fromString("9f5c3c20-2d45-4b74-8a4d-3b8e7e5d1201")
    }

    private val adapter: BluetoothAdapter? =
        (context.getSystemService(Context.BLUETOOTH_SERVICE) as android.bluetooth.BluetoothManager).adapter

    private val scanner: BluetoothLeScanner?
        get() = adapter?.bluetoothLeScanner

    private val callback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            onDevice(result.device)
        }

        override fun onBatchScanResults(results: MutableList<ScanResult>) {
            results.forEach { onDevice(it.device) }
        }
    }

    @SuppressLint("MissingPermission")
    fun start() {
        if (adapter?.isEnabled != true) {
            context.startActivity(Intent(Settings.ACTION_BLUETOOTH_SETTINGS))
            return
        }

        val filter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid(SERVICE_UUID))
            .build()

        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        scanner?.startScan(listOf(filter), settings, callback)
    }

    @SuppressLint("MissingPermission")
    fun stop() {
        scanner?.stopScan(callback)
    }
}
