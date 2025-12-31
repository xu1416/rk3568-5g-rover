# RK3568 Remote Rover System

一个基于RK3568开发板的专业级履带式5G远程无人操作车系统，支持实时双摄像头视频、双向语音通话和实时操作控制。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    5G网络                                │
└──────────────┬──────────────────────────────┬────────────┘
               │                              │
        ┌──────▼──────┐              ┌────────▼────────┐
        │  RK3568小车端 │              │  Android App    │
        │   (Python)   │◄────────────►│   (Kotlin/Java) │
        └──────┬──────┘              └────────┬────────┘
               │                              │
        ┌──────▼──────────────────────────────▼──────┐
        │         WebRTC P2P通信                     │
        │  (视频/音频/数据通道)                      │
        └──────────────────────────────────────────┘
```

## 核心功能

### 📷 双摄像头系统
- USB免驱动摄像头（前后各一个）
- 实时1280x720@30fps视频采集
- 支持摄像头切换和同时显示

### 🎥 实时视频编码
- H.264硬件加速编码（RKMPP）
- 自适应码率（512-2048 kbps）
- 低延迟传输（<500ms）

### 🎤 双向语音通话
- Opus音频编码
- 双向/单向语音模式
- 16kHz采样率，24kbps码率

### 🕹️ 实时操作控制
- 虚拟摇杆控制
- 实时指令传输
- 电机响应<100ms

### 🤖 电机驱动
- 平衡车驱动板集成
- 支持串口/GPIO控制
- 可调速度和方向

### 🌐 WebRTC通信
- 点对点低延迟通信
- 自动NAT穿透
- 数据通道控制指令

## 硬件要求

### RK3568开发板
- CPU: 四核ARM Cortex-A55 @ 2.0GHz
- RAM: 2GB/4GB
- 存储: eMMC或SD卡
- VPU: 支持H.264硬件编码

### 外围设备
- USB摄像头 x2（免驱动）
- 麦克风和扬声器
- 平衡车驱动板
- 5G模块（可选）

## 软件要求

### 系统
- Linux 64位（Ubuntu 20.04/22.04 或 Armbian）
- Rockchip BSP内核 5.10 LTS或6.1 LTS
- Python 3.8+

### 依赖库
```bash
pip install -r requirements.txt
```

主要依赖：
- OpenCV 4.8+
- aiortc 1.5+
- PyAudio 0.2+
- PyYAML 6.0+

## 项目结构

```
rk3568_rover/
├── src/
│   ├── main.py                 # 主应用程序
│   ├── logger.py               # 日志系统
│   ├── config_manager.py       # 配置管理
│   ├── camera_manager.py       # 摄像头管理
│   ├── video_encoder.py        # 视频编码
│   ├── audio_processor.py      # 音频处理
│   ├── motor_controller.py     # 电机控制
│   └── webrtc_service.py       # WebRTC服务
├── config/
│   └── config.yaml             # 配置文件
├── tests/                      # 单元测试
├── docs/                       # 文档
├── scripts/                    # 辅助脚本
├── requirements.txt            # Python依赖
└── README.md                   # 本文件
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository_url>
cd rk3568_rover

# 安装依赖
pip install -r requirements.txt

# 检查RKMPP支持
ls -l /dev/mpp_service /dev/rga
```

### 2. 配置系统

编辑 `config/config.yaml`：

```yaml
camera:
  front:
    device_id: 0          # 前摄像头设备ID
    resolution: [1280, 720]
    fps: 30
  rear:
    device_id: 1          # 后摄像头设备ID
    resolution: [1280, 720]
    fps: 30

motor_control:
  serial:
    port: /dev/ttyUSB0    # 电机驱动板串口
    baudrate: 115200

webrtc:
  signaling:
    server_url: ws://localhost:8765
```

### 3. 启动小车端

```bash
cd src
python3 main.py
```

### 4. 连接Android App

- 在Android设备上安装控制App
- 输入小车端的IP地址和端口
- 点击连接

## 配置详解

### 摄像头配置

```yaml
camera:
  front:
    device_id: 0              # /dev/video0
    resolution: [1280, 720]   # 分辨率
    fps: 30                   # 帧率
    format: "MJPEG"           # 格式
    enabled: true
```

### 视频编码配置

```yaml
video_encoding:
  codec: "h264"               # 编码格式
  profile: "baseline"         # H.264 Profile
  level: "3.1"                # H.264 Level
  bitrate: 1024               # 码率 (kbps)
  gop: 60                      # GOP大小
  hardware_acceleration: true  # 硬件加速
  rkmpp_enabled: true         # 使用RKMPP
  preset: "medium"            # 编码速度
