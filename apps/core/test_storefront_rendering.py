from html import unescape

import pytest
from django.urls import reverse

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductCategory, ProductVariant
from apps.core.models import HomepageContent, SiteSettings


@pytest.mark.django_db
class TestPremiumStorefrontRendering:
    def setup_catalog(self):
        SiteSettings.load()
        HomepageContent.load()
        category = ProductCategory.objects.create(
            name="Signature Cookies",
            slug="signature-cookies",
            description="Bestselling handcrafted cookie boxes.",
        )
        product = Product.objects.create(
            category=category,
            name="Sea Salt Caramel",
            slug="sea-salt-caramel",
            short_description="Caramel-rich cookies finished with flaky sea salt.",
            description="A rich, buttery cookie with caramel depth and a polished sea salt finish.",
            is_active=True,
            is_featured=True,
            is_seasonal=True,
        )
        variant = ProductVariant.objects.create(
            product=product,
            name="Box of 6",
            sku="SSC-6",
            pack_size=6,
            price="799.00",
            inventory_quantity=10,
            is_default=True,
            is_active=True,
        )
        return category, product, variant

    def test_homepage_shop_and_product_detail_render_with_premium_sections(self, client):
        category, product, _variant = self.setup_catalog()

        home_response = client.get(reverse("home"))
        shop_response = client.get(reverse("catalog:shop"))
        filtered_shop_response = client.get(reverse("catalog:shop"), {"category": category.slug})
        product_response = client.get(reverse("catalog:product_detail", kwargs={"slug": product.slug}))

        home_content = unescape(home_response.content.decode())
        shop_content = unescape(shop_response.content.decode())
        filtered_shop_content = unescape(filtered_shop_response.content.decode())
        product_content = unescape(product_response.content.decode())

        assert home_response.status_code == 200
        assert "Shop by moment" in home_content
        assert "Featured collection" in home_content

        assert shop_response.status_code == 200
        assert "Browse by category" in shop_content
        assert "Shop notes" in shop_content
        assert "Curator’s note" in shop_content
        assert "Refine the collection" in shop_content
        assert "Serving mood" not in shop_content
        assert "Ready to ship with current inventory available." not in shop_content

        assert filtered_shop_response.status_code == 200
        assert product.name in filtered_shop_content
        assert "Category selected" in filtered_shop_content

        assert product_response.status_code == 200
        assert "Choose your box size" in product_content
        assert "Bakery impression" in product_content
        assert "Care & notes" in product_content or "Description" in product_content
        assert "Delhi NCR local delivery" in product_content
        assert "Coverage commonly includes Delhi, Gurugram, Noida, Greater Noida, Ghaziabad, and Faridabad" in product_content
        assert "Texture meter" in product_content
        assert "Perfect pairings" in product_content
        assert "Shelf life & storage" in product_content

    def test_checkout_renders_premium_modules_and_payment_choices(self, client):
        _category, product, variant = self.setup_catalog()
        session = client.session
        session.save()
        cart = Cart.objects.create(session_key=session.session_key, is_active=True)
        CartItem.objects.create(
            cart=cart,
            product=product,
            variant=variant,
            quantity=2,
            unit_price=variant.price,
        )

        response = client.get(reverse("checkout:index"))
        content = unescape(response.content.decode())

        assert response.status_code == 200
        assert "Choose how you want to finish checkout." in content
        assert "Order summary" in content
        assert "Checkout promise" in content
        assert "Luxury details" in content
        assert "Stripe test mode" in content
        assert "Delhi NCR delivery" in content
        assert "Try a Delhi NCR pincode like 110001, 122002, 201301, 121001" in content

