package com.treninem.beastlegends

import android.annotation.SuppressLint
import android.content.Context
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private lateinit var backendUrlInput: EditText
    private lateinit var linkCodeInput: EditText

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        backendUrlInput = findViewById(R.id.backendUrlInput)
        linkCodeInput = findViewById(R.id.linkCodeInput)
        webView = findViewById(R.id.webView)
        val connectButton: Button = findViewById(R.id.connectButton)

        val prefs = getSharedPreferences("beast_legends", Context.MODE_PRIVATE)
        backendUrlInput.setText(prefs.getString("backend_url", "https://example.com")) // <-- ВСТАВЬ URL backend по умолчанию

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                val token = prefs.getString("token", null)
                if (token != null) {
                    webView.evaluateJavascript("localStorage.setItem('beast_token', '$token');", null)
                }
            }
        }
        webView.webChromeClient = WebChromeClient()

        connectButton.setOnClickListener {
            Thread {
                try {
                    val baseUrl = backendUrlInput.text.toString().trim().trimEnd('/')
                    val code = linkCodeInput.text.toString().trim()
                    val conn = URL("$baseUrl/api/auth/android-link").openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.doOutput = true
                    conn.setRequestProperty("Content-Type", "application/json")
                    OutputStreamWriter(conn.outputStream).use {
                        it.write(JSONObject(mapOf("code" to code)).toString())
                    }
                    val body = BufferedReader(InputStreamReader(if (conn.responseCode in 200..299) conn.inputStream else conn.errorStream)).use { it.readText() }
                    if (conn.responseCode !in 200..299) throw Exception(body)
                    val json = JSONObject(body)
                    prefs.edit().putString("backend_url", baseUrl).putString("token", json.getString("token")).apply()
                    runOnUiThread {
                        Toast.makeText(this, "Профиль синхронизирован", Toast.LENGTH_LONG).show()
                        webView.loadUrl(baseUrl)
                    }
                } catch (e: Exception) {
                    runOnUiThread { Toast.makeText(this, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show() }
                }
            }.start()
        }

        prefs.getString("token", null)?.let {
            val base = prefs.getString("backend_url", "https://example.com")!!.trimEnd('/')
            webView.loadUrl(base)
        }
    }
}
