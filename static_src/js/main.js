import Alpine from 'alpinejs';
import '../css/main.css';

window.Alpine = Alpine;

const formatINR = (value) => {
  const numericValue = Number.parseFloat(value || 0);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isNaN(numericValue) ? 0 : numericValue);
};

const escapeHtml = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;');

const initializeFaqAssistant = () => {
  const root = document.querySelector('[data-faq-assistant]');
  if (!root) return;

  const endpoint = root.dataset.endpoint;
  const form = root.querySelector('[data-faq-assistant-form]');
  const input = root.querySelector('#faq-assistant-question');
  const status = root.querySelector('[data-faq-assistant-status]');
  const messages = root.querySelector('[data-faq-assistant-messages]');
  const starterButtons = root.querySelectorAll('[data-faq-assistant-starter]');
  if (!endpoint || !form || !input || !status || !messages) return;

  const setStatus = (message, tone = 'muted') => {
    status.textContent = message;
    status.classList.remove('hidden', 'text-cocoa/55', 'text-caramel', 'text-dusty-rose');
    if (tone === 'loading') {
      status.classList.add('text-caramel');
    } else if (tone === 'error') {
      status.classList.add('text-dusty-rose');
    } else {
      status.classList.add('text-cocoa/55');
    }
  };

  const appendBubble = ({ text, role = 'assistant', meta = '', ctaUrl = '', ctaLabel = '' }) => {
    const article = document.createElement('article');
    article.className = role === 'user'
      ? 'ml-auto max-w-[92%] rounded-[1.4rem] rounded-br-md bg-cocoa px-4 py-3 text-sm leading-7 text-cream shadow-soft'
      : 'max-w-[92%] rounded-[1.4rem] rounded-bl-md bg-white px-4 py-3 text-sm leading-7 text-cocoa shadow-soft';

    let html = `<p>${escapeHtml(text)}</p>`;
    if (meta) {
      html += `<p class="mt-3 text-[0.68rem] font-semibold uppercase tracking-[0.25em] ${role === 'user' ? 'text-cream/70' : 'text-caramel'}">${escapeHtml(meta)}</p>`;
    }
    if (ctaUrl && ctaLabel && role === 'assistant') {
      html += `<a href="${escapeHtml(ctaUrl)}" class="mt-4 inline-flex rounded-full border border-cocoa/10 px-3 py-2 text-xs font-semibold text-cocoa transition hover:border-caramel hover:text-caramel">${escapeHtml(ctaLabel)}</a>`;
    }
    article.innerHTML = html;
    messages.appendChild(article);
    messages.scrollTop = messages.scrollHeight;
  };

  const askQuestion = async (question) => {
    const trimmed = question.trim();
    if (!trimmed) {
      setStatus('Please enter a fuller question so I can help.', 'error');
      return;
    }

    appendBubble({ text: trimmed, role: 'user', meta: 'You' });
    setStatus('Checking the Nest & Whisk support guide…', 'loading');

    try {
      const url = new URL(endpoint, window.location.origin);
      url.searchParams.set('question', trimmed);
      const response = await fetch(url, { headers: { Accept: 'application/json' } });
      const data = await response.json();

      appendBubble({
        text: data.answer || 'I could not find the right answer just now.',
        role: 'assistant',
        meta: data.used_ai && data.model_name
          ? `AI-assisted · ${data.model_name}`
          : (data.source_title ? `${data.source_type} · ${data.source_title}` : 'Nest & Whisk support'),
        ctaUrl: data.cta_url || '/contact/',
        ctaLabel: data.cta_label || 'Contact support',
      });

      if (Array.isArray(data.follow_up_questions) && data.follow_up_questions.length) {
        const followUps = document.createElement('div');
        followUps.className = 'flex flex-wrap gap-2';
        data.follow_up_questions.slice(0, 3).forEach((followUpQuestion) => {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'rounded-full border border-cocoa/10 bg-cream px-3 py-1.5 text-xs font-medium text-cocoa transition hover:border-caramel hover:text-caramel';
          button.textContent = followUpQuestion;
          button.addEventListener('click', () => {
            input.value = followUpQuestion;
            askQuestion(followUpQuestion);
          });
          followUps.appendChild(button);
        });
        messages.appendChild(followUps);
        messages.scrollTop = messages.scrollHeight;
      }

      setStatus(response.ok ? 'Answer ready.' : 'I found a partial answer—feel free to ask another question.', response.ok ? 'muted' : 'error');
    } catch (_error) {
      appendBubble({
        text: 'I ran into trouble reaching the support assistant just now. Please try again or contact our team directly.',
        role: 'assistant',
        meta: 'Support fallback',
        ctaUrl: '/contact/',
        ctaLabel: 'Contact Nest & Whisk',
      });
      setStatus('Something went wrong while loading the answer.', 'error');
    }
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const question = input.value;
    input.value = '';
    await askQuestion(question);
    input.focus();
  });

  starterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const question = button.textContent || '';
      input.value = question;
      askQuestion(question);
    });
  });
};

