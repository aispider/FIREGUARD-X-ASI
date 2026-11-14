from app.agents.orchestrator import run_council
from app.schemas import ScenarioIn
from app.security.attack_suite import run_suite
from app.security.policy import PermissionDenied, ToolBroker, check
from app.services import mission


def test_attack_suite_blocks_everything(db):
    res = run_suite(db)
    assert res.blocked == res.total >= 9, [r.name for r in res.results if not r.blocked]


def test_agents_cannot_execute_or_admin():
    for a in ("scientist", "data", "fire", "safety", "red", "guardian", "commander"):
        assert not check(a, "execute:command").allowed and not check(a, "admin:users").allowed
    assert not check("red", "write:risk").allowed
    try:
        ToolBroker().call("fire", "execute:command", lambda: None)
        raise AssertionError("should have been denied")
    except PermissionDenied:
        pass


def test_tamper_quarantines_and_restore_recovers(db):
    base = run_council(db, ScenarioIn())
    assert base.integrity.ok
    assert mission.demo_tamper(db, "DEMO-oxygen", "t")
    after = run_council(db, ScenarioIn())
    assert not after.integrity.ok and "DEMO-oxygen" in after.integrity.quarantined
    assert after.trust.score < base.trust.score
    assert not any(e.provenance.document_id == "DEMO-oxygen" for e in after.evidence if e.status == "used")
    assert mission.demo_restore(db, "DEMO-oxygen", "t")
    assert run_council(db, ScenarioIn()).integrity.ok


def test_injected_chunk_is_excluded_and_cannot_lower_risk(db):
    base = run_council(db, ScenarioIn(oxygen_percent=24))
    mission.demo_inject(db, "t")
    atk = run_council(db, ScenarioIn(oxygen_percent=24))
    bad = [e for e in atk.evidence if e.chunk_id.startswith("DEMO-attack")]
    assert bad and bad[0].status == "excluded_injection" and "LOW risk" not in bad[0].text
    assert atk.risk.score == base.risk.score and atk.security_flags["injection_detected"]
    mission.demo_clear(db, "t")
    assert not mission.demo_state(db)[0]


def test_admin_only_actions_blocked_for_viewer(client, auth):
    h = auth("viewer")
    assert client.post("/api/security/demo/tamper", json={"doc_key": "DEMO-oxygen"}, headers=h).status_code == 403
    assert client.post("/api/ingest/run", json={}, headers=h).status_code == 403


def test_security_demo_can_be_disabled(client, auth, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("ENABLE_SECURITY_DEMO", "false")
    get_settings.cache_clear()
    try:
        assert client.post("/api/security/demo/inject", headers=auth("admin")).status_code == 403
    finally:
        monkeypatch.delenv("ENABLE_SECURITY_DEMO")
        get_settings.cache_clear()


def test_production_refuses_default_secrets(monkeypatch):
    import pytest

    from app.config import Settings
    with pytest.raises(RuntimeError):
        Settings(app_env="production").assert_production_safe()


def test_ntrs_client_blocks_non_nasa_hosts():
    from app.evidence.ntrs import host_allowed
    assert host_allowed("https://ntrs.nasa.gov/api/citations/1")
    assert not host_allowed("http://ntrs.nasa.gov/x") and not host_allowed("https://evil.example.com/x")
    assert not host_allowed("https://nasa.gov.evil.com/x")
