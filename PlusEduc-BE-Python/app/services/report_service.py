from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.repositories.activity_repository import ActivityRepository
from app.repositories.activity_submission_repository import ActivitySubmissionRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.report import (
    AtRiskStudent,
    DashboardKpis,
    DashboardResponse,
    DistributionBucket,
    MonthlyAverage,
    NamedAverage,
    ParticipationTotals,
    ReportCatalogItem,
    ReportColumn,
    ReportResponse,
    ReportSummaryItem,
)
from app.services.activity_submission_service import ActivitySubmissionService
from app.services.audit_service import ACTION_LABELS, BRT, ENTITY_LABELS, AuditService, day_end, day_start
from app.services.grade_service import _as_naive_utc
from app.services.student_analytics_service import StudentAnalyticsService

MIN_PASSING_GRADE = 6.0
MIN_ATTENDANCE = 75
MAX_ROWS = 5000

STATUS_OK, STATUS_ATTENTION, STATUS_EMPTY = "REGULAR", "ATENCAO", "SEM_LANCAMENTOS"
STATUS_LABELS = {STATUS_OK: "Regular", STATUS_ATTENTION: "Atenção", STATUS_EMPTY: "Sem lançamentos"}

CATALOG = [
    ReportCatalogItem(
        type="boletim",
        title="Boletim por turma",
        description="Média, frequência e situação de cada aluno, calculadas a partir das notas lançadas.",
        statusOptions=[{"value": STATUS_OK, "label": "Regular"}, {"value": STATUS_ATTENTION, "label": "Atenção"}, {"value": STATUS_EMPTY, "label": "Sem lançamentos"}],
    ),
    ReportCatalogItem(
        type="desempenho-disciplina",
        title="Desempenho por disciplina",
        description="Média, menor e maior nota e quantidade de lançamentos por turma e disciplina.",
    ),
    ReportCatalogItem(
        type="alunos-atencao",
        title="Alunos em atenção",
        description="Alunos com média abaixo de 6,0 ou frequência abaixo de 75%, com o motivo.",
    ),
    ReportCatalogItem(
        type="entregas-atividades",
        title="Entregas de atividades",
        description="Quantos alunos entregaram cada atividade, média de acertos e correções pendentes.",
        statusOptions=[{"value": "COMPLETA", "label": "Todas entregues"}, {"value": "PENDENTE", "label": "Com entregas pendentes"}],
    ),
    ReportCatalogItem(
        type="historico-operacoes",
        title="Histórico de operações",
        description="Registro das operações que alteraram dados no sistema (professor: as próprias; administrador: todas).",
        statusOptions=[{"value": "SUCESSO", "label": "Com sucesso"}, {"value": "FALHA", "label": "Com falha"}],
    ),
]
CATALOG_BY_TYPE = {item.type: item for item in CATALOG}


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().split())


@dataclass
class Filters:
    classroom_id: str | None = None
    subject: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    status: str | None = None
    entity: str | None = None
    action: str | None = None

    def as_text(self, classroom_name: str | None) -> dict[str, str]:
        out: dict[str, str] = {}
        if self.classroom_id:
            out["Turma"] = classroom_name or self.classroom_id
        if self.subject:
            out["Disciplina"] = self.subject
        if self.date_from:
            out["De"] = self.date_from.strftime("%d/%m/%Y")
        if self.date_to:
            out["Até"] = self.date_to.strftime("%d/%m/%Y")
        if self.status:
            out["Situação"] = STATUS_LABELS.get(self.status, self.status.title())
        if self.entity:
            out["Entidade"] = ENTITY_LABELS.get(self.entity, self.entity)
        if self.action:
            out["Ação"] = ACTION_LABELS.get(self.action, self.action)
        return out


def _fmt(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}".replace(".", ",")


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