```

### 音频配置

```yaml
audio:
  microphone:
    sample_rate: 16000        # 采样率
    channels: 1               # 声道数
    chunk_size: 1024          # 缓冲大小
  encoding:
    codec: "opus"             # 编码格式
    bitrate: 24               # 码率 (kbps)
    frame_duration: 20        # 帧长 (ms)
```

### 电机控制配置

```yaml
motor_control:
  driver_type: "balance_car"  # 驱动板类型
  serial:
    port: "/dev/ttyUSB0"      # 串口
    baudrate: 115200          # 波特率
  motor:
    max_speed: 255            # 最大速度
    timeout: 5000             # 超时 (ms)
```

## API接口

### 摄像头管理

```python
from camera_manager import get_camera_manager

manager = get_camera_manager()
manager.initialize()
manager.start_capture()

# 获取最新帧
front_frame = manager.get_front_frame()
rear_frame = manager.get_rear_frame()

# 获取统计信息
stats = manager.get_stats()
print(f"Front FPS: {stats['front_fps']}")
```

### 电机控制

```python
from motor_controller import get_motor_controller

controller = get_motor_controller()
controller.connect()

# 移动
controller.move_forward(200)
controller.turn_left(150)
controller.stop()

# 获取状态
status = controller.get_status()
```

### 音频处理

```python
from audio_processor import get_audio_processor

processor = get_audio_processor()
processor.initialize()
processor.start_capture()

# 获取音频帧
frame = processor.get_latest_frame()

# 播放音频
processor.play_audio(audio_data)
```

### WebRTC服务

```python
from webrtc_service import get_webrtc_service

service = await get_webrtc_service()

# 创建对等连接
pc = await service.create_peer_connection("peer_id")

# 处理SDP offer
answer_sdp = await service.handle_offer("peer_id", offer_sdp)

# 添加媒体轨道
await service.add_video_track("peer_id", video_track)
await service.add_audio_track("peer_id", audio_track)
```

## 性能指标

| 指标 | 目标值 | 备注 |
|------|--------|------|
| 视频延迟 | <500ms | 端到端延迟 |
| 音频延迟 | <200ms | 端到端延迟 |
| 视频分辨率 | 1280x720@30fps | 前后摄像头 |
| 视频码率 | 1-2 Mbps | 自适应 |
| 音频码率 | 24 kbps | Opus编码 |
| 控制响应 | <100ms | 指令到执行 |
| CPU使用率 | <60% | 空闲状态 |
| 内存使用 | <400MB | 运行时 |

## 故障排除

### 摄像头无法打开

```bash
# 检查设备
ls -la /dev/video*

# 测试摄像头
v4l2-ctl --list-devices
```

### 电机不响应

```bash
# 检查串口
ls -la /dev/ttyUSB*

# 测试串口连接
minicom -D /dev/ttyUSB0 -b 115200
```

### RKMPP不可用

```bash
# 检查内核模块
ls -l /dev/mpp_service /dev/rga

# 检查FFmpeg支持
ffmpeg -codecs | grep h264
```

### WebRTC连接失败

- 检查防火墙设置
- 验证STUN服务器可访问
- 查看日志文件获取详细错误信息

## 日志

日志文件位置：`/var/log/rk3568_rover.log`

设置日志级别：
```bash
export ROVER_LOG_LEVEL=DEBUG
python3 src/main.py
```

## 性能优化

### 1. 硬件加速

确保RKMPP正确配置：
```bash
# 验证RKMPP
ffmpeg -v debug -init_hw_device rkmpp=rk
```

### 2. 网络优化

- 使用5G网络以获得最低延迟
- 配置合适的码率以平衡质量和带宽
- 启用自适应码率

### 3. CPU优化

- 设置CPU亲和性
- 使用线程池管理
- 启用硬件加速

## 开发指南

### 添加新功能

1. 在 `src/` 中创建新模块
2. 实现功能逻辑
3. 在 `main.py` 中集成
4. 添加单元测试
5. 更新文档

### 测试

```bash
cd tests
pytest -v
```

## 许可证

MIT License

## 支持

如有问题或建议，请提交Issue或Pull Request。

## 更新日志

### v1.0.0 (2025-12-30)
- 初始版本发布
- 支持双摄像头实时视频
- 实现WebRTC通信
- 集成电机控制
- 完整的音视频处理

## 致谢

感谢所有贡献者和使用者的支持！
