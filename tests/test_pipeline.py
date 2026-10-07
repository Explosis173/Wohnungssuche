from datetime import datetime, timedelta, timezone

from wohnungssuche.collect import collect
from wohnungssuche.models import Listing, ListingStub
from wohnungssuche.notify import notify
from wohnungssuche.ntfy import NtfyClient, PushMessage, build_payload
from wohnungssuche.sources.base import Source
from wohnungssuche.store import Store

DASHBOARD = "https://example.github.io/Wohnungssuche/"
# 06:17 in Berlin (CEST) – the morning run
MORNING = datetime(2026, 10, 7, 4, 17, tzinfo=timezone.utc)
AFTERNOON = datetime(2026, 10, 7, 14, 17, tzinfo=timezone.utc)


class FakeSource(Source):
    name = "kleinanzeigen"

    def __init__(self, config, listings: list[Listing], fail: bool = False):
        super().__init__(http=None, config=config)
        self.listings = {l.id: l for l in listings}
        self.fail = fail
        self.fetched: list[str] = []

    def search(self):
        if self.fail:
            raise RuntimeError("blocked")
        return [ListingStub(id=l.id, url=l.url, title=l.title, price=l.rent_cold, area_m2=l.area_m2) for l in self.listings.values()]

    def fetch(self, stub):
        self.fetched.append(stub.id)
        return Listing.from_dict(self.listings[stub.id].to_dict())


class RecordingClient(NtfyClient):
    def __init__(self):
        super().__init__(topic="test")
        self.sent: list[PushMessage] = []

    def send(self, msg):
        self.sent.append(msg)


def test_collect_filters_scores_and_skips_known(config, make_listing, data_dir):
    store = Store(data_dir)
    good = make_listing(id="ka:1", rent_cold=450)
    too_expensive = make_listing(id="ka:2", rent_cold=450, rent_warm=690)
    source = FakeSource(config, [good, too_expensive])

    new = collect(store, [source], config, MORNING)
    assert [l.id for l in new] == ["ka:1"]
    assert store.listings["ka:1"].score > 0
    assert "ka:2" in store.state.rejected

    source.fetched.clear()
    assert collect(store, [source], config, MORNING + timedelta(hours=6)) == []
    assert source.fetched == []  # neither known nor rejected listings are loaded again


def test_listing_becomes_inactive_when_gone(config, make_listing, data_dir):
    store = Store(data_dir)
    collect(store, [FakeSource(config, [make_listing(id="ka:1")])], config, MORNING)
    collect(store, [FakeSource(config, [])], config, MORNING + timedelta(hours=72))
    assert not store.listings["ka:1"].active


def test_failing_source_is_tracked_and_alerted(config, data_dir):
    store = Store(data_dir)
    client = RecordingClient()
    for i in range(3):
        collect(store, [FakeSource(config, [], fail=True)], config, MORNING + timedelta(hours=i))
    assert store.health("kleinanzeigen").consecutive_failures == 3
    notify(store, client, config, AFTERNOON, DASHBOARD)
    assert any("Aktion nötig" in m.title for m in client.sent)


def test_morning_digest_is_scheduled_for_8(config, make_listing, data_dir):
    store = Store(data_dir)
    collect(store, [FakeSource(config, [make_listing(id="ka:1"), make_listing(id="ka:2", lat=49.04)])], config, MORNING)
    client = RecordingClient()
    notify(store, client, config, MORNING, DASHBOARD)

    summary = client.sent[-1]
    assert "2 neue Wohnungen" in summary.title
    first_delivery = min(m.deliver_at for m in client.sent)
    assert first_delivery.hour == 8 and first_delivery.minute == 0
    # best listing is delivered after the others so it shows up on top
    listing_msgs = client.sent[:-1]
    assert listing_msgs[-1].title.startswith("#1")
    assert all(l.notified_at for l in store.listings.values())
    assert store.state.last_digest_date == "2026-10-07"

    # second run the same day: no new digest
    client.sent.clear()
    notify(store, client, config, AFTERNOON, DASHBOARD)
    assert client.sent == []


def test_late_digest_is_sent_immediately(config, make_listing, data_dir):
    store = Store(data_dir)
    collect(store, [FakeSource(config, [make_listing()])], config, AFTERNOON)
    client = RecordingClient()
    notify(store, client, config, AFTERNOON, DASHBOARD)
    assert client.sent and all(m.deliver_at is None for m in client.sent)


def test_instant_push_only_for_top_listings_after_digest(config, make_listing, data_dir):
    store = Store(data_dir)
    store.state.last_digest_date = "2026-10-07"
    top = make_listing(id="ka:1", rent_warm=420, area_m2=45, rooms=2, features=["Garage"])
    meh = make_listing(id="ka:2", lat=49.05, lon=12.14, area_m2=22, rent_warm=590)
    collect(store, [FakeSource(config, [top, meh])], config, AFTERNOON)
    client = RecordingClient()
    notify(store, client, config, AFTERNOON, DASHBOARD)

    assert len(client.sent) == 1
    assert client.sent[0].title.startswith("Neue Top-Wohnung")
    assert store.listings["ka:2"].notified_at is None  # waits for tomorrow's digest


def test_empty_digest_message(config, data_dir):
    store = Store(data_dir)
    client = RecordingClient()
    notify(store, client, config, MORNING, DASHBOARD)
    assert client.sent[0].title == "Heute keine neuen Wohnungen"


def test_dry_run_does_not_mark_anything(config, make_listing, data_dir):
    store = Store(data_dir)
    collect(store, [FakeSource(config, [make_listing()])], config, MORNING)
    notify(store, NtfyClient(topic=None), config, MORNING, DASHBOARD)
    assert store.state.last_digest_date is None
    assert store.listings["ka:1"].notified_at is None


def test_store_roundtrip(config, make_listing, data_dir):
    store = Store(data_dir)
    collect(store, [FakeSource(config, [make_listing()])], config, MORNING)
    store.save()
    loaded = Store(data_dir).load()
    assert loaded.listings["ka:1"].to_dict() == store.listings["ka:1"].to_dict()
    assert loaded.health("kleinanzeigen").last_count == 1


def test_ntfy_payload():
    when = datetime(2026, 10, 7, 6, 0, tzinfo=timezone.utc)
    payload = build_payload(
        "topic",
        PushMessage(title="t", message="m", attach="https://img/1.jpg", actions=[("Öffnen", "https://x")], deliver_at=when),
    )
    assert payload["delay"] == str(int(when.timestamp()))
    assert payload["attach"] == "https://img/1.jpg"
    assert payload["actions"][0] == {"action": "view", "label": "Öffnen", "url": "https://x", "clear": False}