class ReportService:
    def __init__(
        self,
        student_repository: StudentRepository,
        classroom_repository: ClassroomRepository,
        grade_repository: GradeRepository,
        activity_repository: ActivityRepository,
        submission_repository: ActivitySubmissionRepository,
        audit_repository: AuditRepository,
    ) -> None:
        self.students = student_repository
        self.classrooms = classroom_repository
        self.grades = grade_repository
        self.activities = activity_repository
        self.submissions = submission_repository
        self.audit = audit_repository

    # ------------------------------------------------------------------ dados
    def _load(self, filters: Filters) -> dict[str, Any]:
        classrooms = {str(c["_id"]): c for c in self.classrooms.find_active()}
        if filters.classroom_id and filters.classroom_id not in classrooms:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {filters.classroom_id}")
        students = {}
        for student in self.students.find_active():
            class_id = str(student.get("class_id") or student.get("classId") or "")
            if filters.classroom_id and class_id != filters.classroom_id:
                continue
            student["_class_id"] = class_id
            students[str(student["_id"])] = student
        grades = []
        for grade in self.grades.find_all():
            if filters.classroom_id and str(grade.get("classroomId", "")) != filters.classroom_id:
                continue
            if filters.subject and norm(grade.get("subject")) != norm(filters.subject):
                continue
            when = _as_naive_utc(grade.get("date"))
            if filters.date_from and (when is None or when < day_start(filters.date_from)):
                continue
            if filters.date_to and (when is None or when > day_end(filters.date_to)):
                continue
            grade["_when"] = when
            grades.append(grade)
        return {"classrooms": classrooms, "students": students, "grades": grades}

    @staticmethod
    def _value(grade: dict[str, Any]) -> float:
        return float(grade.get("grade", grade.get("gradeValue")) or 0)

    def _student_rows(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        by_student: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for grade in data["grades"]:
            by_student[str(grade.get("studentId", ""))].append(grade)
        rows = []
        for student_id, student in data["students"].items():
            items = by_student.get(student_id, [])
            values = [self._value(g) for g in items]
            total, attended, absences, rate = StudentAnalyticsService.attendance_counts(items)
            average = sum(values) / len(values) if values else None
            reasons = []
            if average is not None and average < MIN_PASSING_GRADE:
                reasons.append(f"média {_fmt(average)} abaixo de {_fmt(MIN_PASSING_GRADE)}")
            if total and rate < MIN_ATTENDANCE:
                reasons.append(f"frequência {rate}% abaixo de {MIN_ATTENDANCE}%")
            status = STATUS_EMPTY if not items else (STATUS_ATTENTION if reasons else STATUS_OK)
            classroom = data["classrooms"].get(student["_class_id"], {})
            rows.append({
                "studentId": student_id,
                "student": str(student.get("name", "")),
                "matricula": student.get("matricula") or "",
                "classroomId": student["_class_id"],
                "classroom": str(classroom.get("name", "Sem turma")),
                "average": _round(average),
                "attendanceRate": rate if total else None,
                "attended": attended,
                "absences": absences,
                "launches": len(items),
                "status": status,
                "reasons": reasons,
            })
        rows.sort(key=lambda r: (r["classroom"].lower(), r["student"].lower()))
        return rows

    def _activity_rows(self, data: dict[str, Any], filters: Filters) -> list[dict[str, Any]]:
        students_by_class: dict[str, int] = defaultdict(int)
        for student in self.students.find_active():
            students_by_class[str(student.get("class_id") or student.get("classId") or "")] += 1
        submissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for submission in self.submissions.find_all():
            submissions[str(submission.get("activity_id", submission.get("activityId", "")))].append(submission)
        rows = []
        for activity in self.activities.find_all():
            class_id = str(activity.get("classroom_id") or activity.get("classroomId") or "")
            if filters.classroom_id and class_id != filters.classroom_id:
                continue
            if filters.subject and norm(activity.get("subject")) != norm(filters.subject):
                continue
            created = _as_naive_utc(activity.get("created_at") or activity.get("createdAt"))
            if filters.date_from and (created is None or created < day_start(filters.date_from)):
                continue
            if filters.date_to and (created is None or created > day_end(filters.date_to)):
                continue
            target_student = activity.get("student_id") or activity.get("studentId")
            expected = 1 if target_student else students_by_class.get(class_id, 0)
            items = submissions.get(str(activity["_id"]), [])
            scores, pending = [], 0
            for item in items:
                stored = ActivitySubmissionService.parse_stored_result(item.get("content", "{}"))
                scores.append(stored.scorePercent)
                pending += 1 if stored.pendingCount > 0 else 0
            delivered = len(items)
            rows.append({
                "activityId": str(activity["_id"]),
                "title": str(activity.get("title", "")),
                "classroom": str((data["classrooms"].get(class_id) or {}).get("name", "Sem turma")),
                "subject": str(activity.get("subject", "")),
                "createdAt": created.date().isoformat() if created else None,
                "expected": expected,
                "delivered": delivered,
                "deliveryRate": round(delivered * 100 / expected) if expected else None,
                "averageScore": round(sum(scores) / len(scores)) if scores else None,
                "pendingCorrection": pending,
                "complete": bool(expected) and delivered >= expected,
            })
        rows.sort(key=lambda r: r["createdAt"] or "", reverse=True)
        return rows

    # -------------------------------------------------------------- dashboard
    def dashboard(self, principal: UserPrincipal, filters: Filters) -> DashboardResponse:
        data = self._load(filters)
        student_rows = self._student_rows(data)
        activity_rows = self._activity_rows(data, filters)
        grades = data["grades"]
        enrolled = {r["studentId"] for r in student_rows}
        grades = [g for g in grades if str(g.get("studentId", "")) in enrolled]
        values = [self._value(g) for g in grades]
        _, _, _, overall_rate = StudentAnalyticsService.attendance_counts(grades)
        recorded = any(g.get("attendance") is not None for g in grades)

        by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
        subject_names: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        by_month: dict[str, list[float]] = defaultdict(list)
        for g in grades:
            by_class[str(g.get("classroomId", ""))].append(g)
            key = norm(g.get("subject")) or "sem disciplina"
            by_subject[key].append(g)
            subject_names[key][str(g.get("subject") or "Sem disciplina")] += 1
            if g["_when"]:
                by_month[g["_when"].strftime("%Y-%m")].append(self._value(g))

        def named(items: list[dict[str, Any]], ident: str | None, name: str) -> NamedAverage:
            vals = [self._value(i) for i in items]
            _, _, _, rate = StudentAnalyticsService.attendance_counts(items)
            has_att = any(i.get("attendance") is not None for i in items)
            return NamedAverage(id=ident, name=name, average=round(sum(vals) / len(vals), 2), attendanceRate=rate if has_att else None, launches=len(vals))

        average_by_classroom = sorted(
            (named(items, cid, str((data["classrooms"].get(cid) or {}).get("name", "Sem turma"))) for cid, items in by_class.items()),
            key=lambda n: n.name.lower(),
        )
        average_by_subject = sorted(
            (named(items, None, max(subject_names[key].items(), key=lambda kv: (kv[1], any(ord(c) > 127 for c in kv[0])))[0]) for key, items in by_subject.items()),
            key=lambda n: -n.average,
        )
        buckets = [("0 a 2", 0, 2), ("2 a 4", 2, 4), ("4 a 6", 4, 6), ("6 a 8", 6, 8), ("8 a 10", 8, 10.01)]
        distribution = [DistributionBucket(range=label, count=sum(1 for v in values if lo <= v < hi)) for label, lo, hi in buckets]

        delivered = sum(r["delivered"] for r in activity_rows)
        expected = sum(r["expected"] for r in activity_rows)
        pending_total = max(expected - delivered, 0)
        at_risk_rows = [r for r in student_rows if r["status"] == STATUS_ATTENTION]
        at_risk_rows.sort(key=lambda r: (r["average"] if r["average"] is not None else 99))

        classrooms_count = 1 if filters.classroom_id else len(data["classrooms"])
        return DashboardResponse(
            generatedAt=datetime.now(timezone.utc),
            filters=filters.as_text((data["classrooms"].get(filters.classroom_id or "") or {}).get("name")),
            kpis=DashboardKpis(
                students=len(student_rows),
                classrooms=classrooms_count,
                activities=len(activity_rows),
                gradeLaunches=len(values),
                averageGrade=_round(sum(values) / len(values)) if values else None,
                attendanceRate=overall_rate if recorded else None,
                submissionRate=round(delivered * 100 / expected) if expected else None,
                studentsAtRisk=len(at_risk_rows),
            ),
            averageByClassroom=average_by_classroom,
            averageBySubject=average_by_subject,
            monthlyAverage=[MonthlyAverage(month=m, average=round(sum(v) / len(v), 2), launches=len(v)) for m, v in sorted(by_month.items())],
            distribution=distribution,
            participation=ParticipationTotals(delivered=delivered, pending=pending_total),
            atRisk=[
                AtRiskStudent(studentId=r["studentId"], studentName=r["student"], classroomName=r["classroom"], average=r["average"], attendanceRate=r["attendanceRate"], reasons=r["reasons"])
                for r in at_risk_rows[:10]
            ],
            recentOperations=AuditService(self.audit).recent(principal, 8),
        )

    # -------------------------------------------------------------- relatórios
    def report(self, report_type: str, principal: UserPrincipal, filters: Filters) -> ReportResponse:
        if report_type not in CATALOG_BY_TYPE:
            raise HTTPException(status_code=404, detail=f"Relatório não encontrado: {report_type}")
        meta = CATALOG_BY_TYPE[report_type]
        if report_type == "historico-operacoes":
            return self._history_report(meta, principal, filters)
        data = self._load(filters)
        classroom_name = (data["classrooms"].get(filters.classroom_id or "") or {}).get("name")
        builder = {
            "boletim": self._boletim,
            "desempenho-disciplina": self._subject_performance,
            "alunos-atencao": self._attention,
            "entregas-atividades": self._deliveries,
        }[report_type]
        columns, rows, summary = builder(data, filters)
        return ReportResponse(
            type=report_type,
            title=meta.title,
            description=meta.description,
            generatedAt=datetime.now(timezone.utc),
            filters=filters.as_text(classroom_name),
            columns=columns,
            rows=rows[:MAX_ROWS],
            summary=summary,
            total=len(rows),
        )

    def _boletim(self, data, filters):
        rows = self._student_rows(data)
        if filters.status:
            rows = [r for r in rows if r["status"] == filters.status]
        out = [{
            "classroom": r["classroom"], "student": r["student"], "matricula": r["matricula"],
            "average": r["average"], "attendanceRate": r["attendanceRate"], "launches": r["launches"],
            "status": STATUS_LABELS[r["status"]],
        } for r in rows]
        avgs = [r["average"] for r in rows if r["average"] is not None]
        columns = [
            ReportColumn(key="classroom", label="Turma"), ReportColumn(key="student", label="Aluno"),
            ReportColumn(key="matricula", label="Matrícula"), ReportColumn(key="average", label="Média", type="decimal"),
            ReportColumn(key="attendanceRate", label="Frequência", type="percent"),
            ReportColumn(key="launches", label="Lançamentos", type="number"), ReportColumn(key="status", label="Situação"),
        ]
        summary = [
            ReportSummaryItem(label="Alunos", value=str(len(rows))),
            ReportSummaryItem(label="Média geral", value=_fmt(sum(avgs) / len(avgs), 2) if avgs else "-"),
            ReportSummaryItem(label="Em atenção", value=str(sum(1 for r in rows if r["status"] == STATUS_ATTENTION))),
        ]
        return columns, out, summary

    def _subject_performance(self, data, filters):
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        names: dict[str, str] = {}
        for g in data["grades"]:
            cid = str(g.get("classroomId", ""))
            key = (cid, norm(g.get("subject")) or "sem disciplina")
            groups[key].append(g)
            names.setdefault(key[1], str(g.get("subject") or "Sem disciplina"))
        rows = []
        for (cid, key), items in groups.items():
            vals = [self._value(i) for i in items]
            rows.append({
                "classroom": str((data["classrooms"].get(cid) or {}).get("name", "Sem turma")),
                "subject": names[key], "average": round(sum(vals) / len(vals), 2), "min": min(vals), "max": max(vals),
                "launches": len(vals), "students": len({str(i.get("studentId")) for i in items}),
            })
        rows.sort(key=lambda r: (r["classroom"].lower(), r["subject"].lower()))
        columns = [
            ReportColumn(key="classroom", label="Turma"), ReportColumn(key="subject", label="Disciplina"),
            ReportColumn(key="average", label="Média", type="decimal"), ReportColumn(key="min", label="Menor nota", type="decimal"),
            ReportColumn(key="max", label="Maior nota", type="decimal"), ReportColumn(key="launches", label="Lançamentos", type="number"),
            ReportColumn(key="students", label="Alunos", type="number"),
        ]
        all_vals = [self._value(g) for g in data["grades"]]
        summary = [
            ReportSummaryItem(label="Combinações turma/disciplina", value=str(len(rows))),
            ReportSummaryItem(label="Lançamentos", value=str(len(all_vals))),
            ReportSummaryItem(label="Média geral", value=_fmt(sum(all_vals) / len(all_vals), 2) if all_vals else "-"),
        ]
        return columns, rows, summary

    def _attention(self, data, filters):
        rows = [r for r in self._student_rows(data) if r["status"] == STATUS_ATTENTION]
        rows.sort(key=lambda r: (r["average"] if r["average"] is not None else 99))
        out = [{
            "classroom": r["classroom"], "student": r["student"], "average": r["average"],
            "attendanceRate": r["attendanceRate"], "reason": "; ".join(r["reasons"]),
        } for r in rows]
        columns = [
            ReportColumn(key="classroom", label="Turma"), ReportColumn(key="student", label="Aluno"),
            ReportColumn(key="average", label="Média", type="decimal"), ReportColumn(key="attendanceRate", label="Frequência", type="percent"),
            ReportColumn(key="reason", label="Motivo"),
        ]
        return columns, out, [ReportSummaryItem(label="Alunos em atenção", value=str(len(out)))]

    def _deliveries(self, data, filters):
        rows = self._activity_rows(data, filters)
        if filters.status == "COMPLETA":
            rows = [r for r in rows if r["complete"]]
        elif filters.status == "PENDENTE":
            rows = [r for r in rows if not r["complete"]]
        out = [{
            "title": r["title"], "classroom": r["classroom"], "subject": r["subject"], "createdAt": r["createdAt"],
            "expected": r["expected"], "delivered": r["delivered"], "deliveryRate": r["deliveryRate"],
            "averageScore": r["averageScore"], "pendingCorrection": r["pendingCorrection"],
        } for r in rows]
        columns = [
            ReportColumn(key="title", label="Atividade"), ReportColumn(key="classroom", label="Turma"),
            ReportColumn(key="subject", label="Disciplina"), ReportColumn(key="createdAt", label="Criada em", type="date"),
            ReportColumn(key="expected", label="Alunos", type="number"), ReportColumn(key="delivered", label="Entregas", type="number"),
            ReportColumn(key="deliveryRate", label="% entrega", type="percent"), ReportColumn(key="averageScore", label="Acertos (média)", type="percent"),
            ReportColumn(key="pendingCorrection", label="Aguardando correção", type="number"),
        ]
        exp = sum(r["expected"] for r in rows)
        dev = sum(r["delivered"] for r in rows)
        summary = [
            ReportSummaryItem(label="Atividades", value=str(len(rows))),
            ReportSummaryItem(label="Entregas / esperadas", value=f"{dev} / {exp}"),
            ReportSummaryItem(label="Taxa de entrega", value=f"{round(dev * 100 / exp)}%" if exp else "-"),
        ]
        return columns, out, summary

    def _history_report(self, meta: ReportCatalogItem, principal: UserPrincipal, filters: Filters) -> ReportResponse:
        service = AuditService(self.audit)
        success = {"SUCESSO": True, "FALHA": False}.get(filters.status or "")
        query = service.build_query(principal, entity=filters.entity, action=filters.action, success=success, date_from=filters.date_from, date_to=filters.date_to)
        total = self.audit.count(query)
        items = self.audit.search(query, 0, MAX_ROWS)
        rows = []
        for item in items:
            entry = AuditService.to_response(item)
            rows.append({
                "timestamp": entry.timestamp.astimezone(BRT).strftime("%Y-%m-%d %H:%M:%S"),
                "actor": entry.actorEmail or "-", "action": entry.actionLabel, "entity": entry.entityLabel,
                "summary": entry.summary, "result": "Sucesso" if entry.success else f"Falha ({entry.status})",
            })
        columns = [
            ReportColumn(key="timestamp", label="Data e hora", type="datetime"), ReportColumn(key="actor", label="Usuário"),
            ReportColumn(key="action", label="Ação"), ReportColumn(key="entity", label="Entidade"),
            ReportColumn(key="summary", label="Descrição"), ReportColumn(key="result", label="Resultado"),
        ]
        failures = sum(1 for r in rows if r["result"] != "Sucesso")
        return ReportResponse(
            type=meta.type, title=meta.title, description=meta.description, generatedAt=datetime.now(timezone.utc),
            filters=filters.as_text(None), columns=columns, rows=rows, total=total,
            summary=[ReportSummaryItem(label="Operações", value=str(total)), ReportSummaryItem(label="Com falha (nesta lista)", value=str(failures))],
        )
