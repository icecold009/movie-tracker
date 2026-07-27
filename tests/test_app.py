def test_app_imports_and_registers_routes(app):
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert {"/", "/healthz", "/login", "/logout", "/add"}.issubset(routes)


def test_healthz_does_not_query_database(app):
    response = app.test_client().get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
