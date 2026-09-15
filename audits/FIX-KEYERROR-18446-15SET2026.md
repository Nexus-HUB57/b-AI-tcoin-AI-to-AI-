# Fix: KeyError: 0 em mylink_service.py (causa-raiz do 502 intermitente)
Handler do_GET agora aceita tupla (payload,status) ou dict direto.
Validado localmente (18446) e publicamente (mybait.org) em 15/09/2026.
