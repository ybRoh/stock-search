package com.stocksearch;

import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private ProgressBar progressBar;
    private String serverUrl;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);

        setupWebView();

        // 저장된 서버 URL 확인
        SharedPreferences prefs = getSharedPreferences("StockSearch", MODE_PRIVATE);
        serverUrl = prefs.getString("serverUrl", "");

        if (serverUrl.isEmpty()) {
            showServerDialog();
        } else {
            loadServer();
        }
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                Toast.makeText(MainActivity.this, "연결 실패: " + description, Toast.LENGTH_LONG).show();
                showServerDialog();
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress < 100) {
                    progressBar.setVisibility(View.VISIBLE);
                    progressBar.setProgress(newProgress);
                } else {
                    progressBar.setVisibility(View.GONE);
                }
            }
        });
    }

    private void showServerDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("서버 설정");

        View view = getLayoutInflater().inflate(R.layout.dialog_server, null);
        EditText editText = view.findViewById(R.id.serverInput);

        if (!serverUrl.isEmpty()) {
            editText.setText(serverUrl);
        } else {
            editText.setText("http://172.30.1.78:8000");
        }

        builder.setView(view);
        builder.setPositiveButton("연결", (dialog, which) -> {
            serverUrl = editText.getText().toString().trim();
            if (!serverUrl.startsWith("http")) {
                serverUrl = "http://" + serverUrl;
            }

            // 저장
            SharedPreferences prefs = getSharedPreferences("StockSearch", MODE_PRIVATE);
            prefs.edit().putString("serverUrl", serverUrl).apply();

            loadServer();
        });
        builder.setNegativeButton("취소", null);
        builder.setCancelable(false);
        builder.show();
    }

    private void loadServer() {
        progressBar.setVisibility(View.VISIBLE);
        // ngrok 무료 버전 경고 페이지 우회를 위한 헤더 추가
        Map<String, String> headers = new HashMap<>();
        headers.put("ngrok-skip-browser-warning", "true");
        webView.loadUrl(serverUrl, headers);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
