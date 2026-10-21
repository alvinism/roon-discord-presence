import pytest

from roon_discord_presence import DEFAULT_DISCORD_CLIENT_ID, wizard
from roon_discord_presence.config import Config, load


def roundtrip(tmp_path, cfg):
    p = tmp_path / "config.toml"
    p.write_text(wizard.render(cfg))
    return load(p), p.read_text()


def test_render_defaults_is_minimal(tmp_path):
    cfg, text = roundtrip(tmp_path, Config())
    assert cfg == Config()
    assert "[roon]" not in text and 'provider = "none"' in text


def test_render_s3_roundtrip(tmp_path):
    cfg = Config()
    cfg.roon.host = "192.168.1.10"
    cfg.roon.zones = ["Desk", "Living \"Room\""]
    cfg.covers.provider = "s3"
    s3 = cfg.covers.s3
    s3.endpoint, s3.bucket, s3.access_key_id = "https://acct.r2.cloudflarestorage.com", "b", "AK"
    s3.secret_access_key, s3.public_base_url = "keychain:x/y", "https://covers.example.com"
    loaded, text = roundtrip(tmp_path, cfg)
    assert loaded == cfg
    assert 'region = ' not in text  # defaults omitted


def answers(monkeypatch, *values):
    it = iter(values)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(it))


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(wizard.paths, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setattr(wizard.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(wizard, "roon_reachable", lambda host, port: True)
    monkeypatch.setattr(wizard.service, "ephemeral_install_warning", lambda: None)
    return tmp_path


def test_setup_without_covers_and_without_starting(isolated, monkeypatch):
    answers(monkeypatch,
            "", "",        # roon host, port: keep defaults
            "",            # discord app id: default
            "1",           # covers: none
            "n")           # don't start the service
    assert wizard.run() == 0
    cfg = load(isolated / "config.toml")
    assert cfg.roon.host == "127.0.0.1"
    assert cfg.discord.client_id == DEFAULT_DISCORD_CLIENT_ID
    assert cfg.covers.provider == "none"


def test_setup_command_provider_and_backup(isolated, monkeypatch):
    (isolated / "config.toml").write_text('[roon]\nhost = "10.0.0.2"\n')
    answers(monkeypatch, "", "", "123", "3", "/usr/local/bin/up.sh --flag", "n")
    assert wizard.run() == 0
    cfg = load(isolated / "config.toml")
    assert cfg.roon.host == "10.0.0.2"  # existing value offered as default
    assert cfg.discord.client_id == "123"
    assert cfg.covers.command.command == ["/usr/local/bin/up.sh", "--flag"]
    assert (isolated / "config.toml.bak").read_text().startswith("[roon]")


def test_setup_cancel(isolated, monkeypatch):
    def interrupt(_prompt=""):
        raise KeyboardInterrupt
    monkeypatch.setattr("builtins.input", interrupt)
    assert wizard.run() == 130
    assert not (isolated / "config.toml").exists()
