# Android App 控制端 - 开发指南

本文档提供了RK3568远程无人操作车的Android控制App的开发指南。

## 项目结构

```
rover-android-app/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/rover/
│   │   │   │   ├── MainActivity.kt
│   │   │   │   ├── webrtc/
│   │   │   │   │   ├── WebRTCManager.kt
│   │   │   │   │   ├── SignalingClient.kt
│   │   │   │   │   └── MediaManager.kt
│   │   │   │   ├── ui/
│   │   │   │   │   ├── screens/
│   │   │   │   │   │   ├── ConnectScreen.kt
│   │   │   │   │   │   ├── ControlScreen.kt
│   │   │   │   │   │   └── SettingsScreen.kt
│   │   │   │   │   └── components/
│   │   │   │   │       ├── VideoView.kt
│   │   │   │   │       ├── JoystickView.kt
│   │   │   │   │       └── StatusBar.kt
│   │   │   │   ├── controller/
│   │   │   │   │   ├── MotorController.kt
│   │   │   │   │   └── CommandSender.kt
│   │   │   │   └── utils/
│   │   │   │       ├── Logger.kt
│   │   │   │       ├── Config.kt
│   │   │   │       └── Permissions.kt
│   │   │   └── res/
│   │   │       ├── layout/
│   │   │       ├── drawable/
│   │   │       └── values/
│   │   └── test/
│   └── build.gradle
├── build.gradle
└── settings.gradle
```

## 技术栈

- **语言**: Kotlin
- **UI框架**: Jetpack Compose
- **WebRTC库**: WebRTC Android SDK
- **异步框架**: Coroutines
- **依赖注入**: Hilt
- **数据存储**: DataStore

## 核心模块

### 1. WebRTC管理器 (WebRTCManager.kt)

```kotlin
class WebRTCManager(
    private val context: Context,
    private val signalingClient: SignalingClient
) {
    private lateinit var peerConnection: PeerConnection
    private lateinit var videoTrack: VideoTrack
    private lateinit var audioTrack: AudioTrack
    
    suspend fun initialize(): Boolean {
        // 初始化WebRTC工厂
        // 创建对等连接
        // 设置媒体约束
        return true
    }
    
    suspend fun connect(roverAddress: String): Boolean {
        // 连接到小车端
        // 发送SDP offer
        // 处理SDP answer
        return true
    }
    
    fun addVideoRenderer(renderer: VideoRenderer.Callbacks) {
        // 添加视频渲染器
    }
    
    fun sendControlCommand(command: ControlCommand) {
        // 通过数据通道发送控制命令
    }
}
```

### 2. 信令客户端 (SignalingClient.kt)

```kotlin
class SignalingClient(
    private val roverAddress: String,
    private val port: Int = 8765
) {
    private var webSocket: WebSocket? = null
    
    suspend fun connect(): Boolean {
        // 建立WebSocket连接
        return true
    }
    
    suspend fun sendOffer(sdp: String): String? {
        // 发送SDP offer并等待answer
        return null
    }
    
    suspend fun sendAnswer(sdp: String): Boolean {
        // 发送SDP answer
        return true
    }
    
    suspend fun addIceCandidate(candidate: IceCandidate): Boolean {
        // 添加ICE候选
        return true
    }
}
```

### 3. 虚拟摇杆控制 (JoystickView.kt)

```kotlin
@Composable
fun JoystickView(
    onMotorCommand: (MotorCommand) -> Unit,
    modifier: Modifier = Modifier
) {
    var touchX by remember { mutableStateOf(0f) }
    var touchY by remember { mutableStateOf(0f) }
    
    Canvas(
        modifier = modifier
            .size(200.dp)
            .pointerInput(Unit) {
                detectDragGestures { change, dragAmount ->
                    touchX += dragAmount.x
                    touchY += dragAmount.y
                    
                    // 计算摇杆位置并发送命令
                    val command = calculateMotorCommand(touchX, touchY)
                    onMotorCommand(command)
                }
            }
    ) {
        // 绘制摇杆背景
        drawCircle(
            color = Color.LightGray,
            radius = 100f,
            center = center
        )
        
        // 绘制摇杆头
        drawCircle(
            color = Color.Blue,
            radius = 30f,
            center = Offset(touchX, touchY)
        )
    }
}
```

### 4. 视频显示 (VideoView.kt)

```kotlin
@Composable
fun VideoView(
    videoTrack: VideoTrack?,
    modifier: Modifier = Modifier
) {
    val surfaceTextureHelper = remember {
        SurfaceTextureHelper.create("VideoThread", EglBase.create().eglBaseContext)
    }
    
    AndroidView(
        factory = { context ->
            SurfaceViewRenderer(context).apply {
                init(EglBase.create().eglBaseContext, null)
                setScalingType(RendererCommon.ScalingType.SCALE_ASPECT_FIT)
                
                videoTrack?.addSink(this)
            }
        },
        modifier = modifier
    )
}
```

## 功能实现

### 1. 连接流程

```
┌─────────────┐
│  输入地址    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│  连接WebSocket信令服务   │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  初始化WebRTC工厂        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  创建对等连接            │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  添加本地媒体轨道        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  发送SDP Offer          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  接收SDP Answer         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  交换ICE候选            │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  连接成功，开始通信      │
└─────────────────────────┘
```

