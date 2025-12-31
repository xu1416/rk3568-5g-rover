# RK3568 5G远程无人操作车系统 - 项目交付文档

## 📦 项目包含内容

本压缩包 `rk3568_rover_system_v1.0.zip` 包含以下三个核心模块：

1.  **rk3568_rover/** - 小车端核心系统 (Python)
    *   运行在RK3568开发板上
    *   负责视频采集、编码、电机控制和WebRTC通信
    *   包含防失控看门狗机制

2.  **rover-android-app/** - Android控制端源码 (Kotlin)
    *   运行在Android手机/平板上
    *   提供实时视频显示、语音通话和虚拟摇杆控制

3.  **rover_web_control/** - 网页控制端源码 (React + TypeScript)
    *   运行在浏览器中
    *   提供赛博朋克风格的HUD界面、画中画视频和急停功能

---

## 🚀 快速开始

### 1. RK3568小车端部署

1.  将 `rk3568_rover` 文件夹传输到开发板。
2.  运行安装脚本：
    ```bash
    cd rk3568_rover
    sudo ./scripts/install.sh
    ```
3.  修改配置文件 `config/config.yaml`，设置信令服务器地址。
4.  启动服务：
    ```bash
    python3 src/main.py
    ```

### 2. Android App编译

1.  使用 Android Studio 打开 `rover-android-app` 目录。
2.  等待 Gradle 同步完成。
3.  连接 Android 设备并点击 "Run" 按钮。

### 3. 网页控制端运行

1.  进入目录：
    ```bash
    cd rover_web_control
    ```
2.  安装依赖：
    ```bash
    pnpm install
    ```
3.  启动开发服务器：
    ```bash
    pnpm dev
    ```

---

## ⚠️ 安全注意事项

1.  **紧急停车**：网页端和App端均设有红色急停按钮，按下后会立即切断电机电源。
2.  **防失控机制**：小车端内置看门狗，若 500ms 内未收到控制指令，将自动刹车。
3.  **网络延迟**：建议在 5G 或 Wi-Fi 6 环境下使用，以保证视频低延迟。

---

## 📞 技术支持

如有任何问题，请参考各目录下的 `README.md` 文档或联系开发团队。
