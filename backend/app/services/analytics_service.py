from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.db import models
from typing import List, Dict, Any
import datetime
import calendar

class AnalyticsService:
    def get_monthly_stroke_trends(self, db: Session, patient_uid: str, year: int = None) -> List[Dict[str, Any]]:
        """
        Aggregates stroke events and average risk markers by month.
        """
        if not year:
            year = datetime.datetime.now().year

        # 1. Fetch Stroke Events per Month
        stroke_events = db.query(
            extract('month', models.MedicalEvent.event_date).label('month'),
            func.count(models.MedicalEvent.id).label('count')
        ).filter(
            models.MedicalEvent.patient_uid == patient_uid,
            models.MedicalEvent.event_type == 'stroke_event',
            extract('year', models.MedicalEvent.event_date) == year
        ).group_by('month').all()

        stroke_map = {int(m): c for m, c in stroke_events}

        # 2. Fetch Average Risk Markers (BP, Glucose) per Month
        # We'll use LabResult for this
        lab_trends = db.query(
            extract('month', models.LabResult.result_date).label('month'),
            models.LabResult.test_name,
            func.avg(models.LabResult.value).label('avg_value')
        ).filter(
            models.LabResult.patient_uid == patient_uid,
            extract('year', models.LabResult.result_date) == year,
            models.LabResult.test_name.in_(['systolic_bp', 'glucose', 'cholesterol'])
        ).group_by('month', models.LabResult.test_name).all()

        lab_map = {}
        for month, test, avg in lab_trends:
            m = int(month)
            if m not in lab_map:
                lab_map[m] = {}
            lab_map[m][test] = round(float(avg), 2)

        # 3. Combine into final list
        final_data = []
        for i in range(1, 13):
            month_name = calendar.month_abbr[i]
            final_data.append({
                "month": month_name,
                "stroke_events": stroke_map.get(i, 0),
                "avg_systolic_bp": lab_map.get(i, {}).get('systolic_bp', 0),
                "avg_glucose": lab_map.get(i, {}).get('glucose', 0),
                "avg_cholesterol": lab_map.get(i, {}).get('cholesterol', 0),
            })

        return final_data

    def get_patient_benchmarks(self, db: Session, patient_uid: str) -> Dict[str, Any]:
        """
        Compares the latest patient metrics against clinical benchmarks.
        """
        # Get latest labs
        from sqlalchemy import desc
        latest_labs = db.query(models.LabResult).filter_by(patient_uid=patient_uid).order_by(desc(models.LabResult.result_date)).all()
        
        # Deduplicate to get the most recent for each test
        patient_metrics = {}
        for lab in latest_labs:
            if lab.test_name not in patient_metrics:
                patient_metrics[lab.test_name] = float(lab.value) if lab.value.replace('.','',1).isdigit() else 0

        # Standard Benchmarks
        benchmarks = {
            "systolic_bp": {"normal": 120, "high": 140},
            "glucose": {"normal": 100, "high": 126},
            "cholesterol": {"normal": 200, "high": 240},
            "bmi": {"normal": 24.9, "high": 30.0}
        }

        comparison = []
        for metric, bounds in benchmarks.items():
            value = patient_metrics.get(metric, 0)
            comparison.append({
                "metric": metric.replace('_', ' ').title(),
                "patient_value": value,
                "normal_range": bounds["normal"],
                "high_risk_range": bounds["high"],
                "status": "High Risk" if value >= bounds["high"] else "Moderate" if value >= bounds["normal"] else "Normal"
            })

        return comparison

analytics_service = AnalyticsService()