const initializeCheckoutDeliveryLookup = () => {
  const root = document.querySelector('[data-delivery-lookup]');
  if (!root) return;

  const endpoint = root.dataset.endpoint;
  const cityInput = document.querySelector('input[name="shipping_city"]');
  const postalCodeInput = document.querySelector('input[name="shipping_postal_code"]');
  const badge = root.querySelector('[data-delivery-badge]');
  const source = root.querySelector('[data-delivery-source]');
  const headline = root.querySelector('[data-delivery-headline]');
  const body = root.querySelector('[data-delivery-body]');
  const eta = root.querySelector('[data-delivery-eta]');
  const meta = root.querySelector('[data-delivery-meta]');

  if (!endpoint || !cityInput || !postalCodeInput || !badge || !source || !headline || !body || !eta || !meta) return;

  const applyTone = (status, liveEtaAvailable, isExpressZone) => {
    root.classList.remove('border-sage/30', 'bg-sage/10', 'border-cocoa/12', 'bg-white/70', 'border-caramel/20', 'bg-caramel/5');
    if (liveEtaAvailable || isExpressZone) {
      root.classList.add('border-sage/30', 'bg-sage/10');
      return;
    }
    if (['outside', 'city_conflict', 'live_unavailable'].includes(status)) {
      root.classList.add('border-cocoa/12', 'bg-white/70');
      return;
    }
    root.classList.add('border-caramel/20', 'bg-caramel/5');
  };

  const renderExperience = (data) => {
    badge.textContent = data.badge || 'Delivery guidance';
    source.textContent = data.status_note || (data.provider === 'shiprocket' ? 'Powered by Shiprocket live courier serviceability.' : 'Guided by storefront delivery rules.');
    headline.textContent = data.headline || 'Delivery guidance is loading.';
    body.textContent = data.body || '';
    eta.textContent = data.eta || '';

    if (data.provider === 'shiprocket' && data.courier_name) {
      meta.textContent = `Courier: ${data.courier_name}${data.courier_count ? ` · ${data.courier_count} option${data.courier_count === 1 ? '' : 's'} checked` : ''}`;
    } else if (data.shiprocket_available) {
      meta.textContent = 'Live ETA becomes available once a valid 6-digit postal code is entered.';
    } else {
      meta.textContent = 'Live Shiprocket ETA is optional and falls back to our built-in delivery guidance when not configured.';
    }

    applyTone(data.status, Boolean(data.live_eta_available), Boolean(data.is_express_zone));
  };

  let debounceHandle = null;
  let requestCounter = 0;

  const fetchExperience = async () => {
    const city = cityInput.value.trim();
    const postalCode = postalCodeInput.value.trim();
    const lookupId = requestCounter + 1;
    requestCounter = lookupId;

    const url = new URL(endpoint, window.location.origin);
    if (city) url.searchParams.set('city', city);
    if (postalCode) url.searchParams.set('postal_code', postalCode);

    try {
      const response = await fetch(url, { headers: { Accept: 'application/json' } });
      const data = await response.json();
      if (lookupId !== requestCounter) return;
      if (!response.ok || !data.ok) {
        throw new Error('Delivery lookup failed.');
      }
      renderExperience(data);
    } catch (_error) {
      if (lookupId !== requestCounter) return;
      renderExperience({
        badge: 'Delivery guidance',
        status: 'fallback',
        status_note: 'Live lookup temporarily unavailable.',
        headline: 'We could not refresh the live delivery estimate just now.',
        body: 'You can still continue with the checkout form and we’ll keep the delivery guidance visible.',
        eta: 'Please try the postal code again in a moment if you need a refreshed courier estimate.',
        shiprocket_available: false,
        live_eta_available: false,
        is_express_zone: false,
        provider: 'fallback',
        courier_name: '',
        courier_count: 0,
      });
    }
  };

  const scheduleLookup = () => {
    window.clearTimeout(debounceHandle);
    debounceHandle = window.setTimeout(fetchExperience, 350);
  };

  cityInput.addEventListener('input', scheduleLookup);
  cityInput.addEventListener('change', scheduleLookup);
  postalCodeInput.addEventListener('input', scheduleLookup);
  postalCodeInput.addEventListener('change', scheduleLookup);

  if (cityInput.value.trim() || postalCodeInput.value.trim()) {
    fetchExperience();
  }
};

const syncCartSnapshotFromDom = () => {
  const cartContent = document.querySelector('#cart-content');
  if (!cartContent) return;
  window.dispatchEvent(new CustomEvent('cart:updated', {
    detail: {
      itemCount: Number(cartContent.dataset.cartItemCount || 0),
      subtotal: cartContent.dataset.cartSubtotal || '0.00',
    }
  }));
};

document.addEventListener('htmx:afterSwap', (event) => {
  if (event.target && event.target.id === 'cart-content') {
    syncCartSnapshotFromDom();
  }
});

document.addEventListener('DOMContentLoaded', () => {
  syncCartSnapshotFromDom();
  initializeFaqAssistant();
  initializeCheckoutDeliveryLookup();
});

