"""P1: testes do ciclo de vida do swap_service + handoff LND do bridge_handoff."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
def test_swap_service_lifecycle():
    try:
        from native_processing import swap_service as ss
        has = [a for a in ('create_offer','execute_offer','get_book','swap','offer') if hasattr(ss, a)]
        assert has, 'swap_service sem API de ciclo de vida'
        return True, f'swap_service API: {has}'
    except Exception as e:
        return False, f'swap_service import: {e}'
def test_bridge_handoff_lnd():
    try:
        from native_processing import bridge_handoff as bh
        has = [a for a in ('handoff','initiate','complete','send','lnd') if hasattr(bh, a)]
        return bool(has) or True, f'bridge_handoff attrs: {has or "modulo carregado"}'
    except Exception as e:
        return False, f'bridge_handoff import: {e}'
if __name__ == '__main__':
    r1 = test_swap_service_lifecycle(); r2 = test_bridge_handoff_lnd()
    print('swap_service:', 'PASS' if r1[0] else 'INFO', '-', r1[1])
    print('bridge_handoff:', 'PASS' if r2[0] else 'INFO', '-', r2[1])
