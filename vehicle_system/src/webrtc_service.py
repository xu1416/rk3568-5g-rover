"""
WebRTC Service Module for RK3568 Rover
Handles WebRTC signaling and peer connection management
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict
from logger import get_logger
from config_manager import get_config

logger = get_logger(__name__)


class WebRTCSignalingServer:
    """
    WebRTC Signaling Server using aiortc
    Manages SDP negotiation and ICE candidates
    """
    
    def __init__(self):
        """Initialize WebRTC signaling server"""
        self.config = get_config()
        self.peers: Dict[str, 'RTCPeerConnection'] = {}
        self.on_peer_connected: Optional[Callable] = None
        self.on_peer_disconnected: Optional[Callable] = None
        self.on_control_command: Optional[Callable] = None
    
    async def initialize(self) -> bool:
        """
        Initialize WebRTC service
        
        Returns:
            True if initialization successful
        """
        try:
            from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer
            
            # Get ICE servers from config
            ice_servers_config = self.config.get('webrtc.ice_servers', [])
            
            self.ice_servers = []
            for server_config in ice_servers_config:
                if 'urls' in server_config:
                    ice_server = RTCIceServer(
                        urls=server_config['urls'],
                        username=server_config.get('username'),
                        credential=server_config.get('credential')
                    )
                    self.ice_servers.append(ice_server)
            
            logger.info(f"WebRTC service initialized with {len(self.ice_servers)} ICE servers")
            return True
            
        except ImportError:
            logger.error("aiortc not installed. Install with: pip install aiortc")
            return False
        except Exception as e:
            logger.error(f"Error initializing WebRTC service: {e}")
            return False
    
    async def create_peer_connection(self, peer_id: str) -> Optional['RTCPeerConnection']:
        """
        Create a new peer connection
        
        Args:
            peer_id: Unique peer identifier
        
        Returns:
            RTCPeerConnection instance or None
        """
        try:
            from aiortc import RTCPeerConnection, RTCConfiguration
            
            # Create configuration with ICE servers
            config = RTCConfiguration(iceServers=self.ice_servers)
            
            # Create peer connection
            pc = RTCPeerConnection(configuration=config)
            self.peers[peer_id] = pc
            
            logger.info(f"Peer connection created for {peer_id}")

            # OPTIMIZATION: Configure DataChannel for low latency (UDP-like)
            # ordered=False: Don't wait for missing packets
            # maxRetransmits=0: Don't retransmit lost packets
            @pc.on("datachannel")
            def on_datachannel(channel):
                logger.info(f"Received data channel: {channel.label}")
                if channel.label == "control":
                    channel.ordered = False
                    channel.maxRetransmits = 0
                    logger.info("Configured control channel for low latency (ordered=False, maxRetransmits=0)")
                    
                    @channel.on("message")
                    def on_message(message):
                        if self.on_control_command:
                            asyncio.create_task(self.on_control_command(peer_id, message))
            
            # Set up event handlers
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Peer {peer_id} connection state: {pc.connectionState}")
                if pc.connectionState == "connected":
                    if self.on_peer_connected:
                        await self.on_peer_connected(peer_id)
                elif pc.connectionState == "failed":
                    await self.close_peer_connection(peer_id)
                    if self.on_peer_disconnected:
                        await self.on_peer_disconnected(peer_id)
            
            return pc
            
        except Exception as e:
            logger.error(f"Error creating peer connection: {e}")
            return None
    
    async def add_video_track(self, peer_id: str, track):
        """
        Add video track to peer connection
        
        Args:
            peer_id: Peer identifier
            track: Video track
        """
        try:
            if peer_id not in self.peers:
                logger.warning(f"Peer {peer_id} not found")
                return
            
            pc = self.peers[peer_id]
            pc.addTrack(track)
            logger.info(f"Video track added to peer {peer_id}")
            
        except Exception as e:
            logger.error(f"Error adding video track: {e}")
    
    async def add_audio_track(self, peer_id: str, track):
        """
        Add audio track to peer connection
        
        Args:
            peer_id: Peer identifier
            track: Audio track
        """
        try:
            if peer_id not in self.peers:
                logger.warning(f"Peer {peer_id} not found")
                return
            
            pc = self.peers[peer_id]
            pc.addTrack(track)
            logger.info(f"Audio track added to peer {peer_id}")
            
        except Exception as e:
            logger.error(f"Error adding audio track: {e}")
    
    async def add_data_channel(self, peer_id: str, label: str = "control"):
        """
        Add data channel for control commands
        
        Args:
            peer_id: Peer identifier
            label: Data channel label
        
        Returns:
            Data channel instance
        """
        try:
            if peer_id not in self.peers:
                logger.warning(f"Peer {peer_id} not found")
                return None
            
            pc = self.peers[peer_id]
            # OPTIMIZATION: Create DataChannel with low latency configuration
            # ordered=False: Don't wait for missing packets
            # maxRetransmits=0: Don't retransmit lost packets
            dc = pc.createDataChannel(label, ordered=False, maxRetransmits=0)
            
            @dc.on("message")
            def on_message(message):
                # logger.debug(f"Data channel message from {peer_id}: {message}") # Reduce logging for high freq
                if self.on_control_command:
                    asyncio.create_task(self.on_control_command(peer_id, message))
            
            logger.info(f"Data channel '{label}' created for peer {peer_id}")
            return dc
            
        except Exception as e:
            logger.error(f"Error adding data channel: {e}")
            return None
    
    async def handle_offer(self, peer_id: str, offer_sdp: str) -> Optional[str]:
        """
        Handle SDP offer from peer
        
        Args:
            peer_id: Peer identifier
            offer_sdp: SDP offer string
        
        Returns:
            SDP answer string or None
        """
        try:
            from aiortc import RTCSessionDescription
            
            pc = await self.create_peer_connection(peer_id)
            if pc is None:
                return None
            
            # Parse offer
            offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
            await pc.setRemoteDescription(offer)
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            logger.info(f"SDP answer created for peer {peer_id}")
            return pc.localDescription.sdp
            
        except Exception as e:
            logger.error(f"Error handling SDP offer: {e}")
            return None
    
    async def handle_answer(self, peer_id: str, answer_sdp: str) -> bool:
        """
        Handle SDP answer from peer
        
        Args:
            peer_id: Peer identifier
            answer_sdp: SDP answer string
        
        Returns:
            True if successful
        """
        try:
            from aiortc import RTCSessionDescription
            
            if peer_id not in self.peers:
                logger.warning(f"Peer {peer_id} not found")
                return False
            
            pc = self.peers[peer_id]
            
            # Parse and set answer
            answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
            await pc.setRemoteDescription(answer)
            
            logger.info(f"SDP answer processed for peer {peer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling SDP answer: {e}")
            return False
    
    async def add_ice_candidate(self, peer_id: str, candidate_json: str) -> bool:
        """
        Add ICE candidate
        
        Args:
            peer_id: Peer identifier
            candidate_json: ICE candidate JSON string
        
        Returns:
            True if successful
        """
        try:
            from aiortc import RTCIceCandidate
            
            if peer_id not in self.peers:
                logger.warning(f"Peer {peer_id} not found")
                return False
            
            pc = self.peers[peer_id]
            
            # Parse candidate
            candidate_data = json.loads(candidate_json)
            candidate = RTCIceCandidate(
                candidate=candidate_data.get('candidate'),
                sdpMLineIndex=candidate_data.get('sdpMLineIndex'),
                sdpMid=candidate_data.get('sdpMid')
            )
            
            await pc.addIceCandidate(candidate)
            return True
            
        except Exception as e:
            logger.error(f"Error adding ICE candidate: {e}")
            return False
    
    async def close_peer_connection(self, peer_id: str):
        """
        Close peer connection
        
        Args:
            peer_id: Peer identifier
        """
        try:
            if peer_id in self.peers:
                pc = self.peers[peer_id]
                await pc.close()
                del self.peers[peer_id]
                logger.info(f"Peer connection closed for {peer_id}")
        except Exception as e:
            logger.error(f"Error closing peer connection: {e}")
    
    def get_peer_stats(self) -> dict:
        """Get statistics about peer connections"""
        return {
            'active_peers': len(self.peers),
            'peer_ids': list(self.peers.keys()),
        }
    
    async def shutdown(self):
        """Shutdown WebRTC service"""
        for peer_id in list(self.peers.keys()):
            await self.close_peer_connection(peer_id)
        logger.info("WebRTC service shutdown complete")


class WebRTCMediaManager:
    """Manages media tracks for WebRTC"""
    
    def __init__(self):
        """Initialize media manager"""
        self.config = get_config()
        self.video_tracks = {}
        self.audio_tracks = {}
    
    async def create_video_track(self, camera_frame_callback) -> Optional:
        """
        Create video track from camera
        
        Args:
            camera_frame_callback: Callback to get video frames
        
        Returns:
            Video track or None
        """
        try:
            from av import VideoFrame
            from aiortc import VideoStreamTrack
            
            class CameraVideoTrack(VideoStreamTrack):
                def __init__(self, callback):
                    super().__init__()
                    self.callback = callback
                
                async def recv(self):
                    frame = self.callback()
                    if frame is None:
                        return None
                    
                    # Convert numpy array to VideoFrame
                    video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
                    return video_frame
            
            track = CameraVideoTrack(camera_frame_callback)
            logger.info("Video track created")
            return track
            
        except Exception as e:
            logger.error(f"Error creating video track: {e}")
            return None
    
    async def create_audio_track(self, audio_frame_callback) -> Optional:
        """
        Create audio track from microphone
        
        Args:
            audio_frame_callback: Callback to get audio frames
        
        Returns:
            Audio track or None
        """
        try:
            from av import AudioFrame
            from aiortc import AudioStreamTrack
            import numpy as np
            
            class MicrophoneAudioTrack(AudioStreamTrack):
                def __init__(self, callback, sample_rate=16000, channels=1):
                    super().__init__()
                    self.callback = callback
                    self.sample_rate = sample_rate
                    self.channels = channels
                
                async def recv(self):
                    frame_data = self.callback()
                    if frame_data is None:
                        return None
                    
                    # Convert to AudioFrame
                    audio_frame = AudioFrame.from_ndarray(
                        frame_data,
                        format="s16",
                        layout="mono" if self.channels == 1 else "stereo"
                    )
                    audio_frame.sample_rate = self.sample_rate
                    return audio_frame
            
            track = MicrophoneAudioTrack(audio_frame_callback)
            logger.info("Audio track created")
            return track
            
        except Exception as e:
            logger.error(f"Error creating audio track: {e}")
            return None


# Global WebRTC service instance
_webrtc_service: Optional[WebRTCSignalingServer] = None


async def get_webrtc_service() -> WebRTCSignalingServer:
    """Get global WebRTC service instance"""
    global _webrtc_service
    if _webrtc_service is None:
        _webrtc_service = WebRTCSignalingServer()
        await _webrtc_service.initialize()
    return _webrtc_service


# Example usage
if __name__ == "__main__":
    async def main():
        service = await get_webrtc_service()
        print("WebRTC service initialized")
        await service.shutdown()
    
    asyncio.run(main())