Alpine.data('buildABox', ({ target = 0 } = {}) => ({
  targetCount: Number(target) || 0,
  selectedCount: 0,
  init() {
    const variantField = this.$root.querySelector('select[name="variant"]');
    if (variantField) {
      this.targetCount = Number(variantField.options[variantField.selectedIndex]?.text.match(/\d+/)?.[0] || this.targetCount || 0);
      variantField.addEventListener('change', (event) => {
        const match = event.target.options[event.target.selectedIndex]?.text.match(/\d+/);
        this.targetCount = Number(match?.[0] || 0);
      });
    }
    this.selectedCount = this.$root.querySelectorAll('input[name="flavors"]:checked').length;
  },
  syncSelection() {
    this.selectedCount = this.$root.querySelectorAll('input[name="flavors"]:checked').length;
  },
  get isValid() {
    return this.targetCount > 0 && this.selectedCount === this.targetCount;
  },
  get progressWidth() {
    if (!this.targetCount) return 0;
    return Math.min(100, (this.selectedCount / this.targetCount) * 100);
  },
  get helperText() {
    if (!this.targetCount) return 'Choose a box size to set your target flavor count.';
    if (this.selectedCount === this.targetCount) return 'Perfect—your flavor count matches the selected box size.';
    if (this.selectedCount < this.targetCount) return `Choose ${this.targetCount - this.selectedCount} more flavor${this.targetCount - this.selectedCount === 1 ? '' : 's'}.`;
    return `Remove ${this.selectedCount - this.targetCount} flavor${this.selectedCount - this.targetCount === 1 ? '' : 's'} to match the box size.`;
  }
}));

Alpine.data('heroRotator', ({ total = 0, interval = 6400 } = {}) => ({
  active: 0,
  total: Number(total) || 0,
  interval: Number(interval) || 6400,
  timer: null,
  start() {
    if (this.total <= 1) return;
    this.stop();
    this.timer = window.setInterval(() => {
      this.next();
    }, this.interval);
  },
  stop() {
    if (this.timer) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
  },
  pause() {
    this.stop();
  },
  resume() {
    this.start();
  },
  next() {
    if (!this.total) return;
    this.active = (this.active + 1) % this.total;
  },
  prev() {
    if (!this.total) return;
    this.active = (this.active - 1 + this.total) % this.total;
  },
  goTo(index) {
    this.active = Number(index) || 0;
    this.start();
  }
}));


Alpine.data('productGallery', ({
  images = [],
  activeType = 'image',
  activeImage = '',
  activeAlt = '',
  activeVideo = '',
  activePoster = '',
  interval = 5200,
} = {}) => ({
  images: Array.isArray(images) ? images : [],
  imageIndex: 0,
  activeType,
  activeImage,
  activeAlt,
  activeVideo,
  activePoster,
  interval: Number(interval) || 5200,
  timer: null,
  init() {
    if (this.images.length) {
      const matchIndex = this.images.findIndex((item) => item.src === this.activeImage);
      this.imageIndex = matchIndex >= 0 ? matchIndex : 0;
    }
    this.startAuto();
  },
  setImageByIndex(index) {
    if (!this.images.length) return;
    const safeIndex = (Number(index) || 0) % this.images.length;
    const normalizedIndex = safeIndex < 0 ? safeIndex + this.images.length : safeIndex;
    const item = this.images[normalizedIndex];
    this.imageIndex = normalizedIndex;
    this.activeType = 'image';
    this.activeImage = item.src;
    this.activeAlt = item.alt;
  },
  setImageBySrc(src, alt) {
    const matchIndex = this.images.findIndex((item) => item.src === src);
    if (matchIndex >= 0) {
      this.imageIndex = matchIndex;
    }
    this.activeType = 'image';
    this.activeImage = src;
    this.activeAlt = alt;
  },
  startAuto() {
    if (this.images.length <= 1) return;
    this.stopAuto();
    this.timer = window.setInterval(() => {
      this.setImageByIndex(this.imageIndex + 1);
    }, this.interval);
  },
  stopAuto() {
    if (this.timer) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
  },
}));

Alpine.data('miniCart', ({ itemCount = 0, subtotal = '0.00' } = {}) => ({
  miniCartOpen: false,
  mobileNavOpen: false,
  itemCount: Number(itemCount) || 0,
  subtotal,
  init() {
    window.addEventListener('cart:updated', (event) => {
      this.itemCount = Number(event.detail?.itemCount || 0);
      this.subtotal = event.detail?.subtotal || '0.00';
    });
  },
  get formattedSubtotal() {
    return formatINR(this.subtotal);
  },
  open() {
    this.miniCartOpen = true;
    this.mobileNavOpen = false;
  },
  close() {
    this.miniCartOpen = false;
  },
  openMobileNav() {
    this.mobileNavOpen = true;
    this.miniCartOpen = false;
  },
  closeMobileNav() {
    this.mobileNavOpen = false;
  },
  closePanels() {
    this.miniCartOpen = false;
    this.mobileNavOpen = false;
  }
}));

Alpine.start();

