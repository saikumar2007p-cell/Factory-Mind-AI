"""
backend/app/services/learning_signals.py

Stage 10 Verified Learning Signals Service.
Extracts empirical, evidence-backed observations from verified maintenance outcomes and operational histories.
Strictly observational — does NOT modify machine learning models automatically.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.work_order import WorkOrder
from backend.app.models.machine import Machine
from backend.app.models.alert import Alert
from backend.app.services.storage_service import StorageService
from backend.app.services.maintenance_effectiveness import MaintenanceEffectivenessService


class LearningSignalsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.storage = StorageService(session)
        self.effectiveness_service = MaintenanceEffectivenessService(session)

    async def get_learning_signals(self) -> List[Dict[str, Any]]:
        """
        Derives evidence-based learning signals from verified maintenance records.
        """
        all_wos = await self.storage.list_work_orders()
        machines = await self.storage.get_all_machines()
        machine_map = {m.id: m for m in machines}

        verified_wos = [w for w in all_wos if w.status == "VERIFIED"]
        completed_unverified = [w for w in all_wos if w.status == "VERIFICATION_REQUIRED"]

        signals = []
        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Action Effectiveness Learning Signals
        action_outcomes: Dict[str, Dict[str, Any]] = {}
        for w in verified_wos:
            act = w.recommended_action or "Inspection"
            if act not in action_outcomes:
                action_outcomes[act] = {
                    "resolved": 0,
                    "not_resolved": 0,
                    "subsystems": set(),
                    "wo_ids": []
                }
            v_stat = (w.verification_status or "").upper()
            action_outcomes[act]["wo_ids"].append(w.id)
            if w.affected_subsystem:
                action_outcomes[act]["subsystems"].add(w.affected_subsystem)
            if v_stat == "RESOLVED":
                action_outcomes[act]["resolved"] += 1
            elif v_stat in ["NOT_RESOLVED", "PARTIALLY_RESOLVED"]:
                action_outcomes[act]["not_resolved"] += 1

        for act, data in action_outcomes.items():
            tot = data["resolved"] + data["not_resolved"]
            if tot >= 1:
                conf = "HIGH EVIDENCE" if tot >= 3 else ("MODERATE EVIDENCE" if tot >= 2 else "LOW EVIDENCE")
                if data["resolved"] > data["not_resolved"]:
                    sig_id = f"SIG-ACT-RES-{len(signals) + 1:03d}"
                    subs_str = ", ".join(data["subsystems"]) or "Turbofan Core"
                    signals.append({
                        "signal_id": sig_id,
                        "signal_type": "ACTION_EFFECTIVENESS",
                        "affected_entity_type": "ACTION",
                        "entity_id": None,
                        "entity_name": act,
                        "subsystem": subs_str,
                        "evidence_count": tot,
                        "source_records": {"work_orders": data["wo_ids"]},
                        "confidence_level": conf,
                        "observation_title": f"Verified Success: {act}",
                        "explanation": f"Maintenance action '{act}' successfully resolved conditions in {data['resolved']} of {tot} verified maintenance procedures on ({subs_str}).",
                        "generated_at": now_str
                    })
                elif data["not_resolved"] > 0:
                    sig_id = f"SIG-ACT-UNRES-{len(signals) + 1:03d}"
                    subs_str = ", ".join(data["subsystems"]) or "Turbofan Core"
                    signals.append({
                        "signal_id": sig_id,
                        "signal_type": "ACTION_INEFFECTIVENESS",
                        "affected_entity_type": "ACTION",
                        "entity_id": None,
                        "entity_name": act,
                        "subsystem": subs_str,
                        "evidence_count": tot,
                        "source_records": {"work_orders": data["wo_ids"]},
                        "confidence_level": conf,
                        "observation_title": f"Intervention Caution: {act}",
                        "explanation": f"Maintenance action '{act}' did not fully resolve defect in {data['not_resolved']} cases. Secondary engineering review recommended.",
                        "generated_at": now_str
                    })

        # 2. Machine-Specific Repeat Issue Signals
        machine_wos: Dict[int, List[WorkOrder]] = {}
        for w in all_wos:
            if w.machine_id not in machine_wos:
                machine_wos[w.machine_id] = []
            machine_wos[w.machine_id].append(w)

        for m_id, w_list in machine_wos.items():
            if len(w_list) >= 2:
                m = machine_map.get(m_id)
                m_name = m.name if m else f"Unit #{m_id}"
                u_num = m.unit_number if m else m_id
                sub_list = list(set(w.affected_subsystem for w in w_list if w.affected_subsystem))
                subs_str = ", ".join(sub_list) or "Turbofan Core"
                sig_id = f"SIG-MACH-REC-{len(signals) + 1:03d}"
                conf = "HIGH EVIDENCE" if len(w_list) >= 3 else "MODERATE EVIDENCE"
                signals.append({
                    "signal_id": sig_id,
                    "signal_type": "RECURRING_MACHINE_DEGRADATION",
                    "affected_entity_type": "MACHINE",
                    "entity_id": m_id,
                    "entity_name": f"{m_name} (Unit #{u_num})",
                    "subsystem": subs_str,
                    "evidence_count": len(w_list),
                    "source_records": {"work_orders": [w.id for w in w_list]},
                    "confidence_level": conf,
                    "observation_title": f"Repeat Maintenance Interventions on Unit #{u_num}",
                    "explanation": f"Machine has required {len(w_list)} independent work orders targeting {subs_str}. Suggests underlying fatigue or recurring stress factor.",
                    "generated_at": now_str
                })

        # 3. Subsystem Fleet Vulnerability Signals
        subsystem_counts: Dict[str, List[int]] = {}
        for w in all_wos:
            sub = w.affected_subsystem or "Turbofan Core"
            if sub not in subsystem_counts:
                subsystem_counts[sub] = []
            subsystem_counts[sub].append(w.id)

        for sub, w_ids in subsystem_counts.items():
            if len(w_ids) >= 5:
                sig_id = f"SIG-SUB-FLEET-{len(signals) + 1:03d}"
                signals.append({
                    "signal_id": sig_id,
                    "signal_type": "SUBSYSTEM_FLEET_CONCENTRATION",
                    "affected_entity_type": "SUBSYSTEM",
                    "entity_id": None,
                    "entity_name": sub,
                    "subsystem": sub,
                    "evidence_count": len(w_ids),
                    "source_records": {"work_orders": w_ids},
                    "confidence_level": "HIGH EVIDENCE",
                    "observation_title": f"Fleet-Wide Defect Concentration in {sub}",
                    "explanation": f"{sub} is the most frequent target of maintenance work orders ({len(w_ids)} total orders plant-wide).",
                    "generated_at": now_str
                })

        # 4. Post-Maintenance Verification Quality Signal
        if len(completed_unverified) >= 1:
            sig_id = f"SIG-VERIF-BACKLOG-{len(signals) + 1:03d}"
            signals.append({
                "signal_id": sig_id,
                "signal_type": "VERIFICATION_QUALITY",
                "affected_entity_type": "FLEET",
                "entity_id": None,
                "entity_name": "Plant Maintenance Operations",
                "subsystem": "All Subsystems",
                "evidence_count": len(completed_unverified),
                "source_records": {"work_orders": [w.id for w in completed_unverified]},
                "confidence_level": "HIGH EVIDENCE" if len(completed_unverified) >= 3 else "MODERATE EVIDENCE",
                "observation_title": f"Unverified Maintenance Backlog ({len(completed_unverified)} units)",
                "explanation": f"{len(completed_unverified)} work orders are completed but awaiting post-run sensor verification.",
                "generated_at": now_str
            })

        return signals
