#!/bin/bash
# PC에서 Oracle Cloud로 파일 업로드 스크립트
# 사용법: ./upload-to-cloud.sh <서버IP> <SSH키경로>

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "============================================"
echo "  주식 검색기 - 클라우드 업로드"
echo "============================================"

# 파라미터 확인
if [ -z "$1" ]; then
    echo -e "${YELLOW}사용법: $0 <서버IP> [SSH키경로] [사용자명]${NC}"
    echo ""
    echo "예시:"
    echo "  $0 140.238.xxx.xxx"
    echo "  $0 140.238.xxx.xxx ~/Downloads/ssh-key.key"
    echo "  $0 140.238.xxx.xxx ~/Downloads/ssh-key.key ubuntu"
    echo ""
    read -p "서버 IP 주소: " SERVER_IP
else
    SERVER_IP=$1
fi

if [ -z "$2" ]; then
    # SSH 키 자동 검색
    SSH_KEY=$(ls ~/Downloads/ssh-key*.key 2>/dev/null | head -1)
    if [ -z "$SSH_KEY" ]; then
        SSH_KEY=$(ls ~/.ssh/id_rsa 2>/dev/null | head -1)
    fi
    if [ -z "$SSH_KEY" ]; then
        read -p "SSH 키 경로: " SSH_KEY
    fi
else
    SSH_KEY=$2
fi

if [ -z "$3" ]; then
    # Oracle Linux: opc, Ubuntu: ubuntu
    SSH_USER="ubuntu"
else
    SSH_USER=$3
fi

echo ""
echo -e "서버: ${GREEN}$SSH_USER@$SERVER_IP${NC}"
echo -e "SSH키: ${GREEN}$SSH_KEY${NC}"
echo ""

# SSH 키 권한 설정
chmod 400 "$SSH_KEY"

# 프로젝트 루트 경로
PROJECT_ROOT="/home/ybr/stock_search"
REMOTE_PATH="~/stock_search"

# 업로드할 파일/폴더 목록
UPLOAD_ITEMS=(
    "web"
    "services"
    "models"
    "screener"
    "utils"
    "commands"
    "main.py"
    "deploy"
)

echo "1. 원격 디렉토리 생성..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "mkdir -p ~/stock_search"

echo ""
echo "2. 파일 업로드 중..."
for item in "${UPLOAD_ITEMS[@]}"; do
    if [ -e "$PROJECT_ROOT/$item" ]; then
        echo -e "  - $item"
        scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -r "$PROJECT_ROOT/$item" "$SSH_USER@$SERVER_IP:$REMOTE_PATH/" 2>/dev/null
    fi
done

echo ""
echo -e "${GREEN}[✓] 업로드 완료!${NC}"
echo ""
echo "============================================"
echo "  다음 단계: 서버에서 설정 스크립트 실행"
echo "============================================"
echo ""
echo "서버 접속:"
echo -e "  ${YELLOW}ssh -i $SSH_KEY $SSH_USER@$SERVER_IP${NC}"
echo ""
echo "설정 스크립트 실행:"
echo -e "  ${YELLOW}cd ~/stock_search && bash deploy/setup-oracle.sh${NC}"
echo ""
