#!/bin/bash
# ngrok URL 확인 스크립트

URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -oP 'https://[^"]*ngrok[^"]*')

if [ -n "$URL" ]; then
    echo "============================================"
    echo "  현재 ngrok 주소"
    echo "============================================"
    echo ""
    echo "  $URL"
    echo ""
    echo "============================================"
    echo "  이 주소를 핸드폰 앱에 입력하세요"
    echo "============================================"
else
    echo "ngrok이 실행 중이 아닙니다."
    echo "실행: systemctl --user start ngrok"
fi
