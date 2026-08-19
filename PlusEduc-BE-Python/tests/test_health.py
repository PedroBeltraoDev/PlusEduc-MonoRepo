def test_health_check_is_exposed(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["service"] == "PlusEduc API"
    assert payload["database"] == "degraded"
    assert "timestamp" in payload


def test_openapi_contains_current_scope_routes(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = set(response.json()["paths"])
    assert "/api/activities" in paths
    assert "/api/activities/{activity_id}" in paths
    assert "/api/activities/classroom/{classroom_id}" in paths
    assert "/api/activities/student/{student_id}" in paths
    assert "/api/activities/teacher/{teacher_id}" in paths
    assert "/api/student-portal/activities/{activity_id}/submissions" in paths
    assert "/api/grades" in paths
    assert "/api/students/{student_id}/performance" in paths
    assert "/api/students/{student_id}/attendance" in paths
    assert "/api/student-portal/me" in paths
    assert "/api/student-portal/classroom" in paths
    assert "/api/student-portal/classmates" in paths
    assert "/api/student-portal/teachers" in paths
    assert "/api/student-portal/activities" in paths
    assert "/api/student-portal/activities/{activity_id}" in paths
    assert "/api/student-portal/activities/{activity_id}/submissions" in paths
    assert "/api/student-portal/activities/{activity_id}/export-pdf" in paths
    assert "/api/student-portal/grades" in paths
    assert "/api/activities/generate" in paths
    assert "/api/activities/{activity_id}/export-pdf" in paths
