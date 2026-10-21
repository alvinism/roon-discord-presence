import pytest

from roon_discord_presence import moo


def test_roundtrip_with_unicode_body():
    body = {"title": "雨宿りの憧憬", "n": 1}
    data = moo.encode("REQUEST", "com.roonlabs.registry:1/register", 7, body)
    # Content-Length counts bytes, not characters
    assert b"Content-Length: %d\n" % len(data.partition(b"\n\n")[2]) in data
    assert moo.decode(data) == moo.Message("REQUEST", "com.roonlabs.registry:1/register", 7, body)


def test_without_body():
    data = moo.encode("COMPLETE", "Success", 3)
    assert data == b"MOO/1 COMPLETE Success\nRequest-Id: 3\n\n"
    assert moo.decode(data) == moo.Message("COMPLETE", "Success", 3, None)


def test_server_request_as_text():
    msg = moo.decode("MOO/1 REQUEST com.roonlabs.ping:1/ping\nRequest-Id: 12\n\n")
    assert (msg.verb, msg.name, msg.request_id) == ("REQUEST", "com.roonlabs.ping:1/ping", 12)


@pytest.mark.parametrize("bad", [b"HTTP/1.1 200 OK\n\n", b"MOO/1 COMPLETE Success\n\n"])
def test_rejects_malformed(bad):
    with pytest.raises(moo.MooError):
        moo.decode(bad)
