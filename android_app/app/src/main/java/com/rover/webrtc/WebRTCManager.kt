package com.rover.webrtc

import android.content.Context
import kotlinx.coroutines.*
import org.webrtc.*
import timber.log.Timber
import java.util.concurrent.Executors

/**
 * WebRTC Manager for handling peer connections and media streams
 */
class WebRTCManager(
    private val context: Context,
    private val signalingClient: SignalingClient
) {
    private val coroutineScope = CoroutineScope(Dispatchers.Default + Job())
    private val executor = Executors.newSingleThreadExecutor()
    
    private lateinit var peerConnectionFactory: PeerConnectionFactory
    private var peerConnection: PeerConnection? = null
    
    private var localVideoTrack: VideoTrack? = null
    private var localAudioTrack: AudioTrack? = null
    private var remoteVideoTrack: VideoTrack? = null
    private var remoteAudioTrack: AudioTrack? = null
    
    private var videoSource: VideoSource? = null
    private var audioSource: AudioSource? = null
    
    private var dataChannel: DataChannel? = null
    
    // Callbacks
    var onRemoteVideoTrackReceived: ((VideoTrack) -> Unit)? = null
    var onRemoteAudioTrackReceived: ((AudioTrack) -> Unit)? = null
    var onConnectionStateChanged: ((PeerConnection.PeerConnectionState) -> Unit)? = null
    var onIceCandidate: ((IceCandidate) -> Unit)? = null
    var onDataChannelOpen: (() -> Unit)? = null
    var onDataChannelMessage: ((String) -> Unit)? = null
    
    // Statistics
    var connectionState: PeerConnection.PeerConnectionState = PeerConnection.PeerConnectionState.NEW
    var iceConnectionState: PeerConnection.IceConnectionState = PeerConnection.IceConnectionState.NEW
    var signalingState: PeerConnection.SignalingState = PeerConnection.SignalingState.STABLE
    
    suspend fun initialize(): Boolean = withContext(Dispatchers.Default) {
        return@withContext try {
            // Initialize PeerConnectionFactory
            val options = PeerConnectionFactory.Options()
            options.disableEncryption = false
            
            PeerConnectionFactory.initialize(
                PeerConnectionFactory.InitializationOptions.builder(context)
                    .setEnableInternalTracer(true)
                    .setFieldTrials("")
                    .createInitializationOptions()
            )
            
            peerConnectionFactory = PeerConnectionFactory.builder()
                .setOptions(options)
                .setVideoEncoderFactory(DefaultVideoEncoderFactory(
                    EglBase.create().eglBaseContext,
                    true,
                    true
                ))
                .setVideoDecoderFactory(DefaultVideoDecoderFactory(
                    EglBase.create().eglBaseContext
                ))
                .createPeerConnectionFactory()
            
            Timber.d("WebRTC initialized successfully")
            true
        } catch (e: Exception) {
            Timber.e(e, "Error initializing WebRTC")
            false
        }
    }
    
    suspend fun connect(roverAddress: String): Boolean = withContext(Dispatchers.Default) {
        return@withContext try {
            // Create peer connection
            val iceServers = listOf(
                PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer(),
                PeerConnection.IceServer.builder("stun:stun1.l.google.com:19302").createIceServer()
            )
            
            val rtcConfig = PeerConnection.RTCConfiguration(iceServers)
            rtcConfig.bundlePolicy = PeerConnection.BundlePolicy.MAXBUNDLE
            rtcConfig.rtcpMuxPolicy = PeerConnection.RtcpMuxPolicy.REQUIRE
            rtcConfig.continualGatheringPolicy = PeerConnection.ContinualGatheringPolicy.GATHER_CONTINUALLY
            
            peerConnection = peerConnectionFactory.createPeerConnection(
                rtcConfig,
                PeerConnectionObserver()
            ) ?: return@withContext false
            
            // Add local media tracks
            addLocalMediaTracks()
            
            // Create data channel for control commands
            val dataChannelInit = DataChannel.Init()
            dataChannelInit.ordered = true
            dataChannelInit.negotiated = false
            
            dataChannel = peerConnection?.createDataChannel("control", dataChannelInit)
            dataChannel?.registerObserver(DataChannelObserver())
            
            // Create and send offer
            val offerOptions = PeerConnection.RTCOfferAnswerOptions()
            offerOptions.iceRestart = false
            offerOptions.voiceActivityDetection = true
            
            peerConnection?.createOffer(object : SdpObserver {
                override fun onCreateSuccess(sessionDescription: SessionDescription?) {
                    if (sessionDescription != null) {
                        peerConnection?.setLocalDescription(object : SdpObserver {
                            override fun onCreateSuccess(p0: SessionDescription?) {}
                            override fun onSetSuccess() {
                                coroutineScope.launch {
                                    signalingClient.sendOffer(sessionDescription.description)
                                }
                            }
                            override fun onCreateFailure(p0: String?) {}
                            override fun onSetFailure(p0: String?) {}
                        }, sessionDescription)
                    }
                }
                override fun onSetSuccess() {}
                override fun onCreateFailure(p0: String?) {
                    Timber.e("Failed to create offer: $p0")
                }
                override fun onSetFailure(p0: String?) {}
            }, offerOptions)
            
            // Connect to signaling server
            signalingClient.connect(roverAddress)
            
            Timber.d("WebRTC connection initiated")
            true
        } catch (e: Exception) {
            Timber.e(e, "Error connecting WebRTC")
            false
        }
    }
    
    private fun addLocalMediaTracks() {
        try {
            // Add video track
            videoSource = peerConnectionFactory.createVideoSource(false)
            localVideoTrack = peerConnectionFactory.createVideoTrack("video_track", videoSource)
            
            val videoRtpSender = peerConnection?.addTrack(localVideoTrack, listOf("stream_id"))
            
            // Add audio track
            val audioConstraints = MediaConstraints()
            audioConstraints.mandatory.add(MediaConstraints.KeyValuePair("echoCancellation", "true"))
            audioConstraints.mandatory.add(MediaConstraints.KeyValuePair("noiseSuppression", "true"))
            audioConstraints.mandatory.add(MediaConstraints.KeyValuePair("autoGainControl", "true"))
            
            audioSource = peerConnectionFactory.createAudioSource(audioConstraints)
            localAudioTrack = peerConnectionFactory.createAudioTrack("audio_track", audioSource)
            
            val audioRtpSender = peerConnection?.addTrack(localAudioTrack, listOf("stream_id"))
            
            Timber.d("Local media tracks added")
        } catch (e: Exception) {
            Timber.e(e, "Error adding local media tracks")
        }
    }
    
    suspend fun handleAnswer(answerSdp: String) = withContext(Dispatchers.Default) {
        try {
            val sessionDescription = SessionDescription(SessionDescription.Type.ANSWER, answerSdp)
            peerConnection?.setRemoteDescription(object : SdpObserver {
                override fun onCreateSuccess(p0: SessionDescription?) {}
                override fun onSetSuccess() {
                    Timber.d("Remote description set successfully")
                }
                override fun onCreateFailure(p0: String?) {}
                override fun onSetFailure(p0: String?) {
                    Timber.e("Failed to set remote description: $p0")
                }
            }, sessionDescription)
        } catch (e: Exception) {
            Timber.e(e, "Error handling answer")
        }
    }
    
    suspend fun addIceCandidate(candidate: String, sdpMLineIndex: Int, sdpMid: String?) = withContext(Dispatchers.Default) {
        try {
            val iceCandidate = IceCandidate(sdpMid, sdpMLineIndex, candidate)
            peerConnection?.addIceCandidate(iceCandidate)
        } catch (e: Exception) {
            Timber.e(e, "Error adding ICE candidate")
        }
    }
    
    fun sendControlCommand(command: String) {
        try {
            if (dataChannel?.state() == DataChannel.State.OPEN) {
                val buffer = DataChannel.Buffer(java.nio.ByteBuffer.wrap(command.toByteArray()), false)
                dataChannel?.send(buffer)
                Timber.d("Control command sent: $command")
            } else {
                Timber.w("Data channel not open")
            }
        } catch (e: Exception) {
            Timber.e(e, "Error sending control command")
        }
    }
    
    fun getConnectionStats(callback: (Map<String, String>) -> Unit) {
        peerConnection?.getStats { report ->
            val stats = mutableMapOf<String, String>()
            
            report.statsMap.forEach { (_, rtcStats) ->
                when (rtcStats) {
                    is RTCInboundRtpStreamStats -> {
                        stats["bytesReceived"] = rtcStats.bytesReceived.toString()
                        stats["packetsLost"] = rtcStats.packetsLost.toString()
                        stats["jitter"] = rtcStats.jitter.toString()
                        stats["framesDecoded"] = rtcStats.framesDecoded.toString()
                    }
                    is RTCOutboundRtpStreamStats -> {
                        stats["bytesSent"] = rtcStats.bytesSent.toString()
                        stats["framesSent"] = rtcStats.framesSent.toString()
                        stats["qualityLimitation"] = rtcStats.qualityLimitation.toString()
                    }
                    is RTCCandidatePairStats -> {
                        stats["availableOutgoingBitrate"] = rtcStats.availableOutgoingBitrate.toString()
                        stats["currentRoundTripTime"] = rtcStats.currentRoundTripTime.toString()
                    }
                }
            }
            
            callback(stats)
        }
    }
    
    fun close() {
        try {
            dataChannel?.unregisterObserver()
            dataChannel?.close()
            dataChannel = null
            
            localVideoTrack?.dispose()
            localAudioTrack?.dispose()
            
            peerConnection?.close()
            peerConnection = null
            
            videoSource?.dispose()
            audioSource?.dispose()
            
            peerConnectionFactory.dispose()
            
            coroutineScope.cancel()
            executor.shutdown()
            
            Timber.d("WebRTC closed")
        } catch (e: Exception) {
            Timber.e(e, "Error closing WebRTC")
        }
    }
    
    // Inner classes for observers
    
    private inner class PeerConnectionObserver : PeerConnection.Observer {
        override fun onSignalingChange(signalingState: PeerConnection.SignalingState?) {
            Timber.d("Signaling state changed: $signalingState")
            signalingState?.let {
                this@WebRTCManager.signalingState = it
            }
        }
        
        override fun onIceConnectionChange(iceConnectionState: PeerConnection.IceConnectionState?) {
            Timber.d("ICE connection state changed: $iceConnectionState")
            iceConnectionState?.let {
                this@WebRTCManager.iceConnectionState = it
            }
        }
        
        override fun onConnectionChange(connectionState: PeerConnection.PeerConnectionState?) {
            Timber.d("Connection state changed: $connectionState")
            connectionState?.let {
                this@WebRTCManager.connectionState = it
                onConnectionStateChanged?.invoke(it)
            }
        }
        
        override fun onIceCandidate(iceCandidate: IceCandidate?) {
            Timber.d("ICE candidate: ${iceCandidate?.candidate}")
            iceCandidate?.let {
                onIceCandidate?.invoke(it)
            }
        }
        
        override fun onIceCandidatesRemoved(candidates: Array<out IceCandidate>?) {
            Timber.d("ICE candidates removed")
        }
        
        override fun onAddStream(mediaStream: MediaStream?) {
            Timber.d("Stream added")
        }
        
        override fun onRemoveStream(mediaStream: MediaStream?) {
            Timber.d("Stream removed")
        }
        
        override fun onAddTrack(rtpReceiver: RtpReceiver?, mediaStreams: Array<out MediaStream>?) {
            Timber.d("Track added")
            rtpReceiver?.track()?.let { track ->
                when (track) {
                    is VideoTrack -> {
                        remoteVideoTrack = track
                        onRemoteVideoTrackReceived?.invoke(track)
                    }
                    is AudioTrack -> {
                        remoteAudioTrack = track
                        onRemoteAudioTrackReceived?.invoke(track)
                    }
                }
            }
        }
        
        override fun onRemoveTrack(rtpReceiver: RtpReceiver?) {
            Timber.d("Track removed")
        }
        
        override fun onDataChannel(dataChannel: DataChannel?) {
            Timber.d("Data channel received")
            this@WebRTCManager.dataChannel = dataChannel
            dataChannel?.registerObserver(DataChannelObserver())
        }
        
        override fun onRenegotiationNeeded() {
            Timber.d("Renegotiation needed")
        }
        
        override fun onIceGatheringChange(iceGatheringState: PeerConnection.IceGatheringState?) {
            Timber.d("ICE gathering state changed: $iceGatheringState")
        }
        
        override fun onAddIceCandidate(iceCandidate: IceCandidate?) {
            Timber.d("ICE candidate added")
        }
        
        override fun onRemoveIceCandidates(candidates: Array<out IceCandidate>?) {
            Timber.d("ICE candidates removed")
        }
    }
    
    private inner class DataChannelObserver : DataChannel.Observer {
        override fun onBufferedAmountChange(previousAmount: Long) {
            Timber.d("Data channel buffered amount changed: $previousAmount")
        }
        
        override fun onMessage(buffer: DataChannel.Buffer?) {
            try {
                buffer?.data?.let { byteBuffer ->
                    val bytes = ByteArray(byteBuffer.remaining())
                    byteBuffer.get(bytes)
                    val message = String(bytes)
                    Timber.d("Data channel message: $message")
                    onDataChannelMessage?.invoke(message)
                }
            } catch (e: Exception) {
                Timber.e(e, "Error processing data channel message")
            }
        }
        
        override fun onStateChange() {
            Timber.d("Data channel state changed: ${dataChannel?.state()}")
            if (dataChannel?.state() == DataChannel.State.OPEN) {
                onDataChannelOpen?.invoke()
            }
        }
    }
    
    private class SdpObserver : org.webrtc.SdpObserver {
        override fun onCreateSuccess(sessionDescription: SessionDescription?) {}
        override fun onSetSuccess() {}
        override fun onCreateFailure(error: String?) {}
        override fun onSetFailure(error: String?) {}
    }
}
