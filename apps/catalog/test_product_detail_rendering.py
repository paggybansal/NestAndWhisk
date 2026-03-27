from html import unescape

import pytest
from django.urls import reverse

from apps.catalog.models import Product, ProductCategory, ProductVariant


@pytest.mark.django_db
def test_product_detail_renders_merchandising_modules_for_rich_product_content(client):
    category = ProductCategory.objects.create(name="Signature Cookies", slug="signature-cookies")
    product = Product.objects.create(
        category=category,
        name="Sea Salt Caramel",
        slug="sea-salt-caramel",
        short_description="Buttery caramel cookies with a glossy sea salt finish.",
        description="A rich caramel-forward cookie with a soft center and polished finish.",
        ingredients="Butter, flour, caramel, sea salt, dark chocolate",
        ingredient_highlights="Brown butter, Dark chocolate, Sea salt flakes",
        nutritional_notes="Enjoy with coffee or warm gently before serving.",
        care_instructions="Store sealed in a cool, dry place away from direct heat.",
        texture_chewy=4,
        texture_crunchy=2,
        texture_gooey=5,
        pairing_notes="coffee, chai, milk",
        shelf_life_days=6,
        storage_guidance="Keep airtight and warm for 8 seconds before serving.",
        video_url="https://cdn.example.com/videos/sea-salt-caramel.mp4",
        video_caption="A quick look at the caramel sheen and gooey center.",
        is_active=True,
    )
    ProductVariant.objects.create(
        product=product,
        name="Box of 6",
        sku="SSC-6",
        pack_size=6,
        price="799.00",
        inventory_quantity=12,
        is_active=True,
    )

    response = client.get(reverse("catalog:product_detail", kwargs={"slug": product.slug}))
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert "Bakery impression" in content
    assert "Brown butter" in content
    assert "Texture meter" in content
    assert "Chewy" in content and "4/5" in content
    assert "Perfect pairings" in content
    assert "Coffee" in content and "Tea" in content and "Milk" in content
    assert "Shelf life & storage" in content
    assert "Best enjoyed within 6 days of delivery" in content
    assert "Storage guidance" in content
    assert "Gifting detail" in content
    assert "Short product video" in content
    assert '<video class="aspect-video w-full' in content
