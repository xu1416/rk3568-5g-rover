package com.rover.webrtc

import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.*
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import timber.log.Timber
import java.util.concurrent.TimeUnit

/**
 * WebSocket-based signaling client for WebRTC negotiation
 */
class SignalingClient(
    private val roverAddress: String,
    private val port: Int = 8765
) {
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()
    
    private var webSocket: WebSocket? = null
    private var isConnected = false
    
    private val coroutineScope = CoroutineScope(Dispatchers.Main + Job())
    
    // Callbacks
    var onAnswerReceived: ((String) -> Unit)? = null
    var onIceCandidateReceived: ((String, Int, String?) -> Unit)? = null
    var onConnected: (() -> Unit)? = null
    var onDisconnected: (() -> Unit)? = null
    var onError: ((String) -> Unit)? = null
    
    suspend fun connect(peerId: String = "android_client"): Boolean = withContext(Dispatchers.IO) {
        return@withContext try {
            val url = "ws://$roverAddress:$port"
            val request = Request.Builder()
                .url(url)
                .build()
            
            webSocket = client.newWebSocket(request, WebSocketListener())
            
            // Wait for connection
            var attempts = 0
            while (!isConnected && attempts < 50) {
                delay(100)
                attempts++
            }
            
            if (isConnected) {
                // Send peer ID
                val message = JsonObject().apply {
                    addProperty("type", "register")
                    addProperty("peerId", peerId)
                }
                sendMessage(message.toString())
                Timber.d("Connected to signaling server")
                true
            } else {
                Timber.e("Failed to connect to signaling server")
                false
            }
        } catch (e: Exception) {
            Timber.e(e, "Error connecting to signaling server")
            false
        }
    }
    
    suspend fun sendOffer(offerSdp: String): String? = withContext(Dispatchers.IO) {
        return@withContext try {
            val message = JsonObject().apply {
                addProperty("type", "offer")
                addProperty("sdp", offerSdp)
            }
            
            sendMessage(message.toString())
            
            // Wait for answer (with timeout)
            var attempts = 0
            var answer: String? = null
            val startTime = System.currentTimeMillis()
            
            while (answer == null && System.currentTimeMillis() - startTime < 30000) {
                delay(100)
                attempts++
            }
            
            answer
        } catch (e: Exception) {
            Timber.e(e, "Error sending offer")
            null
        }
    }
    
    suspend fun sendAnswer(answerSdp: String): Boolean = withContext(Dispatchers.IO) {
        return@withContext try {
            val message = JsonObject().apply {
                addProperty("type", "answer")
                addProperty("sdp", answerSdp)
            }
            
            sendMessage(message.toString())
            Timber.d("Answer sent")
            true
        } catch (e: Exception) {
            Timber.e(e, "Error sending answer")
            false
        }
    }
    
    suspend fun sendIceCandidate(candidate: String, sdpMLineIndex: Int, sdpMid: String?): Boolean = withContext(Dispatchers.IO) {
        return@withContext try {
            val message = JsonObject().apply {
                addProperty("type", "ice_candidate")
                addProperty("candidate", candidate)
                addProperty("sdpMLineIndex", sdpMLineIndex)
                if (sdpMid != null) {
                    addProperty("sdpMid", sdpMid)
                }
            }
            
            sendMessage(message.toString())
            true
        } catch (e: Exception) {
            Timber.e(e, "Error sending ICE candidate")
            false
        }
    }
    
    private fun sendMessage(message: String) {
        try {
            webSocket?.send(message)
            Timber.d("Message sent: $message")
        } catch (e: Exception) {
            Timber.e(e, "Error sending message")
        }
    }
    
    fun disconnect() {
        try {
            webSocket?.close(1000, "Client disconnecting")
            webSocket = null
            isConnected = false
            coroutineScope.cancel()
            Timber.d("Disconnected from signaling server")
        } catch (e: Exception) {
            Timber.e(e, "Error disconnecting")
        }
    }
    
    private inner class WebSocketListener : okhttp3.WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
            Timber.d("WebSocket opened")
            isConnected = true
            coroutineScope.launch {
                onConnected?.invoke()
            }
        }
        
        override fun onMessage(webSocket: WebSocket, text: String) {
            try {
                Timber.d("WebSocket message received: $text")
                
                val json = gson.fromJson(text, JsonObject::class.java)
                val type = json.get("type")?.asString
                
                when (type) {
                    "answer" -> {
                        val sdp = json.get("sdp")?.asString
                        if (sdp != null) {
                            coroutineScope.launch {
                                onAnswerReceived?.invoke(sdp)
                            }
                        }
                    }
                    "ice_candidate" -> {
                        val candidate = json.get("candidate")?.asString
                        val sdpMLineIndex = json.get("sdpMLineIndex")?.asInt ?: 0
                        val sdpMid = json.get("sdpMid")?.asString
                        
                        if (candidate != null) {
                            coroutineScope.launch {
                                onIceCandidateReceived?.invoke(candidate, sdpMLineIndex, sdpMid)
                            }
                        }
                    }
                    "error" -> {
                        val error = json.get("message")?.asString ?: "Unknown error"
                        coroutineScope.launch {
                            onError?.invoke(error)
                        }
                    }
                }
            } catch (e: Exception) {
                Timber.e(e, "Error processing WebSocket message")
            }
        }
        
        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            Timber.d("WebSocket closing: $code $reason")
            isConnected = false
            coroutineScope.launch {
                onDisconnected?.invoke()
            }
        }
        
        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Timber.d("WebSocket closed: $code $reason")
            isConnected = false
        }
        
        override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) {
            Timber.e(t, "WebSocket error")
            isConnected = false
            coroutineScope.launch {
                onError?.invoke(t.message ?: "Unknown error")
            }
        }
    }
}
