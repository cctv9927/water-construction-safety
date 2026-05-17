#!/bin/bash
# =============================================================================
# 水利工地安全监管系统 - 设备模拟器一键启动脚本
# 
# 功能：一键启动所有设备模拟器（用于无真实设备时测试完整数据流）
# 
# 支持的模拟器：
#   1. sensor-collector/simulator.py  - 传感器数据模拟
#   2. video-streamer/                - 视频流模拟
#   3. drone-integration/            - 无人机巡检模拟
#
# 使用方法:
#   ./test_device_simulation.sh              # 启动所有模拟器
#   ./test_device_simulation.sh --sensors    # 仅启动传感器模拟器
#   ./test_device_simulation.sh --video      # 仅启动视频流模拟器
#   ./test_device_simulation.sh --drone      # 仅启动无人机模拟器
#   ./test_device_simulation.sh --stop       # 停止所有模拟器
#
# 作者：水利工地安全监管系统开发组
# 版本：v1.0
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs/simulation"
mkdir -p "$LOG_DIR"

# PID 文件目录
PID_DIR="$PROJECT_ROOT/.pids"
mkdir -p "$PID_DIR"

# 打印带颜色的消息
print_header() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 检查依赖
check_dependencies() {
    print_header "检查依赖"
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        print_success "Python3: $(python3 --version)"
    else
        print_error "Python3 未安装"
        exit 1
    fi
    
    # 检查 Node.js (for drone simulator)
    if command -v node &> /dev/null; then
        print_success "Node.js: $(node --version)"
    else
        print_warning "Node.js 未安装（无人机模拟器将不可用）"
    fi
    
    # 检查 pip
    if python3 -m pip --version &> /dev/null; then
        print_success "pip: 已安装"
    else
        print_warning "pip 未安装"
    fi
    
    # 检查必要的 Python 包
    echo ""
    print_info "检查 Python 包..."
    
    if python3 -c "import paho.mqtt" 2>/dev/null; then
        print_success "paho-mqtt: 已安装"
    else
        print_warning "paho-mqtt 未安装（MQTT模拟将不可用）"
        print_info "安装命令: pip install paho-mqtt"
    fi
    
    echo ""
}

