"""
scripts/smoke_test.py
End-to-end QA Smoke Test for FactoryMind AI.
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import AsyncClient, ASGITransport
from backend.app.main import app


async def run_smoke_test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        # 1. Health
        h = await client.get('/health')
        assert h.status_code == 200, f'Health failed: {h.text}'
        print('[PASS] Health check passed')

        # 2. Datasets
        ds = await client.get('/api/v1/datasets/', headers={'X-User-Role': 'ADMIN'})
        assert ds.status_code == 200, f'Datasets failed: {ds.text}'
        data = ds.json()
        print(f'[PASS] Datasets: {len(data)} registered')

        # 3. Machines
        m = await client.get('/api/v1/machines', headers={'X-User-Role': 'ADMIN'})
        assert m.status_code == 200, f'Machines failed: {m.text}'
        machines = m.json().get('machines', [])
        print(f'[PASS] Machines: {len(machines)} machines found')

        # 4. Predictions & RUL
        p = await client.get('/api/v1/predictions/1/latest', headers={'X-User-Role': 'ADMIN'})
        assert p.status_code == 200, f'Predictions failed: {p.text}'
        pred = p.json()
        print(f'[PASS] Predictions Unit #1: RUL={pred.get("rul_estimate")} cycles, Health Index={pred.get("health_index")}%')

        # 5. Work orders (Operator creates, Viewer blocked)
        wo_create = await client.post('/api/v1/work-orders', json={
            'machine_id': 1,
            'title': 'QA Test Inspection',
            'recommended_action': 'Inspect and replace turbine seal',
            'description': 'Automated QA test work order',
            'priority': 'MEDIUM',
            'assigned_to': 'Lead Maintenance Engineer'
        }, headers={'X-User-Role': 'OPERATOR'})
        assert wo_create.status_code in (200, 201), f'Operator create WO failed: {wo_create.text}'
        wo_id = wo_create.json()['id']
        print(f'[PASS] Operator created Work Order #{wo_id}')

        # Viewer blocked from mutating (403 Forbidden)
        wo_blocked = await client.post('/api/v1/work-orders', json={
            'machine_id': 1,
            'title': 'Viewer Attempt',
            'recommended_action': 'Unauthorized repair',
            'priority': 'LOW'
        }, headers={'X-User-Role': 'VIEWER'})
        assert wo_blocked.status_code == 403, f'Viewer was not blocked: {wo_blocked.status_code}'
        print('[PASS] Viewer mutation correctly blocked with 403 Forbidden')

        # 6. Fleet Intelligence
        fleet = await client.get('/api/v1/fleet/summary', headers={'X-User-Role': 'ADMIN'})
        assert fleet.status_code == 200, f'Fleet summary failed: {fleet.text}'
        print(f'[PASS] Fleet Summary: Total Machines={fleet.json().get("total_machines")}')

        # 7. Continuous Learning
        learn = await client.get('/api/v1/learning/overview', headers={'X-User-Role': 'ADMIN'})
        assert learn.status_code == 200, f'Learning failed: {learn.text}'
        print('[PASS] Continuous Learning overview verified')

        # 8. Diagnostics
        diag = await client.post('/api/v1/diagnostics/explain', json={'machine_id': 1, 'cycle': 50}, headers={'X-User-Role': 'ADMIN'})
        assert diag.status_code == 200, f'Diagnostics failed: {diag.text}'
        diag_data = diag.json()
        print(f'[PASS] Diagnostics: Summary="{diag_data.get("summary")[:40]}...", Source={diag_data.get("source")}')

        # 9. Security Audit Logs
        sec = await client.get('/api/v1/auth/security-audit-logs', headers={'X-User-Role': 'ADMIN'})
        assert sec.status_code == 200, f'Security logs failed: {sec.text}'
        print(f'[PASS] Security Audit Logs: {len(sec.json().get("logs", []))} events recorded')


if __name__ == '__main__':
    asyncio.run(run_smoke_test())
