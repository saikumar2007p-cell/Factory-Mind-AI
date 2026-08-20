"""
backend/app/services/data_sufficiency.py

Data Sufficiency Heuristics Service for FactoryMind AI.

Replaces rigid time thresholds (≥2 weeks / ≥4 weeks / ≥3 months) with a
multi-dimensional evidence-based assessment of what a dataset can actually support.

Dimensions assessed:
  1. Duration          – calendar span of data
  2. Sample Density    – observations per unit time
  3. Signal Quality    – fraction of non-null, non-stale readings
  4. Variation         – distribution breadth (IQR, std) — static data is uninformative
  5. Failure Labels    – whether dataset contains degradation/failure examples
  6. Maintenance History – presence of known maintenance events as reference points
  7. Operating Conditions – coverage of different operating regimes
  8. Machine Evidence  – machine-specific context (age, MTBF, known intervals)

Final verdict uses weakest-link logic across required dimensions:
  SUFFICIENT_FOR_PROGNOSTICS – full RUL + anomaly
  SUFFICIENT_FOR_ANOMALY     – anomaly detection only
  SUFFICIENT_FOR_BASELINE    – normal behaviour characterisation only
  MARGINAL                   – some modelling possible with caveats
  INSUFFICIENT               – dataset cannot support any reliable model
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import math
import logging

logger = logging.getLogger("factorymind.data_sufficiency")


@dataclass
class DimensionResult:
    dimension: str
    score: float           # 0.0 – 1.0
    verdict: str           # PASS | WARN | FAIL
    value: Any             # The actual measured value
    threshold_description: str
    explanation: str


@dataclass
class DataSufficiencyReport:
    overall_verdict: str   # SUFFICIENT_FOR_PROGNOSTICS | SUFFICIENT_FOR_ANOMALY | SUFFICIENT_FOR_BASELINE | MARGINAL | INSUFFICIENT
    overall_score: float   # 0.0 – 1.0 (minimum across required dimensions)
    dimensions: List[DimensionResult] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class DataSufficiencyAssessor:
    """
    Evidence-based dataset capability assessor.
    Each dimension is scored independently; the final verdict is the weakest link.
    """

    def assess(
        self,
        duration_days: Optional[float] = None,
        sample_count: Optional[int] = None,
        samples_per_day: Optional[float] = None,
        missing_fraction: Optional[float] = None,    # 0.0 = no missing, 1.0 = all missing
        signal_variance: Optional[float] = None,     # mean coefficient of variation across channels
        has_failure_labels: bool = False,
        failure_event_count: int = 0,
        maintenance_event_count: int = 0,
        operating_condition_count: int = 1,          # distinct operating regimes
        machine_mtbf_days: Optional[float] = None,  # machine-specific MTBF if known
        notes: Optional[str] = None
    ) -> DataSufficiencyReport:
        """
        Runs all dimensional assessments and returns a DataSufficiencyReport.
        """
        results: List[DimensionResult] = []

        # --- 1. Duration ---
        results.append(self._assess_duration(duration_days, machine_mtbf_days))

        # --- 2. Sample Density ---
        results.append(self._assess_density(sample_count, samples_per_day, duration_days))

        # --- 3. Signal Quality ---
        results.append(self._assess_quality(missing_fraction))

        # --- 4. Signal Variation ---
        results.append(self._assess_variation(signal_variance))

        # --- 5. Failure Labels ---
        results.append(self._assess_failure_labels(has_failure_labels, failure_event_count))

        # --- 6. Maintenance History ---
        results.append(self._assess_maintenance_history(maintenance_event_count))

        # --- 7. Operating Condition Coverage ---
        results.append(self._assess_operating_conditions(operating_condition_count))

        # --- Overall verdict logic ---
        failure_result = next(r for r in results if r.dimension == "Failure Labels")
        quality_result = next(r for r in results if r.dimension == "Signal Quality")

        # Scores excluding failure labels (for unsupervised tasks like anomaly detection & baseline)
        unsupervised_scores = [r.score for r in results if r.dimension != "Failure Labels"]
        min_unsupervised = min(unsupervised_scores) if unsupervised_scores else 0.0
        all_min = min([r.score for r in results]) if results else 0.0
        mean_score = sum([r.score for r in results]) / len(results) if results else 0.0

        if quality_result.verdict == "FAIL":
            verdict = "INSUFFICIENT"
        elif all_min >= 0.70 and failure_result.verdict in ["PASS", "WARN"]:
            verdict = "SUFFICIENT_FOR_PROGNOSTICS"
        elif min_unsupervised >= 0.40:
            verdict = "SUFFICIENT_FOR_ANOMALY"
        elif min_unsupervised >= 0.20:
            verdict = "SUFFICIENT_FOR_BASELINE"
        elif min_unsupervised >= 0.10:
            verdict = "MARGINAL"
        else:
            verdict = "INSUFFICIENT"


        summary = self._build_summary(verdict, results)
        recommendations = self._build_recommendations(results, verdict)

        return DataSufficiencyReport(
            overall_verdict=verdict,
            overall_score=round(mean_score, 3),
            dimensions=results,
            summary=summary,
            recommendations=recommendations
        )

    # -------------------------------------------------------------------------
    # DIMENSION ASSESSORS
    # -------------------------------------------------------------------------

    def _assess_duration(
        self,
        duration_days: Optional[float],
        mtbf_days: Optional[float]
    ) -> DimensionResult:
        if duration_days is None:
            return DimensionResult(
                dimension="Duration",
                score=0.0,
                verdict="FAIL",
                value=None,
                threshold_description="Dataset duration unknown",
                explanation="Dataset duration could not be determined — cannot assess temporal coverage."
            )

        # If machine MTBF is known, require at least 50% MTBF coverage for prognostics
        if mtbf_days and mtbf_days > 0:
            required_days = mtbf_days * 0.5
            score = min(1.0, duration_days / required_days)
            threshold_desc = f"≥ 50% of machine MTBF ({mtbf_days:.0f} days → need ≥ {required_days:.0f} days)"
        else:
            # Generic heuristic: 14 days minimum for any useful baseline
            score = min(1.0, duration_days / 14.0)
            threshold_desc = "Dataset span assessed relative to minimum useful baseline (heuristic)"

        verdict = "PASS" if score >= 0.8 else ("WARN" if score >= 0.5 else "FAIL")
        return DimensionResult(
            dimension="Duration",
            score=round(score, 3),
            verdict=verdict,
            value=f"{duration_days:.1f} days",
            threshold_description=threshold_desc,
            explanation=f"Dataset spans {duration_days:.1f} days (score: {score:.2f})."
        )

    def _assess_density(
        self,
        sample_count: Optional[int],
        samples_per_day: Optional[float],
        duration_days: Optional[float]
    ) -> DimensionResult:
        if sample_count is None and samples_per_day is None:
            return DimensionResult(
                dimension="Sample Density",
                score=0.0,
                verdict="FAIL",
                value=None,
                threshold_description="Sample density unknown",
                explanation="Cannot determine sample density — row count or rate unavailable."
            )

        effective_spd = samples_per_day
        if effective_spd is None and sample_count and duration_days and duration_days > 0:
            effective_spd = sample_count / duration_days

        if effective_spd is None:
            score = 0.3
            verdict = "WARN"
            explanation = f"Sample count={sample_count}, but daily rate cannot be computed without duration."
        elif effective_spd >= 24:
            score = 1.0
            verdict = "PASS"
            explanation = f"Hourly or better sampling ({effective_spd:.1f}/day) — sufficient density."
        elif effective_spd >= 4:
            score = 0.75
            verdict = "PASS"
            explanation = f"Multiple daily samples ({effective_spd:.1f}/day) — adequate density."
        elif effective_spd >= 1:
            score = 0.5
            verdict = "WARN"
            explanation = f"Daily samples ({effective_spd:.1f}/day) — marginal density for pattern detection."
        else:
            score = 0.2
            verdict = "FAIL"
            explanation = f"Sub-daily sampling ({effective_spd:.1f}/day) — insufficient for reliable pattern detection."

        return DimensionResult(
            dimension="Sample Density",
            score=score,
            verdict=verdict,
            value=f"{effective_spd:.1f} samples/day" if effective_spd else f"{sample_count} total",
            threshold_description="Assessed against: ≥24/day=ideal, ≥4/day=adequate, ≥1/day=marginal",
            explanation=explanation
        )

    def _assess_quality(self, missing_fraction: Optional[float]) -> DimensionResult:
        if missing_fraction is None:
            return DimensionResult(
                dimension="Signal Quality",
                score=0.5,
                verdict="WARN",
                value=None,
                threshold_description="Missing/null fraction unknown",
                explanation="Data completeness could not be assessed. Proceeding with caution."
            )

        completeness = 1.0 - missing_fraction
        score = completeness
        verdict = "PASS" if completeness >= 0.95 else ("WARN" if completeness >= 0.80 else "FAIL")
        return DimensionResult(
            dimension="Signal Quality",
            score=round(score, 3),
            verdict=verdict,
            value=f"{completeness * 100:.1f}% complete",
            threshold_description="≥95% completeness=PASS, ≥80%=WARN, <80%=FAIL",
            explanation=f"{missing_fraction * 100:.1f}% of readings are missing or null."
        )

    def _assess_variation(self, signal_variance: Optional[float]) -> DimensionResult:
        if signal_variance is None:
            return DimensionResult(
                dimension="Signal Variation",
                score=0.5,
                verdict="WARN",
                value=None,
                threshold_description="Signal variation not computed",
                explanation="Could not assess signal variation. Static data would be uninformative for ML."
            )

        # Mean coefficient of variation (CV) > 0.01 means there's real variation
        if signal_variance >= 0.05:
            score = 1.0
            verdict = "PASS"
            explanation = f"Good signal variation (mean CV={signal_variance:.3f}) — informative for pattern learning."
        elif signal_variance >= 0.01:
            score = 0.6
            verdict = "WARN"
            explanation = f"Low but detectable signal variation (CV={signal_variance:.3f}) — limited degradation signal."
        else:
            score = 0.1
            verdict = "FAIL"
            explanation = f"Near-constant signals (CV={signal_variance:.4f}) — insufficient variation for ML pattern detection."

        return DimensionResult(
            dimension="Signal Variation",
            score=score,
            verdict=verdict,
            value=f"mean CV={signal_variance:.4f}",
            threshold_description="CV ≥0.05=good, ≥0.01=marginal, <0.01=insufficient",
            explanation=explanation
        )

    def _assess_failure_labels(
        self,
        has_failure_labels: bool,
        failure_event_count: int
    ) -> DimensionResult:
        if not has_failure_labels or failure_event_count == 0:
            score = 0.2
            verdict = "FAIL"
            explanation = (
                "No failure or degradation events found in dataset. "
                "Prognostic models require examples of degraded behaviour to learn from. "
                "Anomaly detection and baseline characterisation are still possible."
            )
        elif failure_event_count == 1:
            score = 0.5
            verdict = "WARN"
            explanation = f"One failure/degradation event found — marginal. More events improve prognostic reliability."
        elif failure_event_count >= 3:
            score = 1.0
            verdict = "PASS"
            explanation = f"{failure_event_count} failure/degradation events — sufficient for supervised prognostic learning."
        else:
            score = 0.75
            verdict = "PASS"
            explanation = f"{failure_event_count} failure/degradation events found — adequate for initial prognostic model."

        return DimensionResult(
            dimension="Failure Labels",
            score=score,
            verdict=verdict,
            value=f"{failure_event_count} events",
            threshold_description="≥3 events=PASS, 1-2=WARN, 0=FAIL (required for full RUL prognostics)",
            explanation=explanation
        )

    def _assess_maintenance_history(self, maintenance_event_count: int) -> DimensionResult:
        if maintenance_event_count == 0:
            score = 0.4
            verdict = "WARN"
            explanation = "No recorded maintenance events. Known maintenance points help calibrate model baselines."
        elif maintenance_event_count >= 3:
            score = 1.0
            verdict = "PASS"
            explanation = f"{maintenance_event_count} maintenance events provide reference points for baseline calibration."
        else:
            score = 0.7
            verdict = "PASS"
            explanation = f"{maintenance_event_count} maintenance event(s) available."

        return DimensionResult(
            dimension="Maintenance History",
            score=score,
            verdict=verdict,
            value=f"{maintenance_event_count} events",
            threshold_description="Maintenance events improve baseline calibration quality",
            explanation=explanation
        )

    def _assess_operating_conditions(self, condition_count: int) -> DimensionResult:
        if condition_count <= 0:
            condition_count = 1

        if condition_count >= 3:
            score = 1.0
            verdict = "PASS"
            explanation = f"{condition_count} distinct operating conditions — good regime coverage."
        elif condition_count == 2:
            score = 0.7
            verdict = "WARN"
            explanation = "2 operating conditions detected — partial regime coverage."
        else:
            score = 0.5
            verdict = "WARN"
            explanation = "Single operating condition detected — model may not generalise to different regimes."

        return DimensionResult(
            dimension="Operating Conditions",
            score=score,
            verdict=verdict,
            value=f"{condition_count} regime(s)",
            threshold_description="≥3 regimes=PASS, 2=WARN, 1=WARN",
            explanation=explanation
        )

    # -------------------------------------------------------------------------
    # SUMMARY + RECOMMENDATIONS
    # -------------------------------------------------------------------------

    def _build_summary(self, verdict: str, results: List[DimensionResult]) -> str:
        fails = [r.dimension for r in results if r.verdict == "FAIL"]
        warns = [r.dimension for r in results if r.verdict == "WARN"]

        if verdict == "SUFFICIENT_FOR_PROGNOSTICS":
            return "Dataset meets evidence requirements for full prognostic modelling (RUL + anomaly detection)."
        elif verdict == "SUFFICIENT_FOR_ANOMALY":
            summary = "Dataset supports anomaly detection. "
            if fails:
                summary += f"Prognostic RUL blocked by: {', '.join(fails)}."
            return summary
        elif verdict == "SUFFICIENT_FOR_BASELINE":
            return f"Dataset supports baseline characterisation only. Blocked on: {', '.join(fails or warns)}."
        elif verdict == "MARGINAL":
            return f"Marginal dataset — modelling possible with significant caveats. Weak dimensions: {', '.join(fails + warns)}."
        else:
            return f"Insufficient data — no reliable ML model can be trained. Issues: {', '.join(fails)}."

    def _build_recommendations(
        self,
        results: List[DimensionResult],
        verdict: str
    ) -> List[str]:
        recs = []
        for r in results:
            if r.verdict == "FAIL":
                if r.dimension == "Duration":
                    recs.append("Collect more historical data — insufficient temporal coverage.")
                elif r.dimension == "Sample Density":
                    recs.append("Increase sampling frequency or collect more observations.")
                elif r.dimension == "Signal Quality":
                    recs.append("Resolve data quality issues: missing values, sensor dropouts, or transmission errors.")
                elif r.dimension == "Signal Variation":
                    recs.append("Dataset appears to contain near-constant signals. Verify sensor connectivity and operating range coverage.")
                elif r.dimension == "Failure Labels":
                    recs.append("No failure events in dataset — collect data through degradation events or use transfer learning from similar equipment.")
            elif r.verdict == "WARN":
                if r.dimension == "Operating Conditions":
                    recs.append("Cover more operating conditions (load levels, speeds, temperatures) to improve model generalisability.")
                elif r.dimension == "Maintenance History":
                    recs.append("Record maintenance events with timestamps to improve model baseline calibration.")
                elif r.dimension == "Failure Labels":
                    recs.append("Additional failure/degradation events would improve prognostic accuracy.")

        if not recs and verdict == "SUFFICIENT_FOR_PROGNOSTICS":
            recs.append("Dataset meets all assessed requirements. Proceed with model training.")

        return recs
