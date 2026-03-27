from apps.cart.services import get_or_create_cart


def cart_snapshot(request):
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    cart = get_or_create_cart(user=request.user, session_key=session_key or "")
    return {
        "cart_snapshot": {
            "item_count": cart.item_count,
            "subtotal": cart.subtotal,
            "preview_items": list(
                cart.items.select_related("product", "variant").all()[:3]
            ),
        }
    }
