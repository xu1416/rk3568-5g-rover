# RK3568 5G远程无人操作车系统 - 详细部署指南

本文档提供了 **RK3568小车端** 和 **Android App控制端** 的详细部署步骤、环境配置要求及常见问题解决方案。

---

## 📋 目录

1. [RK3568 小车端部署](#1-rk3568-小车端部署)
2. [Android App 控制端部署](#2-android-app-控制端部署)
3. [网络环境配置方案](#3-网络环境配置方案)
4. [常见问题排查 (FAQ)](#4-常见问题排查-faq)

---

## 1. RK3568 小车端部署

### 1.1 硬件环境要求
*   **核心板**：RK3568 开发板（推荐 4GB LPDDR4 内存及以上）。
*   **存储**：16GB eMMC 或高速 TF 卡。
*   **摄像头**：2个 USB 免驱摄像头（支持 UVC 协议，推荐 1080P/720P）。
*   **电机驱动**：平衡车拆机驱动板或标准串口电机驱动器。
*   **网络**：5G 模组（如移远 RM500Q）或千兆以太网/Wi-Fi 6。

### 1.2 操作系统准备
推荐使用 **Ubuntu 20.04 LTS** 或 **Debian 10 (Buster)** 的 Arm64 版本。确保内核版本支持 RKMPP 硬件编解码（通常 Rockchip 官方固件已包含）。

```bash
# 检查系统架构（应输出 aarch64）
uname -m

# 更新系统软件包
sudo apt update && sudo apt upgrade -y
```

### 1.3 安装系统依赖
在终端执行以下命令，安装 Python 环境、多媒体库及硬件访问工具：

```bash
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    libopencv-dev \
    libatlas-base-dev \
    libavdevice-dev \
    libavfilter-dev \
    libopus-dev \
    libvpx-dev \
    pkg-config \
    libffi-dev \
    libssl-dev \
    git \
    v4l-utils \
    i2c-tools
```

### 1.4 部署项目代码
1.  将 `rk3568_rover` 文件夹上传至开发板 `/home/ubuntu/` 目录。
2.  进入目录并创建 Python 虚拟环境：

```bash
cd /home/ubuntu/rk3568_rover

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装 Python 依赖库
pip install -r requirements.txt
```

### 1.5 硬件配置与测试

#### 摄像头配置
使用 `v4l2-ctl` 查看摄像头设备节点：
```bash
v4l2-ctl --list-devices
```
输出示例：
```text
USB Camera (usb-xhci-hcd.0.auto-1.1):
    /dev/video0
    /dev/video1

USB 2.0 Camera (usb-xhci-hcd.0.auto-1.2):
    /dev/video2
    /dev/video3
```
*记录下 `/dev/video0` (前摄) 和 `/dev/video2` (后摄)。*

#### 配置文件修改
编辑 `config/config.yaml` 文件：
```yaml
camera:
  front_device: "/dev/video0"  # 前置摄像头节点
  rear_device: "/dev/video2"   # 后置摄像头节点
  width: 1280
  height: 720
  fps: 30

motor:
  driver_type: "serial"        # 驱动类型
  port: "/dev/ttyS3"           # 电机驱动板连接的串口
  baudrate: 115200

webrtc:
  signaling_url: "ws://YOUR_SERVER_IP:8080" # 信令服务器地址
```

### 1.6 启动服务
```bash
# 启动主程序
python3 src/main.py
```
*若看到 "System initialized successfully" 日志，说明启动成功。*

---

## 2. Android App 控制端部署

### 2.1 开发环境准备
*   **操作系统**：Windows 10/11, macOS, 或 Linux。
*   **IDE**：Android Studio Koala (2024.1.1) 或更新版本。
*   **JDK**：Java Development Kit 17。
*   **Android SDK**：API Level 34 (Android 14)，最低支持 API 26。

### 2.2 导入与编译
1.  启动 Android Studio，选择 **Open**。
2.  导航至 `rover-android-app` 目录并点击 **OK**。
3.  等待 Gradle Sync 完成（需保持网络连接以下载依赖）。
4.  连接 Android 手机（需开启“开发者模式”和“USB调试”）。
5.  点击顶部工具栏的绿色 **Run** 按钮 (Shift+F10)。

### 2.3 权限授予
App 首次启动时会请求以下权限，请务必**全部允许**：
*   📷 **相机**：用于视频通话及画中画显示。
*   🎤 **麦克风**：用于采集语音发送给小车。
*   📍 **位置信息**：用于蓝牙/Wi-Fi 扫描（Android 系统要求）。

---

## 3. 网络环境配置方案

由于系统依赖 WebRTC 进行实时通信，网络连通性是关键。

### 方案 A：局域网调试 (推荐初次使用)
*   **配置**：小车和控制端（手机/电脑）连接同一个 Wi-Fi 路由器。
*   **信令服务器**：可以在小车端本地运行信令服务，或者在局域网内的电脑上运行。
*   **地址设置**：App 端输入小车的局域网 IP（如 `ws://192.168.1.105:8080`）。

### 方案 B：5G 远程控制 (公网服务器)
*   **配置**：小车通过 5G 联网，控制端通过 4G/5G/Wi-Fi 联网。
*   **要求**：需要一台具有**公网 IP** 的云服务器（阿里云/腾讯云/AWS）。
*   **部署**：
    1.  在云服务器上部署 WebRTC 信令服务器 (Signaling Server)。
    2.  部署 COTURN 服务（用于 STUN/TURN 穿透，解决 NAT 问题）。
*   **地址设置**：小车和 App 均指向云服务器的公网 IP。

### 方案 C：虚拟局域网 (VPN) - 最简易远程方案
*   **工具**：Tailscale, ZeroTier, 或 Frp。
*   **配置**：
    1.  在小车端安装 Tailscale 并登录。
    2.  在手机端安装 Tailscale App 并登录同一账号。
    3.  系统会自动分配虚拟 IP（如 `100.x.x.x`）。
*   **优势**：无需公网 IP，无需配置复杂的 TURN 服务器，直接像局域网一样使用。

---

## 4. 常见问题排查 (FAQ)

### Q1: 启动时报错 "Cannot open camera device"
*   **原因**：摄像头未连接、权限不足或设备节点配置错误。
*   **解决**：
    1.  运行 `ls -l /dev/video*` 检查设备是否存在。
    2.  运行 `sudo chmod 777 /dev/video*` 赋予权限。
    3.  检查 `config.yaml` 中的设备节点是否与 `v4l2-ctl` 输出一致。

### Q2: 视频画面卡顿或延迟高
*   **原因**：网络带宽不足或信号差。
*   **解决**：
    1.  降低分辨率：在 `config.yaml` 中将分辨率改为 640x480。
    2.  降低帧率：将 `fps` 设置为 15 或 20。
    3.  检查 5G 信号强度，确保天线连接良好。

### Q3: 紧急停车按钮无反应
*   **原因**：网络完全断开或指令丢失。
*   **解决**：
    1.  这是网络系统的物理限制。
    2.  **防失控机制**（已内置）会在网络断开 500ms 后自动切断电机，作为最后一道安全防线。

### Q4: 网页端显示 "Signal Lost"
*   **原因**：WebRTC 连接未建立。
*   **解决**：
    1.  检查小车端程序是否运行。
    2.  检查浏览器控制台 (F12) 是否有报错。
    3.  确认信令服务器地址配置正确且可访问。