### 2. 控制命令格式

```json
{
  "type": "motor",
  "action": "forward",
  "speed": 200,
  "timestamp": 1234567890
}
```

支持的操作：
- `forward`: 前进
- `backward`: 后退
- `left`: 左转
- `right`: 右转
- `stop`: 停止

### 3. 权限要求

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

## build.gradle 配置

```gradle
dependencies {
    // Kotlin
    implementation "org.jetbrains.kotlin:kotlin-stdlib:1.9.0"
    implementation "org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.0"
    
    // Jetpack Compose
    implementation "androidx.compose.ui:ui:1.5.0"
    implementation "androidx.compose.material3:material3:1.1.0"
    implementation "androidx.lifecycle:lifecycle-runtime-compose:2.6.0"
    
    // WebRTC
    implementation "org.webrtc:google-webrtc:1.0.32006"
    
    // Network
    implementation "com.squareup.okhttp3:okhttp:4.11.0"
    implementation "com.squareup.okhttp3:logging-interceptor:4.11.0"
    
    // Serialization
    implementation "com.google.code.gson:gson:2.10.1"
    
    // Hilt
    implementation "com.google.dagger:hilt-android:2.47"
    kapt "com.google.dagger:hilt-compiler:2.47"
    
    // DataStore
    implementation "androidx.datastore:datastore-preferences:1.0.0"
    
    // Testing
    testImplementation "junit:junit:4.13.2"
    androidTestImplementation "androidx.test.espresso:espresso-core:3.5.1"
}
```

## 主界面布局 (Compose)

```kotlin
@Composable
fun ControlScreen(
    webRTCManager: WebRTCManager,
    motorController: MotorController
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // 视频显示区域
        VideoView(
            videoTrack = webRTCManager.videoTrack,
            modifier = Modifier
                .fillMaxWidth()
                .height(300.dp)
                .clip(RoundedCornerShape(8.dp))
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // 状态栏
        StatusBar(
            connectionStatus = webRTCManager.connectionStatus,
            fps = webRTCManager.fps,
            latency = webRTCManager.latency
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // 虚拟摇杆
        JoystickView(
            onMotorCommand = { command ->
                motorController.sendCommand(command)
            },
            modifier = Modifier
                .size(250.dp)
                .align(Alignment.CenterHorizontally)
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // 控制按钮
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            Button(onClick = { motorController.emergencyStop() }) {
                Text("紧急停止")
            }
            Button(onClick = { /* 切换摄像头 */ }) {
                Text("切换摄像头")
            }
            Button(onClick = { /* 设置 */ }) {
                Text("设置")
            }
        }
    }
}
```

## 性能优化

### 1. 视频优化
- 使用硬件解码
- 启用自适应码率
- 优化缓冲区大小

### 2. 网络优化
- 启用自适应比特率
- 实现重连机制
- 监控网络质量

### 3. UI优化
- 使用Compose的惰性加载
- 避免重复渲染
- 优化内存使用

## 测试

### 单元测试

```kotlin
@Test
fun testMotorCommandCalculation() {
    val command = calculateMotorCommand(100f, 50f)
    assertEquals(MotorDirection.FORWARD, command.direction)
    assertEquals(150, command.speed)
}
```

### 集成测试

```kotlin
@Test
fun testWebRTCConnection() = runTest {
    val manager = WebRTCManager(context, signalingClient)
    val result = manager.connect("192.168.1.100")
    assertTrue(result)
}
```

## 调试

### 启用日志

```kotlin
class Logger {
    companion object {
        fun d(tag: String, message: String) {
            if (BuildConfig.DEBUG) {
                Log.d(tag, message)
            }
        }
    }
}
```

### WebRTC统计

```kotlin
fun getWebRTCStats(): Map<String, String> {
    val stats = mutableMapOf<String, String>()
    
    peerConnection.getStats { report ->
        report.statsMap.forEach { (_, rtcStats) ->
            when (rtcStats) {
                is RTCInboundRtpStreamStats -> {
                    stats["bytesReceived"] = rtcStats.bytesReceived.toString()
                    stats["packetsLost"] = rtcStats.packetsLost.toString()
                }
                is RTCOutboundRtpStreamStats -> {
                    stats["bytesSent"] = rtcStats.bytesSent.toString()
                }
            }
        }
    }
    
    return stats
}
```

## 常见问题

### Q: 视频显示黑屏
A: 检查摄像头权限和WebRTC连接状态

### Q: 控制命令延迟高
A: 检查网络连接和码率设置

### Q: 应用崩溃
A: 查看日志并检查内存使用情况

## 参考资源

- [WebRTC Android SDK](https://webrtc.googlesource.com/src/+/refs/heads/main/docs/native-code/android/index.md)
- [Jetpack Compose](https://developer.android.com/jetpack/compose)
- [Kotlin Coroutines](https://kotlinlang.org/docs/coroutines-overview.html)

## 下一步

1. 创建Android Studio项目
2. 实现WebRTC管理器
3. 构建UI界面
4. 集成信令客户端
5. 测试和优化
