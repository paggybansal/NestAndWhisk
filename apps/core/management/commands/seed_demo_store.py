from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import BlogCategory, BlogPost
from apps.catalog.models import DietaryAttribute, Product, ProductCategory, ProductImage, ProductTag, ProductVariant
from apps.core.models import ContactSettings, FAQ, HomepageContent, NewsletterSignup, PolicyPage, SiteSettings, Testimonial
from apps.corporate.models import CorporateInquiry, CorporatePageContent
from apps.marketing.models import CampaignAttribution, MarketingSource
from apps.orders.models import Order, OrderItem, Payment
from apps.reviews.models import Review
from apps.subscriptions.models import SubscriptionPlan, SubscriptionShipment, UserSubscription


class Command(BaseCommand):
    help = "Seed the local Nest & Whisk storefront with polished demo merchandising content."

    @transaction.atomic
    def handle(self, *args, **options):
        site_settings = self.seed_site_settings()
        self.seed_homepage_content()
        self.seed_contact_settings()
        self.seed_policy_pages()
        self.seed_faqs()
        self.seed_testimonials()
        self.seed_newsletter_signups()
        marketing = self.seed_marketing_data()
        self.seed_blog_content()
        self.seed_corporate_page_content()
        taxonomy = self.seed_taxonomy()
        products = self.seed_products(taxonomy=taxonomy)
        self.seed_reviews(products=products)
        plans = self.seed_subscription_plans()
        self.seed_demo_operations(products=products, plans=plans, marketing=marketing)

        self.stdout.write(self.style.SUCCESS("Demo store content seeded successfully."))
        self.stdout.write(f"Home: {reverse('home')}")
        self.stdout.write(f"Shop: {reverse('catalog:shop')}")
        self.stdout.write(f"Subscriptions: {reverse('subscriptions:list')}")
        self.stdout.write(f"Build a box: {reverse('cart:build_a_box')}")
        self.stdout.write(f"Contact: {reverse('contact')}")
        self.stdout.write(f"Brand: {site_settings.site_name}")

    def seed_site_settings(self) -> SiteSettings:
        settings_obj = SiteSettings.load()
        settings_obj.site_name = "Nest & Whisk"
        settings_obj.tag_line = "Premium handcrafted cookies delivered with warmth, elegance, and delight."
        settings_obj.meta_title = "Nest & Whisk | Premium Artisan Cookie Gifting"
        settings_obj.meta_description = (
            "Small-batch artisan cookies, curated gifting boxes, subscriptions, and custom cookie assortments from Nest & Whisk."
        )
        settings_obj.announcement_bar_text = "Free nationwide shipping on curated gift boxes over ₹2,500."
        settings_obj.support_email = "hello@nestandwhisk.com"
        settings_obj.support_phone = "+1 (212) 555-0188"
        settings_obj.instagram_url = "https://instagram.com/nestandwhisk"
        settings_obj.pinterest_url = "https://pinterest.com/nestandwhisk"
        settings_obj.tiktok_url = "https://tiktok.com/@nestandwhisk"
        settings_obj.footer_blurb = (
            "Nest & Whisk blends the comfort of home baking with the elegance of handcrafted gifting. "
            "Every box is baked in small batches, wrapped beautifully, and meant to feel like a small celebration."
        )
        settings_obj.save()
        return settings_obj

    def seed_homepage_content(self) -> None:
        homepage = HomepageContent.load()
        homepage.eyebrow = "Premium handcrafted cookies"
        homepage.hero_title = "Delivered with warmth, elegance, and delight."
        homepage.hero_body = (
            "Thoughtfully baked in small batches, beautifully packed for gifting, and made to turn ordinary moments into something worth savoring."
        )
        homepage.primary_cta_label = "Shop Now"
        homepage.primary_cta_url = reverse("catalog:shop")
        homepage.secondary_cta_label = "Build a Box"
        homepage.secondary_cta_url = reverse("cart:build_a_box")
        homepage.tertiary_cta_label = "Subscribe"
        homepage.tertiary_cta_url = reverse("subscriptions:list")
        homepage.feature_one_label = "Bestseller"
        homepage.feature_one_title = "Sea Salt Caramel"
        homepage.feature_one_body = "Buttery centers, caramel notes, and a delicate salt finish that feels instantly gift-worthy."
        homepage.feature_two_label = "Seasonal"
        homepage.feature_two_title = "Pistachio Rose"
        homepage.feature_two_body = "A softly floral, elegant cookie with toasted pistachio crunch and a refined finish."
        homepage.feature_banner_label = "Curated gifting"
        homepage.feature_banner_body = (
            "Luxury packaging, personal gift notes, and recurring boxes that arrive with bakery-fresh polish."
        )
        homepage.quality_title = "Small-batch quality"
        homepage.quality_body_left = (
            "Premium chocolate, cultured butter, fragrant vanilla, and thoughtful finishing touches in every box."
        )
        homepage.quality_body_right = (
            "Build-your-own assortments, subscription rituals, and polished gifting moments crafted to feel personal."
        )
        homepage.save()

    def seed_contact_settings(self) -> None:
        contact = ContactSettings.load()
        contact.page_title = "We’d love to help you plan something delicious."
        contact.intro = (
            "Questions about gifting, events, custom assortments, or recurring cookie deliveries? Our studio team is here to help."
        )
        contact.inquiry_email = "hello@nestandwhisk.com"
        contact.business_hours = "Mon–Sat · 9am–6pm EST"
        contact.studio_location = "New York City studio kitchen"
        contact.contact_card_body = (
            "Tell us what you’re celebrating and we’ll guide you toward a thoughtful cookie moment that feels beautifully personal."
        )
        contact.save()

    def seed_policy_pages(self) -> None:
        policies = [
            {
                "title": "Shipping Policy",
                "slug": "shipping-policy",
                "summary": "Delivery windows, packaging standards, and transit timing.",
                "body": (
                    "We bake to order in small batches and dispatch most curated boxes within two business days. "
                    "Seasonal drops and custom orders may require additional lead time, and tracking details are sent as soon as each parcel leaves our studio."
                ),
                "sort_order": 1,
            },
            {
                "title": "Refund Policy",
                "slug": "refund-policy",
                "summary": "How Nest & Whisk handles quality concerns and damaged deliveries.",
                "body": (
                    "Because our cookies are handcrafted and perishable, refunds are handled case by case. "
                    "If your order arrives damaged or below standard, contact us within 48 hours and our team will make it right with a replacement, credit, or refund where appropriate."
                ),
                "sort_order": 2,
            },
            {
                "title": "Privacy Policy",
                "slug": "privacy-policy",
                "summary": "How we handle customer information and store communications.",
                "body": (
                    "We collect only the information needed to fulfill orders, personalize gifting, and send opted-in marketing communications. "
                    "Customer data is never sold, and account preferences can be updated or removed upon request."
                ),
                "sort_order": 3,
            },
            {
                "title": "Terms & Conditions",
                "slug": "terms-and-conditions",
                "summary": "Ordering, fulfillment, and website usage terms.",
                "body": (
                    "By placing an order with Nest & Whisk, you agree to our fulfillment timelines, ingredient disclosures, and limited liability for circumstances outside normal shipping control. "
                    "We reserve the right to update product assortments, pricing, and promotional terms as needed."
                ),
                "sort_order": 4,
            },
        ]
        for policy in policies:
            PolicyPage.objects.update_or_create(slug=policy["slug"], defaults=policy)

    def seed_faqs(self) -> None:
        faqs = [
            (
                "How fresh are your cookies when they arrive?",
                "Every Nest & Whisk order is baked in small batches and packed shortly before dispatch so your cookies arrive fresh, fragrant, and ready to enjoy.",
                "Freshness",
                1,
            ),
            (
                "Can I choose my own flavors in a gift box?",
                "Yes. Our build-a-box experience lets you choose your box size, curate the flavor mix, and include a gift message before checkout.",
                "Ordering",
                2,
            ),
            (
                "Do you offer recurring subscription boxes?",
                "We offer weekly, biweekly, and monthly plans with flexible renewal timing and customer-controlled flavor preferences.",
                "Subscriptions",
                3,
            ),
            (
                "Do you handle corporate gifting and event orders?",
                "Absolutely. We can help with client gifting, event favors, and larger custom assortments with polished packaging and delivery coordination.",
                "Corporate",
                4,
            ),
            (
                "Do your cookies contain allergens?",
                "Many of our cookies contain wheat, dairy, and eggs, and some flavors include nuts. Each product page includes ingredients and allergen notes for easy review.",
                "Ingredients",
                5,
            ),
        ]
        for question, answer, category, sort_order in faqs:
            FAQ.objects.update_or_create(
                question=question,
                defaults={
                    "answer": answer,
                    "category": category,
                    "is_published": True,
                    "sort_order": sort_order,
                },
            )

    def seed_testimonials(self) -> None:
        testimonials = [
            (
                "Ariana Chen",
                "Creative director",
                "The packaging felt as thoughtful as the cookies themselves — polished, warm, and impossibly delicious.",
                5,
                1,
            ),
            (
                "Marcus Hale",
                "Corporate gifting client",
                "We sent Nest & Whisk boxes to our top clients and every single one reached out to ask where they could order more.",
                5,
                2,
            ),
            (
                "Sofia Bennett",
                "Monthly subscriber",
                "It feels like receiving a small celebration at my door. The seasonal flavors are especially memorable.",
                5,
                3,
            ),
        ]
        for customer_name, customer_title, quote, rating, sort_order in testimonials:
            Testimonial.objects.update_or_create(
                customer_name=customer_name,
                defaults={
                    "customer_title": customer_title,
                    "quote": quote,
                    "rating": rating,
                    "is_featured": True,
                    "sort_order": sort_order,
                },
            )

    def seed_newsletter_signups(self) -> None:
        signups = [
            ("amelia@nwandfriends.test", "Amelia", "homepage"),
            ("jules@giftingcircle.test", "Jules", "footer"),
            ("lena@editorialtaste.test", "Lena", "seasonal-launch"),
        ]
        for email, first_name, source in signups:
            NewsletterSignup.objects.update_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "source": source,
                    "is_active": True,
                    "confirmed_at": timezone.now(),
                },
            )

    def seed_marketing_data(self) -> dict[str, dict[str, object]]:
        sources = {}
        for payload in [
            {"name": "Instagram", "slug": "instagram", "channel": "social", "is_active": True},
            {"name": "Newsletter", "slug": "newsletter", "channel": "email", "is_active": True},
            {"name": "Corporate Outreach", "slug": "corporate-outreach", "channel": "partnerships", "is_active": True},
        ]:
            source, _ = MarketingSource.objects.update_or_create(slug=payload["slug"], defaults=payload)
            sources[payload["slug"]] = source

        campaigns = {}
        for payload in [
            {
                "source": sources["instagram"],
                "campaign_name": "Spring gifting editorial",
                "campaign_code": "SPRING-GIFT-26",
                "medium": "social",
                "content_label": "Editorial carousel",
                "is_active": True,
            },
            {
                "source": sources["newsletter"],
                "campaign_name": "Founder's box launch",
                "campaign_code": "FOUNDER-BOX-26",
                "medium": "email",
                "content_label": "Founder launch note",
                "is_active": True,
            },
            {
                "source": sources["corporate-outreach"],
                "campaign_name": "Holiday corporate gifting",
                "campaign_code": "B2B-HOLIDAY-26",
                "medium": "outbound",
                "content_label": "Client gifting one-sheet",
                "is_active": True,
            },
        ]:
            campaign, _ = CampaignAttribution.objects.update_or_create(
                campaign_code=payload["campaign_code"], defaults=payload
            )
            campaigns[payload["campaign_code"]] = campaign

        return {"sources": sources, "campaigns": campaigns}

    def seed_blog_content(self) -> None:
        categories = {}
        for payload in [
            {
                "name": "Entertaining",
                "slug": "entertaining",
                "description": "Hosting ideas, tablescapes, gifting, and warm gathering rituals.",
                "is_active": True,
                "sort_order": 1,
            },
            {
                "name": "Behind the Bake",
                "slug": "behind-the-bake",
                "description": "Ingredient stories, creative process, and Nest & Whisk studio notes.",
                "is_active": True,
                "sort_order": 2,
            },
            {
                "name": "Seasonal Notes",
                "slug": "seasonal-notes",
                "description": "Limited drops, holiday pairings, and seasonal inspiration.",
                "is_active": True,
                "sort_order": 3,
            },
        ]:
            category, _ = BlogCategory.objects.update_or_create(slug=payload["slug"], defaults=payload)
            categories[payload["slug"]] = category

        now = timezone.now()
        posts = [
            {
                "slug": "how-to-build-a-cookie-gift-box-that-feels-personal",
                "category": categories["entertaining"],
                "title": "How to build a cookie gift box that feels deeply personal",
                "excerpt": "A few thoughtful choices—flavor balance, packaging tone, and a small handwritten note—can turn a sweet box into a memorable gift.",
                "body": (
                    "A beautiful gift box starts with intention. Begin by choosing a mix of familiar comfort and one unexpected flavor, then think about who you're sending it to and the mood you want the delivery to create.\n\n"
                    "For thank-yous, we love a balance of classic chocolate chip, sea salt caramel, and one elegant wildcard like Pistachio Rose. For celebrations, brighter profiles like Birthday Sprinkle or Red Velvet Crumble feel joyful without losing polish.\n\n"
                    "Packaging matters just as much. Ribbon-ready wrapping, a warm card, and a small note written with specificity can make the moment feel generous before the box is even opened."
                ),
                "hero_kicker": "Gifting guide",
                "reading_time_minutes": 4,
                "is_published": True,
                "is_featured": True,
                "published_at": now - timedelta(days=6),
                "seo_title": "How to build a personal cookie gift box | Nest & Whisk Journal",
                "seo_description": "A Nest & Whisk gifting guide to building a premium cookie box that feels personal and memorable.",
            },
            {
                "slug": "why-small-batch-baking-makes-a-difference",
                "category": categories["behind-the-bake"],
                "title": "Why small-batch baking changes the entire cookie experience",
                "excerpt": "From ingredient quality to texture and finishing, small-batch baking gives artisan cookies their warmth, nuance, and consistency.",
                "body": (
                    "Small-batch baking creates room for precision. Dough can rest properly, chocolate can be folded in thoughtfully, and each tray can be baked for the finish we want—golden edges, tender centers, and a fragrance that feels unmistakably bakery-fresh.\n\n"
                    "At Nest & Whisk, we think that kind of care is visible. It shows up in the shape of the cookie, the balance of salt, and the way every box feels intentionally assembled rather than mass produced."
                ),
                "hero_kicker": "Behind the bake",
                "reading_time_minutes": 3,
                "is_published": True,
                "is_featured": False,
                "published_at": now - timedelta(days=12),
                "seo_title": "Why small-batch baking matters | Nest & Whisk Journal",
                "seo_description": "Learn why small-batch baking creates a more premium artisan cookie experience.",
            },
            {
                "slug": "hosting-with-seasonal-pumpkin-spice",
                "category": categories["seasonal-notes"],
                "title": "Hosting notes: styling a cozy table around pumpkin spice season",
                "excerpt": "A few tactile details—linen napkins, candlelight, warm ceramics, and softly spiced cookies—create an effortless autumn table.",
                "body": (
                    "Seasonal hosting doesn't need to feel elaborate to feel beautiful. Start with warm neutrals, one textured floral or branch arrangement, and a serving plate that lets your cookies feel central.\n\n"
                    "Pumpkin Spice works especially well beside caramel tones, soft cream ceramics, and coffee-based pairings. Add one polished dessert fork, a linen napkin, and a handwritten place card and the whole moment feels elevated."
                ),
                "hero_kicker": "Seasonal notes",
                "reading_time_minutes": 5,
                "is_published": True,
                "is_featured": False,
                "published_at": now - timedelta(days=2),
                "seo_title": "Hosting with pumpkin spice season | Nest & Whisk Journal",
                "seo_description": "Cozy entertaining inspiration built around Nest & Whisk seasonal pumpkin spice cookies.",
            },
        ]
        for payload in posts:
            BlogPost.objects.update_or_create(slug=payload["slug"], defaults=payload)

    def seed_corporate_page_content(self) -> None:
        page = CorporatePageContent.load()
        page.eyebrow = "Corporate gifting"
        page.title = "Premium cookie gifting for clients, teams, and memorable moments."
        page.intro = (
            "From elevated client gifts to launch-day thank-yous and team celebrations, Nest & Whisk creates artisan cookie experiences that feel polished, warm, and unmistakably premium."
        )
        page.capability_title = "What we can tailor"
        page.capability_body = (
            "Curated assortments, seasonal gifting, personalized notes, premium packaging, and delivery timing planned around launches, milestones, and hosted events."
        )
        page.lead_time_title = "Typical lead time"
        page.lead_time_body = (
            "Most briefs can be reviewed within one to two business days, with larger or highly customized requests scoped on a more tailored timeline."
        )
        page.consultation_title = "Why brands choose us"
        page.consultation_body = (
            "Our gifting team pairs boutique hospitality with editorial presentation, so every touchpoint feels thoughtful from the first inquiry through final delivery."
        )
        page.save()

    def seed_taxonomy(self) -> dict[str, dict[str, object]]:
        categories = {}
        for payload in [
            {
                "name": "Signature Collection",
                "slug": "signature-collection",
                "short_description": "Our everyday favorites with a premium bakery finish.",
                "description": "Small-batch signature cookies designed for gifting, sharing, and repeat cravings.",
                "sort_order": 1,
            },
            {
                "name": "Seasonal Editions",
                "slug": "seasonal-editions",
                "short_description": "Rotating flavors inspired by the season and special occasions.",
                "description": "Limited-batch seasonal cookies with cozy ingredients and event-ready charm.",
                "sort_order": 2,
            },
            {
                "name": "Build-a-Box",
                "slug": "build-a-box",
                "short_description": "Custom assortment builders with flexible pack sizes.",
                "description": "Choose your box size, curate your flavor mix, and create a custom Nest & Whisk gift box.",
                "sort_order": 3,
            },
        ]:
            category, _ = ProductCategory.objects.update_or_create(slug=payload["slug"], defaults=payload)
            categories[payload["slug"]] = category

        tags = {}
        for payload in [
            {"name": "Bestseller", "slug": "bestseller"},
            {"name": "Gifting Favorite", "slug": "gifting-favorite"},
            {"name": "Seasonal", "slug": "seasonal"},
            {"name": "Staff Pick", "slug": "staff-pick"},
            {"name": "Limited Edition", "slug": "limited-edition"},
        ]:
            tag, _ = ProductTag.objects.update_or_create(slug=payload["slug"], defaults=payload)
            tags[payload["slug"]] = tag

        dietary = {}
        for payload in [
            {
                "name": "Vegetarian",
                "slug": "vegetarian",
                "badge_label": "Vegetarian",
                "description": "Made without meat-based ingredients.",
            },
            {
                "name": "Egg-Free",
                "slug": "egg-free",
                "badge_label": "Egg-free",
                "description": "Suitable for customers avoiding eggs.",
            },
            {
                "name": "Seasonal Favorite",
                "slug": "seasonal-favorite",
                "badge_label": "Seasonal",
                "description": "A limited seasonal release.",
            },
            {
                "name": "Gift-Ready",
                "slug": "gift-ready",
                "badge_label": "Gift-ready",
                "description": "Especially popular for gifting and celebrations.",
            },
        ]:
            attribute, _ = DietaryAttribute.objects.update_or_create(slug=payload["slug"], defaults=payload)
            dietary[payload["slug"]] = attribute

        return {"categories": categories, "tags": tags, "dietary": dietary}

    def seed_products(self, *, taxonomy: dict[str, dict[str, object]]) -> dict[str, Product]:
        categories = taxonomy["categories"]
        tags = taxonomy["tags"]
        dietary = taxonomy["dietary"]

        products: dict[str, Product] = {}
        product_payloads = [
            {
                "slug": "classic-chocolate-chip",
                "category": categories["signature-collection"],
                "name": "Classic Chocolate Chip",
                "short_description": "Golden edges, soft vanilla centers, and generous dark chocolate puddles.",
                "description": "Our signature bakery cookie: richly buttery, deeply comforting, and designed to feel like the very best version of a classic.",
                "ingredients": "Flour, cultured butter, dark chocolate, brown sugar, vanilla, sea salt.",
                "allergen_information": "Contains wheat, milk, and soy. Produced in a kitchen that also handles tree nuts.",
                "nutritional_notes": "Rich, indulgent, and best enjoyed slightly warm.",
                "care_instructions": "Store airtight and enjoy within 5 days, or freeze for later gifting moments.",
                "featured_label": "Signature",
                "is_featured": True,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 1,
                "meta_title": "Classic Chocolate Chip Cookies | Nest & Whisk",
                "meta_description": "Soft, bakery-style classic chocolate chip cookies with a premium artisan finish.",
                "tags": [tags["bestseller"], tags["gifting-favorite"]],
                "dietary": [dietary["vegetarian"]],
                "image": "catalog/products/classic-chip.svg",
                "variants": [
                    ("6-cookie box", "NW-CCHIP-06", 6, Decimal("18.00"), Decimal("20.00"), 36),
                    ("12-cookie box", "NW-CCHIP-12", 12, Decimal("34.00"), Decimal("38.00"), 52),
                ],
            },
            {
                "slug": "sea-salt-caramel",
                "category": categories["signature-collection"],
                "name": "Sea Salt Caramel",
                "short_description": "A luxurious caramel-centered cookie with a delicate salty finish.",
                "description": "Brown sugar dough, buttery caramel notes, and a whisper of sea salt create a refined cookie that feels instantly celebratory.",
                "ingredients": "Flour, butter, caramel pieces, brown sugar, vanilla, sea salt.",
                "allergen_information": "Contains wheat, milk, and soy.",
                "nutritional_notes": "Balanced sweetness with a savory finish.",
                "care_instructions": "Warm gently for a softer caramel center.",
                "featured_label": "Bestseller",
                "is_featured": True,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 2,
                "meta_title": "Sea Salt Caramel Cookies | Nest & Whisk",
                "meta_description": "Premium caramel cookies with buttery centers and a delicate sea salt finish.",
                "tags": [tags["bestseller"], tags["staff-pick"]],
                "dietary": [dietary["vegetarian"], dietary["gift-ready"]],
                "image": "catalog/products/sea-salt-caramel.svg",
                "variants": [
                    ("6-cookie box", "NW-SSC-06", 6, Decimal("19.00"), Decimal("22.00"), 28),
                    ("12-cookie box", "NW-SSC-12", 12, Decimal("36.00"), Decimal("40.00"), 40),
                ],
            },
            {
                "slug": "double-dark-chocolate",
                "category": categories["signature-collection"],
                "name": "Double Dark Chocolate",
                "short_description": "Deep cocoa dough with bittersweet chocolate throughout.",
                "description": "For devoted chocolate lovers, this cookie layers Dutch cocoa, bittersweet chunks, and a bakery-style soft center.",
                "ingredients": "Flour, cocoa powder, butter, dark chocolate, brown sugar, sea salt.",
                "allergen_information": "Contains wheat, milk, and soy.",
                "nutritional_notes": "Bold cocoa profile with a soft, rich finish.",
                "care_instructions": "Pairs beautifully with coffee or a glass of cold milk.",
                "featured_label": "Chocolate lover",
                "is_featured": True,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 3,
                "meta_title": "Double Dark Chocolate Cookies | Nest & Whisk",
                "meta_description": "Deep, bakery-style double dark chocolate cookies for serious chocolate lovers.",
                "tags": [tags["staff-pick"]],
                "dietary": [dietary["vegetarian"]],
                "image": "catalog/products/double-dark.svg",
                "variants": [
                    ("6-cookie box", "NW-DDC-06", 6, Decimal("19.00"), Decimal("22.00"), 24),
                    ("12-cookie box", "NW-DDC-12", 12, Decimal("36.00"), Decimal("40.00"), 34),
                ],
            },
            {
                "slug": "red-velvet-crumble",
                "category": categories["signature-collection"],
                "name": "Red Velvet Crumble",
                "short_description": "Festive cocoa crumb with cream-cheese inspired notes.",
                "description": "A playful yet polished cookie with velvet cocoa dough, vanilla lift, and a softly tangy bakery finish.",
                "ingredients": "Flour, butter, cocoa, vanilla, cream-cheese style chips, sugar.",
                "allergen_information": "Contains wheat, milk, and soy.",
                "nutritional_notes": "Celebratory and dessert-forward with a soft center.",
                "care_instructions": "Perfect for gifting and celebration tables.",
                "featured_label": "Celebration",
                "is_featured": False,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 4,
                "meta_title": "Red Velvet Crumble Cookies | Nest & Whisk",
                "meta_description": "Festive red velvet artisan cookies with refined cocoa notes.",
                "tags": [tags["gifting-favorite"]],
                "dietary": [dietary["vegetarian"], dietary["gift-ready"]],
                "image": "catalog/products/red-velvet.svg",
                "variants": [
                    ("6-cookie box", "NW-RVC-06", 6, Decimal("20.00"), Decimal("22.00"), 18),
                    ("12-cookie box", "NW-RVC-12", 12, Decimal("38.00"), Decimal("42.00"), 26),
                ],
            },
            {
                "slug": "pistachio-rose",
                "category": categories["signature-collection"],
                "name": "Pistachio Rose",
                "short_description": "Toasted pistachio and soft floral notes in a refined bakery cookie.",
                "description": "Elegant and softly aromatic, Pistachio Rose layers nutty crunch with a delicate floral finish that feels made for premium gifting.",
                "ingredients": "Flour, butter, pistachios, rose water, white chocolate, sugar.",
                "allergen_information": "Contains wheat, milk, soy, and tree nuts.",
                "nutritional_notes": "Fragrant, lightly sweet, and ideal for afternoon gifting spreads.",
                "care_instructions": "Serve at room temperature for the most expressive flavor.",
                "featured_label": "Elegant favorite",
                "is_featured": True,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 5,
                "meta_title": "Pistachio Rose Cookies | Nest & Whisk",
                "meta_description": "Elegant pistachio rose artisan cookies with floral bakery notes.",
                "tags": [tags["staff-pick"], tags["gifting-favorite"]],
                "dietary": [dietary["vegetarian"], dietary["gift-ready"]],
                "image": "catalog/products/pistachio-rose.svg",
                "variants": [
                    ("6-cookie box", "NW-PRS-06", 6, Decimal("22.00"), Decimal("24.00"), 16),
                    ("12-cookie box", "NW-PRS-12", 12, Decimal("42.00"), Decimal("46.00"), 22),
                ],
            },
            {
                "slug": "oatmeal-cinnamon",
                "category": categories["signature-collection"],
                "name": "Oatmeal Cinnamon",
                "short_description": "Toasty oats, warm cinnamon, and a cozy bakery chew.",
                "description": "Comforting and gently spiced, this cookie brings nostalgic warmth with a polished Nest & Whisk finish.",
                "ingredients": "Flour, rolled oats, butter, cinnamon, brown sugar, vanilla.",
                "allergen_information": "Contains wheat, milk, and gluten.",
                "nutritional_notes": "Soft, warmly spiced, and perfect for cozy gifting moments.",
                "care_instructions": "Lovely with tea and warm cider.",
                "featured_label": "Cozy classic",
                "is_featured": False,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 6,
                "meta_title": "Oatmeal Cinnamon Cookies | Nest & Whisk",
                "meta_description": "Warm, comforting oatmeal cinnamon artisan cookies with a bakery-soft texture.",
                "tags": [tags["staff-pick"]],
                "dietary": [dietary["vegetarian"]],
                "image": "catalog/products/classic-chip.svg",
                "variants": [
                    ("6-cookie box", "NW-OTC-06", 6, Decimal("18.00"), Decimal("20.00"), 20),
                    ("12-cookie box", "NW-OTC-12", 12, Decimal("34.00"), Decimal("37.00"), 30),
                ],
            },
            {
                "slug": "smores-stuffed",
                "category": categories["signature-collection"],
                "name": "S’mores Stuffed",
                "short_description": "Chocolate cookie dough with marshmallow pockets and graham crunch.",
                "description": "A playful crowd-pleaser with toasted marshmallow notes, melty chocolate, and a nostalgic fireside finish.",
                "ingredients": "Flour, butter, cocoa, marshmallow, graham crumbs, dark chocolate.",
                "allergen_information": "Contains wheat, milk, soy, and gelatin.",
                "nutritional_notes": "Indulgent and dessert-like with a soft, gooey center.",
                "care_instructions": "Warm briefly before serving for the most dramatic center.",
                "featured_label": "Crowd favorite",
                "is_featured": False,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 7,
                "meta_title": "S’mores Stuffed Cookies | Nest & Whisk",
                "meta_description": "Playful stuffed s’mores cookies with rich chocolate and marshmallow pockets.",
                "tags": [tags["gifting-favorite"]],
                "dietary": [dietary["vegetarian"], dietary["gift-ready"]],
                "image": "catalog/products/double-dark.svg",
                "variants": [
                    ("6-cookie box", "NW-SMS-06", 6, Decimal("21.00"), Decimal("24.00"), 18),
                    ("12-cookie box", "NW-SMS-12", 12, Decimal("40.00"), Decimal("45.00"), 24),
                ],
            },
            {
                "slug": "white-chocolate-macadamia",
                "category": categories["signature-collection"],
                "name": "White Chocolate Macadamia",
                "short_description": "Buttery macadamia crunch and silky white chocolate in every bite.",
                "description": "Smooth white chocolate and toasted macadamia nuts create a polished, luxurious cookie with a bright finish.",
                "ingredients": "Flour, butter, white chocolate, macadamia nuts, brown sugar, vanilla.",
                "allergen_information": "Contains wheat, milk, soy, and tree nuts.",
                "nutritional_notes": "Buttery and rich with satisfying crunch.",
                "care_instructions": "Serve slightly warm to soften the white chocolate.",
                "featured_label": "Luxury bite",
                "is_featured": False,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 8,
                "meta_title": "White Chocolate Macadamia Cookies | Nest & Whisk",
                "meta_description": "Luxurious white chocolate macadamia artisan cookies with buttery crunch.",
                "tags": [tags["gifting-favorite"]],
                "dietary": [dietary["vegetarian"], dietary["gift-ready"]],
                "image": "catalog/products/pistachio-rose.svg",
                "variants": [
                    ("6-cookie box", "NW-WCM-06", 6, Decimal("21.00"), Decimal("23.00"), 18),
                    ("12-cookie box", "NW-WCM-12", 12, Decimal("40.00"), Decimal("44.00"), 24),
                ],
            },
            {
                "slug": "birthday-sprinkle",
                "category": categories["signature-collection"],
                "name": "Birthday Sprinkle",
                "short_description": "Vanilla celebration cookies finished with cheerful rainbow sprinkles.",
                "description": "A joyful gifting favorite with buttery vanilla dough, white chocolate sweetness, and festive color in every box.",
                "ingredients": "Flour, butter, vanilla, white chocolate, sprinkles, sugar.",
                "allergen_information": "Contains wheat, milk, and soy.",
                "nutritional_notes": "Playful, sweet, and perfect for celebrations.",
                "care_instructions": "Ideal for party favors, birthdays, and thank-you gifting.",
                "featured_label": "Party-ready",
                "is_featured": False,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 9,
                "meta_title": "Birthday Sprinkle Cookies | Nest & Whisk",
                "meta_description": "Festive birthday sprinkle artisan cookies for joyful gifting moments.",
                "tags": [tags["gifting-favorite"]],
                "dietary": [dietary["vegetarian"], dietary["gift-ready"]],
                "image": "catalog/products/red-velvet.svg",
                "variants": [
                    ("6-cookie box", "NW-BDS-06", 6, Decimal("19.00"), Decimal("21.00"), 22),
                    ("12-cookie box", "NW-BDS-12", 12, Decimal("36.00"), Decimal("40.00"), 28),
                ],
            },
            {
                "slug": "seasonal-pumpkin-spice",
                "category": categories["seasonal-editions"],
                "name": "Seasonal Pumpkin Spice",
                "short_description": "Brown sugar warmth, autumn spice, and a soft bakery center.",
                "description": "Our seasonal pumpkin spice cookie is deeply cozy with brown butter notes, warming spice, and a mellow pumpkin finish.",
                "ingredients": "Flour, butter, pumpkin puree, cinnamon, nutmeg, clove, brown sugar.",
                "allergen_information": "Contains wheat and milk.",
                "nutritional_notes": "Seasonal, warmly spiced, and ideal for fall gifting.",
                "care_instructions": "Serve with chai, coffee, or a warm autumn table.",
                "featured_label": "Limited batch",
                "is_featured": True,
                "is_seasonal": True,
                "allows_build_a_box": True,
                "sort_order": 10,
                "meta_title": "Seasonal Pumpkin Spice Cookies | Nest & Whisk",
                "meta_description": "Limited seasonal pumpkin spice artisan cookies with cozy autumn flavor.",
                "tags": [tags["seasonal"], tags["limited-edition"]],
                "dietary": [dietary["vegetarian"], dietary["seasonal-favorite"]],
                "image": "catalog/products/pumpkin-spice.svg",
                "variants": [
                    ("6-cookie box", "NW-PMK-06", 6, Decimal("20.00"), Decimal("22.00"), 20),
                    ("12-cookie box", "NW-PMK-12", 12, Decimal("38.00"), Decimal("42.00"), 26),
                ],
            },
            {
                "slug": "signature-build-a-box",
                "category": categories["build-a-box"],
                "name": "Signature Build-a-Box",
                "short_description": "Choose your box size, curate your flavors, and send a polished cookie gift.",
                "description": "Our signature build-a-box format lets you create a custom Nest & Whisk assortment with flexible sizing, refined packaging, and a personal note.",
                "ingredients": "A rotating assortment selected from our active flavor collection.",
                "allergen_information": "Allergens vary by selected flavors. See each flavor page for complete details.",
                "nutritional_notes": "Totals vary according to the selected assortment.",
                "care_instructions": "Ideal for gifting, celebrations, and curated sharing boxes.",
                "featured_label": "Custom gifting",
                "is_featured": True,
                "is_seasonal": False,
                "allows_build_a_box": True,
                "sort_order": 11,
                "meta_title": "Build Your Own Cookie Box | Nest & Whisk",
                "meta_description": "Create a custom artisan cookie assortment with Nest & Whisk build-a-box gifting.",
                "tags": [tags["gifting-favorite"]],
                "dietary": [dietary["gift-ready"]],
                "image": "catalog/products/signature-box.svg",
                "variants": [
                    ("6-cookie custom box", "NW-BUILD-06", 6, Decimal("18.00"), Decimal("20.00"), 40),
                    ("12-cookie custom box", "NW-BUILD-12", 12, Decimal("34.00"), Decimal("38.00"), 40),
                ],
            },
        ]

        for payload in product_payloads:
            tag_objects = payload.pop("tags")
            dietary_objects = payload.pop("dietary")
            image_path = payload.pop("image")
            variant_rows = payload.pop("variants")
            product, _ = Product.objects.update_or_create(slug=payload["slug"], defaults=payload)
            product.tags.set(tag_objects)
            product.dietary_attributes.set(dietary_objects)
            ProductImage.objects.update_or_create(
                product=product,
                sort_order=0,
                defaults={
                    "image": image_path,
                    "alt_text": product.name,
                    "is_primary": True,
                },
            )
            for index, (name, sku, pack_size, price, compare_at_price, inventory_quantity) in enumerate(variant_rows):
                ProductVariant.objects.update_or_create(
                    sku=sku,
                    defaults={
                        "product": product,
                        "name": name,
                        "pack_size": pack_size,
                        "price": price,
                        "compare_at_price": compare_at_price,
                        "inventory_quantity": inventory_quantity,
                        "low_stock_threshold": 6,
                        "weight_grams": pack_size * 68,
                        "is_default": index == 0,
                        "is_active": True,
                        "sort_order": index,
                    },
                )
            products[product.slug] = product
        return products

    def seed_reviews(self, *, products: dict[str, Product]) -> None:
        review_payloads = [
            {
                "product": products["classic-chocolate-chip"],
                "customer_name": "Naomi Park",
                "customer_email": "naomi@classictaste.test",
                "rating": 5,
                "title": "A true bakery classic",
                "body": "Exactly the kind of cookie you hope for in a premium gift box — soft, buttery, and packed with chocolate.",
                "is_verified_purchase": True,
            },
            {
                "product": products["sea-salt-caramel"],
                "customer_name": "Daniel Flores",
                "customer_email": "daniel@caramelclub.test",
                "rating": 5,
                "title": "The perfect sweet-salty balance",
                "body": "These disappeared first from our office tasting box. The caramel flavor is rich without feeling heavy.",
                "is_verified_purchase": True,
            },
            {
                "product": products["pistachio-rose"],
                "customer_name": "Ella Sutton",
                "customer_email": "ella@editselect.test",
                "rating": 5,
                "title": "Elegant and memorable",
                "body": "A beautifully refined cookie with floral notes that still feels warm and comforting.",
                "is_verified_purchase": False,
            },
            {
                "product": products["seasonal-pumpkin-spice"],
                "customer_name": "Mina Kapoor",
                "customer_email": "mina@seasonaltable.test",
                "rating": 5,
                "title": "Autumn in cookie form",
                "body": "Warm spice, soft texture, and a lovely bakery finish. I’d order this every fall.",
                "is_verified_purchase": True,
            },
            {
                "product": products["signature-build-a-box"],
                "customer_name": "Hugo Bennett",
                "customer_email": "hugo@gifthost.test",
                "rating": 5,
                "title": "Our go-to hostess gift",
                "body": "The ability to curate flavors made the box feel truly personal — and the packaging looked stunning.",
                "is_verified_purchase": True,
            },
        ]
        for payload in review_payloads:
            Review.objects.update_or_create(
                product=payload["product"],
                customer_email=payload["customer_email"],
                title=payload["title"],
                defaults={
                    "customer_name": payload["customer_name"],
                    "rating": payload["rating"],
                    "body": payload["body"],
                    "is_approved": True,
                    "is_verified_purchase": payload["is_verified_purchase"],
                },
            )

    def seed_subscription_plans(self) -> dict[str, SubscriptionPlan]:
        plans: dict[str, SubscriptionPlan] = {}
        payloads = [
            {
                "slug": "weekly-signature-box",
                "name": "Weekly Signature Box",
                "headline": "A dependable weekly ritual for cookie lovers who never want to run out.",
                "description": "A rotating assortment of our signature favorites delivered every week in a premium gift-ready format.",
                "billing_interval": SubscriptionPlan.BillingInterval.WEEKLY,
                "cadence_days": 7,
                "shipment_offset_days": 3,
                "box_size": "12-cookie curated box",
                "price": Decimal("34.00"),
                "compare_at_price": Decimal("38.00"),
                "is_featured": False,
                "is_active": True,
                "sort_order": 1,
            },
            {
                "slug": "biweekly-hostess-edit",
                "name": "Biweekly Hostess Edit",
                "headline": "A polished gifting rhythm for dinner parties, thank-yous, and thoughtful touchpoints.",
                "description": "A balanced biweekly cookie edit designed for sharing, gifting, and keeping something beautiful on hand.",
                "billing_interval": SubscriptionPlan.BillingInterval.BIWEEKLY,
                "cadence_days": 14,
                "shipment_offset_days": 5,
                "box_size": "12-cookie curated box",
                "price": Decimal("36.00"),
                "compare_at_price": Decimal("40.00"),
                "is_featured": True,
                "is_active": True,
                "sort_order": 2,
            },
            {
                "slug": "monthly-founders-box",
                "name": "Monthly Founder’s Box",
                "headline": "A monthly delivery with signature favorites and a seasonal surprise.",
                "description": "Our most giftable recurring plan — part signature collection, part seasonal reveal, and always packed with editorial polish.",
                "billing_interval": SubscriptionPlan.BillingInterval.MONTHLY,
                "cadence_days": 30,
                "shipment_offset_days": 8,
                "box_size": "18-cookie premium box",
                "price": Decimal("52.00"),
                "compare_at_price": Decimal("58.00"),
                "is_featured": False,
                "is_active": True,
                "sort_order": 3,
            },
        ]
        for payload in payloads:
            plan, _ = SubscriptionPlan.objects.update_or_create(slug=payload["slug"], defaults=payload)
            plans[plan.slug] = plan
        return plans

    def seed_demo_operations(self, *, products: dict[str, Product], plans: dict[str, SubscriptionPlan], marketing: dict[str, dict[str, object]]) -> None:
        User = get_user_model()
        customer, created = User.objects.get_or_create(
            email="claire.holloway@nestandwhisk.test",
            defaults={
                "first_name": "Claire",
                "last_name": "Holloway",
                "phone_number": "+1 (646) 555-0142",
                "is_active": True,
            },
        )
        if created:
            customer.set_unusable_password()
            customer.save(update_fields=["password"])

        featured_product = products["sea-salt-caramel"]
        featured_variant = featured_product.variants.order_by("sort_order", "price").first()
        seasonal_product = products["seasonal-pumpkin-spice"]
        seasonal_variant = seasonal_product.variants.order_by("sort_order", "price").first()
        if not featured_variant or not seasonal_variant:
            return

        paid_order, _ = Order.objects.update_or_create(
            order_number="NWDEMO1001",
            defaults={
                "user": customer,
                "status": Order.Status.PAID,
                "payment_status": Order.PaymentStatus.PAID,
                "customer_email": customer.email,
                "customer_first_name": customer.first_name,
                "customer_last_name": customer.last_name,
                "customer_phone": customer.phone_number,
                "shipping_address_line_1": "112 Mercer Street",
                "shipping_address_line_2": "Apartment 4B",
                "shipping_city": "New York",
                "shipping_state": "NY",
                "shipping_postal_code": "10012",
                "shipping_country": "United States",
                "delivery_notes": "Leave with concierge if unavailable.",
                "gift_note": "Thank you for hosting such a beautiful evening.",
                "is_gift_wrapped": True,
                "preferred_delivery_date": date.today() + timedelta(days=5),
                "subtotal": featured_variant.price,
                "discount_total": Decimal("0.00"),
                "shipping_total": Decimal("0.00"),
                "total": featured_variant.price,
                "currency": "INR",
                "provider": "stripe",
                "provider_payment_id": "pi_demo_paid_1001",
                "provider_checkout_id": "cs_demo_paid_1001",
                "placed_at": timezone.now() - timedelta(days=2),
            },
        )
        OrderItem.objects.update_or_create(
            order=paid_order,
            sku=featured_variant.sku,
            defaults={
                "product": featured_product,
                "variant": featured_variant,
                "product_name": featured_product.name,
                "variant_name": featured_variant.name,
                "quantity": 1,
                "unit_price": featured_variant.price,
                "line_total": featured_variant.price,
                "gift_message": "With love, Claire",
                "packaging_option": "Ribbon-ready signature wrap",
            },
        )
        Payment.objects.update_or_create(
            order=paid_order,
            provider_reference="demo-payment-paid-1001",
            defaults={
                "amount": paid_order.total,
                "currency": "INR",
                "provider": "stripe",
                "provider_payment_id": paid_order.provider_payment_id,
                "provider_checkout_id": paid_order.provider_checkout_id,
                "status": Payment.Status.SUCCEEDED,
                "receipt_url": "https://payments.example.test/receipt/demo-payment-paid-1001",
                "raw_response": {"demo": True, "kind": "seeded-payment"},
                "paid_at": timezone.now() - timedelta(days=2),
            },
        )

        pending_order, _ = Order.objects.update_or_create(
            order_number="NWDEMO1002",
            defaults={
                "user": customer,
                "status": Order.Status.PENDING,
                "payment_status": Order.PaymentStatus.PROCESSING,
                "customer_email": customer.email,
                "customer_first_name": customer.first_name,
                "customer_last_name": customer.last_name,
                "customer_phone": customer.phone_number,
                "shipping_address_line_1": "112 Mercer Street",
                "shipping_address_line_2": "Apartment 4B",
                "shipping_city": "New York",
                "shipping_state": "NY",
                "shipping_postal_code": "10012",
                "shipping_country": "United States",
                "delivery_notes": "Ring bell once.",
                "gift_note": "A little autumn treat.",
                "is_gift_wrapped": False,
                "preferred_delivery_date": date.today() + timedelta(days=9),
                "subtotal": seasonal_variant.price,
                "discount_total": Decimal("0.00"),
                "shipping_total": Decimal("6.00"),
                "total": seasonal_variant.price + Decimal("6.00"),
                "currency": "INR",
                "provider": "stripe",
                "provider_payment_id": "pi_demo_processing_1002",
                "provider_checkout_id": "cs_demo_processing_1002",
                "placed_at": timezone.now() - timedelta(hours=18),
            },
        )
        OrderItem.objects.update_or_create(
            order=pending_order,
            sku=seasonal_variant.sku,
            defaults={
                "product": seasonal_product,
                "variant": seasonal_variant,
                "product_name": seasonal_product.name,
                "variant_name": seasonal_variant.name,
                "quantity": 1,
                "unit_price": seasonal_variant.price,
                "line_total": seasonal_variant.price,
                "gift_message": "Hope this brightens your week.",
                "packaging_option": "Minimal seasonal wrap",
            },
        )
        Payment.objects.update_or_create(
            order=pending_order,
            provider_reference="demo-payment-processing-1002",
            defaults={
                "amount": pending_order.total,
                "currency": "INR",
                "provider": "stripe",
                "provider_payment_id": pending_order.provider_payment_id,
                "provider_checkout_id": pending_order.provider_checkout_id,
                "status": Payment.Status.PENDING,
                "raw_response": {"demo": True, "kind": "seeded-processing-payment"},
            },
        )

        subscription, _ = UserSubscription.objects.update_or_create(
            user=customer,
            plan=plans["biweekly-hostess-edit"],
            defaults={
                "latest_order": paid_order,
                "status": UserSubscription.Status.ACTIVE,
                "flavor_preferences": [
                    "Sea Salt Caramel",
                    "Classic Chocolate Chip",
                    "Pistachio Rose",
                ],
                "renewal_day": min(date.today().day, 28),
                "admin_notes": "Seeded local subscription for admin preview.",
            },
        )
        subscription.refresh_schedule(from_date=date.today())
        subscription.latest_order = paid_order
        subscription.status = UserSubscription.Status.ACTIVE
        subscription.save(update_fields=["latest_order", "status", "next_renewal_date", "next_shipment_date", "updated_at"])

        if subscription.next_shipment_date:
            SubscriptionShipment.objects.update_or_create(
                subscription=subscription,
                scheduled_for=subscription.next_shipment_date,
                defaults={
                    "order": paid_order,
                    "status": SubscriptionShipment.ShipmentStatus.UPCOMING,
                    "tracking_reference": "NW-SHIP-DEMO-1001",
                    "shipment_notes": "Seeded upcoming subscription shipment.",
                },
            )

        CorporateInquiry.objects.update_or_create(
            company_name="Aster & Pine Interiors",
            email="events@asterpine.test",
            defaults={
                "user": customer,
                "source": marketing["sources"]["corporate-outreach"],
                "campaign": marketing["campaigns"]["B2B-HOLIDAY-26"],
                "contact_name": "Ava Reynolds",
                "phone_number": "+1 (917) 555-0124",
                "occasion": "Holiday client gifting",
                "quantity_estimate": 60,
                "budget_range": CorporateInquiry.BudgetRange.OVER_1000,
                "event_date": date.today() + timedelta(days=45),
                "delivery_date": date.today() + timedelta(days=40),
                "gifting_goal": "A premium year-end thank-you that feels warm and design-forward.",
                "notes": "Interested in a polished neutral palette, ribbon-ready wrapping, and a short printed note tucked inside every box.",
                "status": CorporateInquiry.Status.QUOTED,
                "admin_notes": "Seeded local lead for pipeline review.",
            },
        )

