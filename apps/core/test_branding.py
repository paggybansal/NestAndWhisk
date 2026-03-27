from apps.core.branding import get_brand_logo_path


def test_get_brand_logo_path_prefers_png_over_jpeg(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    (tmp_path / "Logo.jpeg").write_bytes(b"jpeg")
    assert get_brand_logo_path() == "/media/Logo.jpeg"

    (tmp_path / "Logo.png").write_bytes(b"png")
    assert get_brand_logo_path() == "/media/Logo.png"
