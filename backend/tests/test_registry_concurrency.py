from concurrent.futures import ThreadPoolExecutor

from app.api.routers import assets as assets_router
from app.contracts.artifacts import AssetType
from app.storage.models import AssetFilter, AssetMetadata
from app.storage.registry import AssetRegistry


def test_concurrent_asset_listing_serializes_shared_sqlite_connection(tmp_path):
    registry = AssetRegistry(
        store_root=tmp_path / "store",
        db_path=tmp_path / "store" / "registry.db",
        project_root=tmp_path,
    )
    # Create enough metadata rows that concurrent cursor interleaving is
    # exercised during the list query and per-row lineage lookup.
    for index in range(24):
        registry.db.insert_asset(
            AssetMetadata(
                asset_id=f"asset_{index:02d}",
                project_id="concurrent_project",
                asset_type=AssetType.IMAGE_REFERENCE,
                name=f"reference-{index}",
                original_filename=f"reference-{index}.png",
                managed_path=f"objects/{index:02d}.png",
                mime_type="image/png",
                extension=".png",
                byte_size=16,
                content_sha256=f"{index:064x}",
            )
        )

    expected = {f"asset_{index:02d}" for index in range(24)}
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(
            lambda _: {asset.asset_id for asset in registry.list_assets(AssetFilter(project_id="concurrent_project"))},
            range(48),
        ))

    assert all(result == expected for result in results)
    registry.db.close()


def test_registry_singleton_is_initialized_once_for_concurrent_first_requests(tmp_path, monkeypatch):
    monkeypatch.setattr(assets_router, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(assets_router, "_registry_instance", None)

    with ThreadPoolExecutor(max_workers=12) as pool:
        registries = list(pool.map(lambda _: assets_router.get_registry(), range(24)))

    assert len({id(registry) for registry in registries}) == 1
    registries[0].db.close()
