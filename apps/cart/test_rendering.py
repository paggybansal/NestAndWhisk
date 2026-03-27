from html import unescape

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_header_renders_mini_cart_with_full_height_drawer_shell(client):
	response = client.get(reverse("home"))
	content = unescape(response.content.decode())

	assert response.status_code == 200
	assert "Mini cart" in content
	assert 'href="/cart/"' in content
	assert '@click.prevent="open()"' in content
	assert "pointer-events-none fixed inset-0 z-[80] flex items-center justify-end overflow-hidden px-3 py-4 sm:px-5 lg:px-8" in content
	assert "pointer-events-auto ml-auto flex h-[min(46rem,calc(100vh-2rem))] w-full max-w-[min(35rem,calc(100vw-1.5rem))]" in content
	assert "lg:max-w-[min(36rem,calc(100vw-4rem))]" in content
	assert "min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-6" in content


@pytest.mark.django_db
def test_cart_detail_renders_delhi_ncr_delivery_summary(client):
	response = client.get(reverse("cart:detail"))
	content = unescape(response.content.decode())

	assert response.status_code == 200
	assert "Cart concierge" in content
	assert "Packed to arrive beautifully" in content
	assert 'lg:items-start' in content
	assert 'lg:items-end' not in content
	assert "Delhi NCR local delivery" in content
	assert "Coverage commonly includes Delhi, Gurugram, Noida, Greater Noida, Ghaziabad, and Faridabad" in content


