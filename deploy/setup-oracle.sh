#!/bin/bash
# Oracle Cloud VM 자동 설정 스크립트
# 사용법: curl -sSL <URL> | bash 또는 bash setup-oracle.sh

set -e

echo "============================================"
echo "  주식 검색기 - Oracle Cloud 서버 설정"
echo "============================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# OS 감지
if [ -f /etc/oracle-release ]; then
    OS="oracle"
    PKG_MANAGER="dnf"
elif [ -f /etc/debian_version ]; then
    OS="ubuntu"
    PKG_MANAGER="apt"
else
    print_error "지원하지 않는 OS입니다."
    exit 1
fi

print_status "OS 감지: $OS"

# 1. 시스템 업데이트
echo ""
echo "1. 시스템 업데이트 중..."
if [ "$OS" = "ubuntu" ]; then
    sudo apt update && sudo apt upgrade -y
    sudo apt install -y python3 python3-pip python3-venv git curl
else
    sudo dnf update -y
    sudo dnf install -y python3 python3-pip git curl
fi
print_status "시스템 업데이트 완료"

# 2. 방화벽 포트 열기
echo ""
echo "2. 방화벽 포트 8000 열기..."
if [ "$OS" = "ubuntu" ]; then
    sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
    sudo sh -c "iptables-save > /etc/iptables/rules.v4" 2>/dev/null || true
    # netfilter-persistent가 없으면 설치
    if ! command -v netfilter-persistent &> /dev/null; then
        sudo apt install -y iptables-persistent
    fi
    sudo netfilter-persistent save 2>/dev/null || true
else
    sudo firewall-cmd --permanent --add-port=8000/tcp 2>/dev/null || sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
    sudo firewall-cmd --reload 2>/dev/null || true
fi
print_status "방화벽 포트 열기 완료"

# 3. 프로젝트 디렉토리 생성
echo ""
echo "3. 프로젝트 디렉토리 생성..."
mkdir -p ~/stock_search
cd ~/stock_search
print_status "디렉토리 생성 완료: ~/stock_search"

# 4. 가상환경 생성
echo ""
echo "4. Python 가상환경 생성..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
print_status "가상환경 생성 완료"

# 5. 파일이 이미 있는지 확인
if [ -f "web/server.py" ]; then
    echo ""
    echo "5. 의존성 설치 중... (CPU 버전 PyTorch 사용)"
    pip install -r deploy/requirements-cloud.txt
    print_status "의존성 설치 완료"
else
    print_warning "프로젝트 파일이 없습니다. 먼저 파일을 업로드하세요."
    print_warning "PC에서 다음 명령 실행:"
    echo ""
    echo "  scp -r /home/ybr/stock_search/* ubuntu@<서버IP>:~/stock_search/"
    echo ""
    exit 0
fi

# 6. systemd 서비스 생성
echo ""
echo "6. systemd 서비스 생성..."
USER_NAME=$(whoami)
HOME_DIR=$(eval echo ~$USER_NAME)

sudo tee /etc/systemd/system/stock-search.service > /dev/null << EOF
[Unit]
Description=Stock Search Web Server
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$HOME_DIR/stock_search/web
ExecStart=$HOME_DIR/stock_search/venv/bin/python server.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable stock-search
sudo systemctl start stock-search
print_status "서비스 등록 완료"

# 7. 상태 확인
echo ""
echo "============================================"
echo "  설정 완료!"
echo "============================================"
echo ""

# Public IP 확인
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "확인불가")
echo -e "서버 주소: ${GREEN}http://$PUBLIC_IP:8000${NC}"
echo ""
echo "서비스 상태:"
sudo systemctl status stock-search --no-pager | head -5
echo ""
echo "============================================"
echo "안드로이드 앱에서 위 주소로 접속하세요!"
echo "============================================"
