# RK3568远程无人操作车系统 - 部署和运维指南

## 部署前检查清单

### 硬件检查

- [ ] RK3568开发板已安装
- [ ] 前后USB摄像头已连接
- [ ] 麦克风和扬声器已连接
- [ ] 平衡车驱动板已连接到串口
- [ ] 5G模块已安装（可选）
- [ ] 电源供应充足

### 软件检查

- [ ] Linux系统已安装（Ubuntu 20.04/22.04或Armbian）
- [ ] Python 3.8+已安装
- [ ] 所有依赖库已安装
- [ ] RKMPP支持已验证

## 系统部署步骤

### 1. 基础系统配置

```bash
# 更新系统
sudo apt-get update
sudo apt-get upgrade -y

# 设置主机名
sudo hostnamectl set-hostname rover-01

# 配置时区
sudo timedatectl set-timezone Asia/Shanghai

# 配置网络（如果使用WiFi）
sudo nmcli device wifi connect "SSID" password "PASSWORD"
```

### 2. 安装项目

```bash
# 克隆项目
git clone <repository_url> /opt/rover
cd /opt/rover

# 运行安装脚本
sudo bash scripts/install.sh

# 验证安装
python3 -c "import cv2; import aiortc; print('Installation OK')"
```

### 3. 配置系统

编辑 `/opt/rover/config/config.yaml`：

```yaml
system:
  device_name: "rover-01"
  debug_mode: false
  log_level: "INFO"

camera:
  front:
    device_id: 0
  rear:
    device_id: 1

motor_control:
  serial:
    port: /dev/ttyUSB0
    baudrate: 115200

webrtc:
  signaling:
    server_url: "ws://control-server:8765"
```

### 4. 启动服务

#### 方式一：直接运行

```bash
cd /opt/rover/src
python3 main.py
```

#### 方式二：使用systemd服务

```bash
# 启用服务
sudo systemctl enable rover

# 启动服务
sudo systemctl start rover

# 查看状态
sudo systemctl status rover

# 查看日志
sudo journalctl -u rover -f
```

#### 方式三：使用Docker

```bash
# 构建镜像
docker build -t rover:latest .

# 运行容器
docker run -d \
  --name rover \
  --device /dev/video0 \
  --device /dev/video1 \
  --device /dev/ttyUSB0 \
  --device /dev/mpp_service \
  --device /dev/rga \
  -v /opt/rover/config:/app/config \
  rover:latest
```

## 运维指南

### 日志管理

```bash
# 查看实时日志
tail -f /var/log/rk3568_rover.log

# 查看特定级别日志
grep "ERROR" /var/log/rk3568_rover.log

# 日志轮转配置（logrotate）
sudo tee /etc/logrotate.d/rover > /dev/null <<EOF
/var/log/rk3568_rover.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF
```

### 性能监控

```bash
# 实时监控CPU和内存
top -p $(pgrep -f "python3 main.py")

# 监控网络流量
iftop -i eth0

# 监控摄像头
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --all

# 检查RKMPP性能
ffmpeg -v debug -init_hw_device rkmpp=rk
```

### 故障排除

#### 问题1：摄像头无法打开

```bash
# 检查设备
ls -la /dev/video*

# 测试摄像头
ffplay /dev/video0

# 检查权限
sudo usermod -aG video $USER

# 重新启动服务
sudo systemctl restart rover
```

#### 问题2：电机不响应

```bash
# 检查串口
ls -la /dev/ttyUSB*

# 测试串口连接
minicom -D /dev/ttyUSB0 -b 115200

# 查看驱动板日志
dmesg | grep ttyUSB
```

#### 问题3：WebRTC连接失败

```bash
# 检查网络连接
ping 8.8.8.8

# 检查防火墙
sudo ufw status

# 允许WebRTC端口
sudo ufw allow 8765/tcp
sudo ufw allow 8765/udp

# 测试STUN服务器
nc -zv stun.l.google.com 19302
```

#### 问题4：高CPU使用率

```bash
# 分析进程
ps aux | grep python3

# 检查线程数
cat /proc/$(pgrep -f "python3 main.py")/status | grep Threads

# 启用性能分析
python3 -m cProfile -s cumtime src/main.py
```

### 备份和恢复

```bash
# 备份配置
sudo tar -czf /backup/rover-config-$(date +%Y%m%d).tar.gz /opt/rover/config

# 备份系统
sudo tar -czf /backup/rover-system-$(date +%Y%m%d).tar.gz /opt/rover

# 恢复配置
sudo tar -xzf /backup/rover-config-20240101.tar.gz -C /

# 恢复系统
sudo tar -xzf /backup/rover-system-20240101.tar.gz -C /
```

