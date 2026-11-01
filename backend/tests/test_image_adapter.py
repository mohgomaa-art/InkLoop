import base64
import io

from PIL import Image

from app.image_adapter import GenerationRequest, MetaImageGenerationAdapter, ReferenceImagePayload


def _png_bytes():
    image = Image.new("RGB", (2, 2), "white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_live_provider_receives_requested_canvas_aspect_ratio(monkeypatch):
    import httpx

    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {"x-request-id": "req_test"}

        @staticmethod
        def json():
            return {"data": [{"b64_json": base64.b64encode(_png_bytes()).decode()}]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, **kwargs):
            captured["url"] = url
            captured["payload"] = kwargs["json"]
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    adapter = MetaImageGenerationAdapter(
        config=type("Config", (), {
            "has_credentials": True,
            "model_api_key": "unit-test-key",
            "muse_image_model": "muse-image-1.0",
            "meta_base_url": "https://provider.invalid/v1",
        })()
    )

    response = adapter.generate(GenerationRequest(
        prompt="A doctor checks a chart",
        panel_id="panel_02",
        dimensions=[258, 601],
    ))

    assert response.success is True
    assert captured["url"] == "https://provider.invalid/v1/images/generations"
    assert captured["payload"]["size"] == "258x601"
    assert response.sanitized_metadata["requested_dimensions"] == [258, 601]


def test_live_provider_omits_invalid_dimensions_instead_of_sending_bad_size(monkeypatch):
    import httpx

    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {}

        @staticmethod
        def json():
            return {"data": [{"b64_json": base64.b64encode(_png_bytes()).decode()}]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, _url, **kwargs):
            captured.update(kwargs["json"])
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    adapter = MetaImageGenerationAdapter(
        config=type("Config", (), {
            "has_credentials": True,
            "model_api_key": "unit-test-key",
            "muse_image_model": "muse-image-1.0",
            "meta_base_url": "https://provider.invalid/v1",
        })()
    )

    response = adapter.generate(GenerationRequest(
        prompt="An editorial comic panel",
        dimensions=[0, 0],
    ))

    assert response.success is True
    assert "size" not in captured


def test_live_provider_edit_sends_object_reference_bytes_and_preserves_input_role_order(monkeypatch):
    import httpx

    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {"x-request-id": "req_object_ref"}

        @staticmethod
        def json():
            return {"data": [{"b64_json": base64.b64encode(_png_bytes()).decode()}]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, **kwargs):
            captured["url"] = url
            captured["payload"] = kwargs["json"]
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    object_bytes = _png_bytes()
    adapter = MetaImageGenerationAdapter(
        config=type("Config", (), {
            "has_credentials": True,
            "model_api_key": "unit-test-key",
            "muse_image_model": "muse-image-1.0",
            "meta_base_url": "https://provider.invalid/v1",
        })()
    )
    response = adapter.generate(GenerationRequest(
        prompt="Reference image order: stable physical identity of object hand_lamp only.",
        reference_images=[ReferenceImagePayload(
            asset_id="lamp_anchor", image_bytes=object_bytes, mime_type="image/png",
            role="object_reference", prop_id="hand_lamp",
        )],
    ))

    assert response.success is True
    assert captured["url"] == "https://provider.invalid/v1/images/edits"
    data_url = captured["payload"]["images"][0]["image_url"]
    assert data_url.startswith("data:image/png;base64,")
    assert base64.b64decode(data_url.split(",", 1)[1]) == object_bytes
    assert "stable physical identity of object hand_lamp only" in captured["payload"]["prompt"]
    assert response.sanitized_metadata["reference_roles"] == ["object_reference"]


def test_live_provider_missing_credentials_is_a_truthful_failure_for_object_reference(monkeypatch):
    import httpx

    monkeypatch.setattr(httpx, "Client", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")))
    adapter = MetaImageGenerationAdapter(
        config=type("Config", (), {
            "has_credentials": False,
            "model_api_key": None,
            "muse_image_model": "muse-image-1.0",
            "meta_base_url": "https://provider.invalid/v1",
        })()
    )
    response = adapter.generate(GenerationRequest(
        prompt="Match the lamp reference.",
        reference_images=[ReferenceImagePayload(
            asset_id="lamp_anchor", image_bytes=_png_bytes(), role="object_reference", prop_id="hand_lamp",
        )],
    ))
    assert response.success is False
    assert response.http_status == 401
    assert response.error_message == "Meta Model API key is not configured."
