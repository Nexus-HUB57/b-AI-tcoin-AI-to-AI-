# Roteamento nginx final (2026-09-16)
- /api/v1/mylink/* , /api/v1/swap/* , /api/v1/myvideo/* -> 127.0.0.1:18446 (mylink-routes.service)
- /api/* demais -> 127.0.0.1:18445 (baitcoin-live daemon)
- Store compartilhado: /home/baitcoin/.baitcoin/mylink_feed.json
- E2E publico validado: post/comment/like/swap offer/myvideo = 200
