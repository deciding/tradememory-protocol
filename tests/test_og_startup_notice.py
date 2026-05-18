from types import SimpleNamespace

from click.testing import CliRunner


def test_doctor_prints_zerog_notice(monkeypatch):
    from tradememory import cli
    from tradememory.onboarding import doctor as doctor_module

    called = {"notice": False}

    def fake_notice(logger=None):
        called["notice"] = True
        print("0G startup notice")
        return SimpleNamespace(
            enabled=False, reason="missing_env", missing=["ZEROG_TESTNET_RPC_URL"]
        )

    monkeypatch.setattr(cli, "print_zerog_startup_notice", fake_notice)
    monkeypatch.setattr(doctor_module, "run_doctor", lambda full=False: {"ok": True})
    monkeypatch.setattr(doctor_module, "print_results", lambda results: print("doctor ok"))

    result = CliRunner().invoke(cli.cli, ["doctor"])

    assert result.exit_code == 0
    assert called["notice"] is True
    assert "0G startup notice" in result.output
    assert "doctor ok" in result.output


def test_server_main_prints_zerog_notice(monkeypatch, capsys):
    from tradememory import server

    called = {"notice": False, "run": False}

    def fake_notice(logger=None):
        called["notice"] = True
        print("0G startup notice")
        return SimpleNamespace(enabled=True, reason="configured", missing=[])

    def fake_run(app, host, port):
        called["run"] = True
        assert app is server.app
        assert host == "127.0.0.1"
        assert port == 8000

    monkeypatch.setattr(server, "print_zerog_startup_notice", fake_notice)
    monkeypatch.setitem(__import__("sys").modules, "uvicorn", SimpleNamespace(run=fake_run))

    server.main()

    out = capsys.readouterr().out
    assert called["notice"] is True
    assert called["run"] is True
    assert "0G startup notice" in out