# 启动传感器模拟器
start_sensor_simulator() {
    print_header "启动传感器模拟器"
    
    SENSOR_DIR="$PROJECT_ROOT/sensor-collector"
    
    if [ ! -d "$SENSOR_DIR" ]; then
        print_error "传感器目录不存在: $SENSOR_DIR"
        return 1
    fi
    
    cd "$SENSOR_DIR"
    
    # 检查脚本是否存在
    if [ ! -f "simulator.py" ]; then
        print_error "simulator.py 不存在"
        return 1
    fi
    
    # 检查执行权限
    if [ ! -x "simulator.py" ]; then
        chmod +x simulator.py
        print_info "已添加执行权限"
    fi
    
    # 启动模拟器（真实设备模式，不连接ThingsBoard）
    print_info "启动真实设备模拟模式..."
    print_info "按 Ctrl+C 停止"
    echo ""
    
    # 后台运行
    nohup python3 simulator.py --mode real_device --interval 5 > "$LOG_DIR/sensor_simulator.log" 2>&1 &
    SENSOR_PID=$!
    echo $SENSOR_PID > "$PID_DIR/sensor_simulator.pid"
    
    sleep 2
    
    if kill -0 $SENSOR_PID 2>/dev/null; then
        print_success "传感器模拟器已启动 (PID: $SENSOR_PID)"
        print_info "日志文件: $LOG_DIR/sensor_simulator.log"
    else
        print_error "传感器模拟器启动失败"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# 启动视频流模拟器
start_video_simulator() {
    print_header "启动视频流模拟器"
    
    VIDEO_DIR="$PROJECT_ROOT/video-streamer"
    
    if [ ! -d "$VIDEO_DIR" ]; then
        print_error "视频流目录不存在: $VIDEO_DIR"
        return 1
    fi
    
    # 检查视频流模拟脚本
    if [ -f "$VIDEO_DIR/test_stream.py" ]; then
        cd "$VIDEO_DIR"
        
        # 检查执行权限
        if [ ! -x "test_stream.py" ]; then
            chmod +x test_stream.py
        fi
        
        print_info "启动视频流模拟..."
        
        # 后台运行
        nohup python3 test_stream.py > "$LOG_DIR/video_simulator.log" 2>&1 &
        VIDEO_PID=$!
        echo $VIDEO_PID > "$PID_DIR/video_simulator.pid"
        
        sleep 2
        
        if kill -0 $VIDEO_PID 2>/dev/null; then
            print_success "视频流模拟器已启动 (PID: $VIDEO_PID)"
        else
            print_warning "视频流模拟器启动失败（可能需要安装依赖）"
        fi
        
        cd "$PROJECT_ROOT"
    else
        print_warning "test_stream.py 不存在，跳过视频流模拟"
        print_info "提示: 创建 video-streamer/test_stream.py 启用视频流模拟"
    fi
}

# 启动无人机模拟器
start_drone_simulator() {
    print_header "启动无人机模拟器"
    
    DRONE_DIR="$PROJECT_ROOT/drone-integration"
    
    if [ ! -d "$DRONE_DIR" ]; then
        print_error "无人机目录不存在: $DRONE_DIR"
        return 1
    fi
    
    if ! command -v node &> /dev/null; then
        print_warning "Node.js 未安装，跳过无人机模拟"
        return 0
    fi
    
    cd "$DRONE_DIR"
    
    # 检查依赖
    if [ -f "package.json" ]; then
        if [ ! -d "node_modules" ]; then
            print_info "安装 Node.js 依赖..."
            npm install --silent 2>/dev/null || true
        fi
    fi
    
    # 检查 TypeScript 配置
    if [ -f "tsconfig.json" ]; then
        print_info "TypeScript 配置: tsconfig.json"
    fi
    
    print_info "启动无人机巡检模拟..."
    print_info "使用 --inspection 参数启动完整巡检模式"
    echo ""
    
    # 后台运行
    nohup npm run dev:simulator > "$LOG_DIR/drone_simulator.log" 2>&1 &
    DRONE_PID=$!
    echo $DRONE_PID > "$PID_DIR/drone_simulator.pid"
    
    sleep 3
    
    if kill -0 $DRONE_PID 2>/dev/null; then
        print_success "无人机模拟器已启动 (PID: $DRONE_PID)"
        print_info "日志文件: $LOG_DIR/drone_simulator.log"
    else
        print_warning "无人机模拟器启动失败（请检查 node_modules）"
    fi
    
    cd "$PROJECT_ROOT"
}

# 停止所有模拟器
stop_all() {
    print_header "停止所有设备模拟器"
    
    if [ -f "$PID_DIR/sensor_simulator.pid" ]; then
        SENSOR_PID=$(cat "$PID_DIR/sensor_simulator.pid")
        if kill -0 $SENSOR_PID 2>/dev/null; then
            kill $SENSOR_PID 2>/dev/null || true
            print_success "传感器模拟器已停止 (PID: $SENSOR_PID)"
        fi
        rm -f "$PID_DIR/sensor_simulator.pid"
    fi
    
    if [ -f "$PID_DIR/video_simulator.pid" ]; then
        VIDEO_PID=$(cat "$PID_DIR/video_simulator.pid")
        if kill -0 $VIDEO_PID 2>/dev/null; then
            kill $VIDEO_PID 2>/dev/null || true
            print_success "视频流模拟器已停止 (PID: $VIDEO_PID)"
        fi
        rm -f "$PID_DIR/video_simulator.pid"
    fi
    
    if [ -f "$PID_DIR/drone_simulator.pid" ]; then
        DRONE_PID=$(cat "$PID_DIR/drone_simulator.pid")
        if kill -0 $DRONE_PID 2>/dev/null; then
            kill $DRONE_PID 2>/dev/null || true
            print_success "无人机模拟器已停止 (PID: $DRONE_PID)"
        fi
        rm -f "$PID_DIR/drone_simulator.pid"
    fi
    
    # 也尝试清理孤儿进程
    pkill -f "simulator.py.*real_device" 2>/dev/null || true
    pkill -f "test_stream.py" 2>/dev/null || true
    pkill -f "drone-integration" 2>/dev/null || true
    
    echo ""
    print_success "所有模拟器已停止"
}

# 显示状态
show_status() {
    print_header "设备模拟器状态"
    
    echo "PID 文件目录: $PID_DIR"
    echo "日志目录: $LOG_DIR"
    echo ""
    
    # 检查传感器模拟器
    if [ -f "$PID_DIR/sensor_simulator.pid" ]; then
        SENSOR_PID=$(cat "$PID_DIR/sensor_simulator.pid")
        if kill -0 $SENSOR_PID 2>/dev/null; then
            echo -e "${GREEN}●${NC} 传感器模拟器: 运行中 (PID: $SENSOR_PID)"
        else
            echo -e "${RED}●${NC} 传感器模拟器: 已停止 (陈旧PID)"
        fi
    else
        echo -e "${YELLOW}●${NC} 传感器模拟器: 未运行"
    fi
    
    # 检查视频流模拟器
    if [ -f "$PID_DIR/video_simulator.pid" ]; then
        VIDEO_PID=$(cat "$PID_DIR/video_simulator.pid")
        if kill -0 $VIDEO_PID 2>/dev/null; then
            echo -e "${GREEN}●${NC} 视频流模拟器: 运行中 (PID: $VIDEO_PID)"
        else
            echo -e "${RED}●${NC} 视频流模拟器: 已停止 (陈旧PID)"
        fi
    else
        echo -e "${YELLOW}●${NC} 视频流模拟器: 未运行"
    fi
    
    # 检查无人机模拟器
    if [ -f "$PID_DIR/drone_simulator.pid" ]; then
        DRONE_PID=$(cat "$PID_DIR/drone_simulator.pid")
        if kill -0 $DRONE_PID 2>/dev/null; then
            echo -e "${GREEN}●${NC} 无人机模拟器: 运行中 (PID: $DRONE_PID)"
        else
            echo -e "${RED}●${NC} 无人机模拟器: 已停止 (陈旧PID)"
        fi
    else
        echo -e "${YELLOW}●${NC} 无人机模拟器: 未运行"
    fi
    
    echo ""
}

# 查看日志
show_logs() {
    print_header "模拟器日志"
    
    echo "可用日志文件:"
    echo ""
    
    if [ -f "$LOG_DIR/sensor_simulator.log" ]; then
        echo -e "${BLUE}[传感器模拟器]${NC} $LOG_DIR/sensor_simulator.log"
    fi
    
    if [ -f "$LOG_DIR/video_simulator.log" ]; then
        echo -e "${BLUE}[视频流模拟器]${NC} $LOG_DIR/video_simulator.log"
    fi
    
    if [ -f "$LOG_DIR/drone_simulator.log" ]; then
        echo -e "${BLUE}[无人机模拟器]${NC} $LOG_DIR/drone_simulator.log"
    fi
    
    echo ""
    echo "查看日志命令:"
    echo "  tail -f $LOG_DIR/sensor_simulator.log"
    echo "  tail -f $LOG_DIR/drone_simulator.log"
}

# 显示帮助
show_help() {
    echo "水利工地安全监管系统 - 设备模拟器启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --all       启动所有模拟器（默认）"
    echo "  --sensors   仅启动传感器模拟器"
    echo "  --video     仅启动视频流模拟器"
    echo "  --drone     仅启动无人机模拟器"
    echo "  --stop      停止所有模拟器"
    echo "  --status    查看模拟器状态"
    echo "  --logs      查看日志文件位置"
    echo "  --help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                  # 启动所有模拟器"
    echo "  $0 --sensors        # 仅启动传感器"
    echo "  $0 --drone --sensors # 启动无人机和传感器"
    echo "  $0 --stop           # 停止所有"
    echo ""
}

# 主函数
main() {
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --stop|-s)
            stop_all
            exit 0
            ;;
        --status)
            show_status
            exit 0
            ;;
        --logs)
            show_logs
            exit 0
            ;;
        --sensors)
            check_dependencies
            start_sensor_simulator
            ;;
        --video)
            check_dependencies
            start_video_simulator
            ;;
        --drone)
            check_dependencies
            start_drone_simulator
            ;;
        --all|*)
            check_dependencies
            start_sensor_simulator
            start_video_simulator
            start_drone_simulator
            
            echo ""
            print_header "启动完成"
            show_status
            echo ""
            show_logs
            echo ""
            print_info "按 Ctrl+C 停止所有模拟器，或运行: $0 --stop"
            ;;
    esac
}

main "$@"