## 性能调优

### 1. 内核参数优化

```bash
# 编辑sysctl配置
sudo nano /etc/sysctl.conf

# 添加以下参数
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_rmem=4096 87380 67108864
net.ipv4.tcp_wmem=4096 65536 67108864

# 应用配置
sudo sysctl -p
```

### 2. CPU亲和性设置

```bash
# 为Python进程设置CPU亲和性
taskset -cp 0,1,2,3 $(pgrep -f "python3 main.py")

# 在config.yaml中配置
performance:
  cpu_affinity: [0, 1, 2, 3]
```

### 3. 网络优化

```bash
# 启用TSO（TCP Segment Offload）
sudo ethtool -K eth0 tso on

# 调整MTU
sudo ip link set dev eth0 mtu 9000

# 启用网络硬件加速
sudo ethtool -K eth0 gro on
```

### 4. 视频编码优化

```yaml
# config.yaml
video_encoding:
  preset: "fast"           # 编码速度
  bitrate: 1024            # 码率
  gop: 60                  # GOP大小
  hardware_acceleration: true
  rkmpp_enabled: true
```

## 安全加固

### 1. 防火墙配置

```bash
# 启用UFW
sudo ufw enable

# 允许SSH
sudo ufw allow 22/tcp

# 允许WebRTC
sudo ufw allow 8765/tcp
sudo ufw allow 8765/udp

# 拒绝其他所有连接
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### 2. 用户权限

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash rover

# 赋予必要权限
sudo usermod -aG video rover
sudo usermod -aG audio rover
sudo usermod -aG dialout rover

# 限制sudo权限
sudo visudo
# rover ALL=(ALL) NOPASSWD: /usr/bin/systemctl
```

### 3. 认证和加密

```bash
# 生成SSL证书
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/rover.key \
  -out /etc/ssl/certs/rover.crt

# 在config.yaml中启用SSL
security:
  use_ssl: true
  cert_file: "/etc/ssl/certs/rover.crt"
  key_file: "/etc/ssl/private/rover.key"
```

## 监控和告警

### 1. 系统监控

```bash
# 安装Prometheus客户端
pip3 install prometheus-client

# 在main.py中添加指标导出
from prometheus_client import Counter, Gauge, start_http_server

# 启动指标服务器
start_http_server(9090)
```

### 2. 日志聚合

```bash
# 安装Loki客户端
pip3 install python-logging-loki

# 配置日志转发
import logging_loki

handler = logging_loki.LokiHandler(
    url="http://loki-server:3100/loki/api/v1/push",
    tags={"job": "rover"},
    auth=("user", "password"),
)
```

### 3. 告警规则

```yaml
# prometheus告警规则
groups:
  - name: rover
    rules:
      - alert: RoverHighCPU
        expr: process_cpu_seconds_total > 0.8
        for: 5m
        annotations:
          summary: "Rover CPU usage is high"
      
      - alert: RoverHighMemory
        expr: process_resident_memory_bytes > 400000000
        for: 5m
        annotations:
          summary: "Rover memory usage is high"
      
      - alert: RoverDisconnected
        expr: rover_webrtc_peers == 0
        for: 1m
        annotations:
          summary: "Rover is disconnected"
```

## 更新和升级

### 1. 更新代码

```bash
cd /opt/rover
git pull origin main
sudo systemctl restart rover
```

### 2. 更新依赖

```bash
pip3 install --upgrade -r requirements.txt
sudo systemctl restart rover
```

### 3. 系统更新

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo reboot
```

## 灾难恢复

### 1. 快照备份

```bash
# 创建系统快照
sudo tar -czf /backup/rover-snapshot-$(date +%Y%m%d-%H%M%S).tar.gz /opt/rover

# 列出快照
ls -lh /backup/rover-snapshot-*.tar.gz
```

### 2. 恢复程序

```bash
# 停止服务
sudo systemctl stop rover

# 恢复快照
sudo tar -xzf /backup/rover-snapshot-20240101-120000.tar.gz -C /

# 启动服务
sudo systemctl start rover
```

## 常见问题

### Q: 如何查看实时性能指标？
A: 使用 `top` 命令或访问Prometheus仪表板

### Q: 如何远程管理系统？
A: 使用SSH和systemctl命令

### Q: 如何处理磁盘满的情况？
A: 清理日志文件或扩展存储空间

### Q: 如何实现自动重启？
A: 在systemd服务中配置 `Restart=always`

## 参考资源

- [systemd服务管理](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Linux性能优化](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/index.html)
- [Docker部署](https://docs.docker.com/)
