(() => {
  const registry = globalThis.__dcLogicFactories ||
    (globalThis.__dcLogicFactories = Object.create(null));

  // This site is static, so it cannot send mail itself. Submissions go to the
  // application's public contact endpoint, which relays them over the same
  // Resend SMTP path the product uses — see docs/EMAIL_SETUP.md.
  const API_BASE = globalThis.__JADAWIL_API_BASE__ ?? 'https://app.jadawl.site';
  const CONTACT_ENDPOINT = `${API_BASE}/api/arabase/contact/`;
  const MAILBOX = 'info@jadawl.site';

  // Everything else on a form is forwarded as a labelled detail line, so a new
  // field can be added to the markup without touching this file.
  const KNOWN_FIELDS = ['name', 'email', 'subject', 'message', 'company'];

  const isEnglish = (root) => root?.dataset.lang === 'en';

  /** Set both languages on an element so the page's toggle keeps working. */
  const bilingual = (element, ar, en, english) => {
    element.dataset.ar = ar;
    element.dataset.en = en;
    element.textContent = english ? en : ar;
    return element;
  };

  /**
   * A field a human never sees and a form-filling bot usually does.
   *
   * Moved off-screen rather than `display:none`, because the crawlers worth
   * catching skip fields that are explicitly hidden. `aria-hidden` and the
   * negative tab index keep it away from screen readers and the keyboard.
   */
  const addHoneypot = (form) => {
    if (form.querySelector('[name="company"]')) return;
    const trap = document.createElement('input');
    trap.type = 'text';
    trap.name = 'company';
    trap.tabIndex = -1;
    trap.autocomplete = 'off';
    trap.setAttribute('aria-hidden', 'true');
    trap.style.cssText =
      'position:absolute;left:-9999px;width:1px;height:1px;opacity:0';
    form.appendChild(trap);
  };

  const postContact = async (payload) => {
    const response = await fetch(CONTACT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = new Error(`Contact endpoint returned ${response.status}`);
      error.kind = response.status === 429 ? 'rate' : 'failed';
      throw error;
    }
    return response.json();
  };

  const FAILURE_TEXT = {
    rate: {
      ar: `أرسلت رسائل كثيرة خلال وقت قصير. جرّب بعد ساعة، أو راسلنا مباشرة على ${MAILBOX}`,
      en: `Too many messages in a short time. Try again in an hour, or email us directly at ${MAILBOX}`,
    },
    failed: {
      ar: `تعذّر إرسال رسالتك. راسلنا مباشرة على ${MAILBOX}`,
      en: `We could not send your message. Please email us directly at ${MAILBOX}`,
    },
  };

  /** An inline, screen-reader-announced error placed directly after the form. */
  const showFailure = (form, kind, english) => {
    const text = FAILURE_TEXT[kind] ?? FAILURE_TEXT.failed;
    let box = form.nextElementSibling;
    if (!box?.dataset.contactError) {
      box = document.createElement('p');
      box.dataset.contactError = 'true';
      box.setAttribute('role', 'alert');
      box.style.cssText =
        'margin:12px 0 0;font-size:14px;line-height:1.7;color:#C2544B';
      form.after(box);
    }
    bilingual(box, text.ar, text.en, english);
  };

  const clearFailure = (form) => {
    const box = form.nextElementSibling;
    if (box?.dataset.contactError) box.remove();
  };

  const landingFactory = (DCLogic) => class extends DCLogic {
    componentDidMount() {
      const root = document.getElementById('jadawil');
      root?.querySelector('#demo')?.remove();
      root?.querySelectorAll('a[href="#demo"]').forEach((link) => {
        link.setAttribute('href', '#contact');
      });
      root?.querySelectorAll('a[href^="Jadawil Releases"]').forEach((link) => {
        const hash = link.getAttribute('href').split('#')[1];
        link.setAttribute('href', `/releases${hash ? `#${hash}` : ''}`);
      });
      root?.querySelectorAll('form').forEach(addHoneypot);
      this.useCleanPath('/');
      if ((this.props.startLang ?? 'ar') === 'en') this.swap();
    }

    useCleanPath(path) {
      if (window.location.protocol === 'file:') return;
      const filename = decodeURIComponent(window.location.pathname).split('/').pop();
      if (filename?.startsWith('Jadawil Landing')) {
        window.history.replaceState(null, '', `${path}${window.location.hash}`);
      }
    }

    swap() {
      const root = document.getElementById('jadawil');
      if (!root) return;
      const toEn = root.dataset.lang !== 'en';
      root.querySelectorAll('[data-en]').forEach((element) => {
        if (element.dataset.ar === undefined) {
          element.dataset.ar = element.textContent;
        }
        element.textContent = toEn ? element.dataset.en : element.dataset.ar;
      });
      root.querySelectorAll('[data-en-placeholder]').forEach((element) => {
        if (element.dataset.arPlaceholder === undefined) {
          element.dataset.arPlaceholder = element.placeholder;
        }
        element.placeholder = toEn
          ? element.dataset.enPlaceholder
          : element.dataset.arPlaceholder;
      });
      root.dataset.lang = toEn ? 'en' : 'ar';
      root.dir = toEn ? 'ltr' : 'rtl';
    }

    /** Replace the form with a confirmation the visitor can actually read. */
    showSent(form, reference) {
      const english = isEnglish(document.getElementById('jadawil'));
      const panel = document.createElement('div');
      // `status` rather than `alert`: this is a confirmation, so it should be
      // announced once the screen reader finishes what it is already saying.
      panel.setAttribute('role', 'status');
      panel.setAttribute('aria-live', 'polite');
      panel.style.cssText =
        'border:1px solid #4C5158;background:#2A2B33;border-radius:12px;' +
        'padding:26px;text-align:center';

      const tick = document.createElement('div');
      tick.textContent = '✓';
      tick.setAttribute('aria-hidden', 'true');
      tick.style.cssText =
        'width:44px;height:44px;border-radius:99px;background:#8FD3AE;' +
        'color:#202128;font-size:20px;font-weight:700;display:flex;' +
        'align-items:center;justify-content:center;margin:0 auto';

      const title = document.createElement('h3');
      title.style.cssText =
        'font-size:19px;font-weight:600;color:#fff;margin:16px 0 0';
      bilingual(title, 'وصلتنا رسالتك', 'Your message has been sent', english);

      const detail = document.createElement('p');
      detail.style.cssText =
        'font-size:15px;line-height:1.7;color:#DBDCD9;margin:10px 0 0';
      bilingual(
        detail,
        `رقم المراسلة ${reference} — نرد عليك خلال يوم عمل واحد.`,
        `Reference ${reference} — we will reply within one business day.`,
        english,
      );

      panel.append(tick, title, detail);
      clearFailure(form);
      form.replaceWith(panel);
    }

    async submitEmail(event) {
      event.preventDefault();
      const form = event.currentTarget;
      const english = isEnglish(document.getElementById('jadawil'));
      const button = form.querySelector('button[type="submit"]');
      const buttonLabel = button?.textContent;

      // Anything the endpoint does not name becomes a labelled detail line.
      const payload = { source: 'landing', details: {} };
      for (const [name, value] of new FormData(form).entries()) {
        if (KNOWN_FIELDS.includes(name)) payload[name] = value;
        else payload.details[name] = value;
      }
      payload.subject ||= form.dataset.emailSubject || 'Jadawil website message';

      clearFailure(form);
      if (button) {
        button.disabled = true;
        button.textContent = english ? 'Sending…' : 'جارٍ الإرسال…';
      }

      try {
        const { reference } = await postContact(payload);
        this.showSent(form, reference);
      } catch (error) {
        showFailure(form, error.kind, english);
        if (button) {
          button.disabled = false;
          button.textContent = buttonLabel;
        }
      }
    }

    renderVals() {
      return {
        priceLabel: (this.props.price ?? 59) + ' ريال/مستخدم/شهريًا',
        toggleLang: () => this.swap(),
        submitEmail: (event) => this.submitEmail(event),
      };
    }
  };

  const releasesFactory = (DCLogic) => class extends DCLogic {
    state = {
      kind: 'bug',
      severity: 'medium',
      email: '',
      where: '',
      title: '',
      steps: '',
      submitted: false,
      ticket: '',
      reports: [
        {
          id: 'JD-1482',
          title: 'تصدير CSV يضيف علامة BOM في أول عمود',
          status: 'progress',
        },
        {
          id: 'JD-1476',
          title: 'لوحة المتابعة ما تحدّث المجموع بعد حذف صف',
          status: 'open',
        },
        {
          id: 'JD-1461',
          title: 'حقل رقم الجوال يرفض الصيغة الدولية +9665',
          status: 'fixed',
        },
      ],
    };

    componentDidMount() {
      const root = document.getElementById('jadawil-rel');
      root?.querySelectorAll('a[href^="Jadawil Landing"]').forEach((link) => {
        const hash = link.getAttribute('href').split('#')[1];
        link.setAttribute('href', `/${hash ? `#${hash}` : ''}`);
      });
      root?.querySelectorAll('form').forEach(addHoneypot);
      if (window.location.protocol === 'file:') return;
      const filename = decodeURIComponent(window.location.pathname).split('/').pop();
      if (filename?.startsWith('Jadawil Releases')) {
        window.history.replaceState(null, '', `/releases${window.location.hash}`);
      }
    }

    statusMeta(status) {
      const english = document.getElementById('jadawil-rel')?.dataset.lang === 'en';
      if (status === 'fixed') {
        return {
          label: english ? 'Fixed' : 'تم الإصلاح',
          chipBg: '#EAF3EE',
          chipFg: '#1E6D4C',
        };
      }
      if (status === 'progress') {
        return {
          label: english ? 'In progress' : 'قيد المعالجة',
          chipBg: '#FAEACF',
          chipFg: '#8E6520',
        };
      }
      return {
        label: english ? 'Open' : 'مستلَم',
        chipBg: '#EEF2F7',
        chipFg: '#3D5A80',
      };
    }

    chip(active) {
      return active
        ? { bg: '#1E6D4C', fg: '#ffffff', border: '#1E6D4C' }
        : { bg: '#ffffff', fg: '#4C5158', border: '#E2E2DD' };
    }

    swap() {
      const root = document.getElementById('jadawil-rel');
      if (!root) return;
      const toEn = root.dataset.lang !== 'en';
      root.querySelectorAll('[data-en]').forEach((element) => {
        if (element.dataset.ar === undefined) {
          element.dataset.ar = element.textContent;
        }
        element.textContent = toEn ? element.dataset.en : element.dataset.ar;
      });
      root.querySelectorAll('[data-en-placeholder]').forEach((element) => {
        if (element.dataset.arPlaceholder === undefined) {
          element.dataset.arPlaceholder = element.placeholder;
        }
        element.placeholder = toEn
          ? element.dataset.enPlaceholder
          : element.dataset.arPlaceholder;
      });
      root.dataset.lang = toEn ? 'en' : 'ar';
      root.dir = toEn ? 'ltr' : 'rtl';
      this.forceUpdate();
    }

    async sendReport(event) {
      event.preventDefault();
      const form = event.currentTarget;
      const english = isEnglish(document.getElementById('jadawil-rel'));
      const button = form.querySelector('button[type="submit"]');
      const buttonLabel = button?.textContent;

      clearFailure(form);
      if (button) {
        button.disabled = true;
        button.textContent = english ? 'Sending…' : 'جارٍ الإرسال…';
      }

      try {
        const { reference } = await postContact({
          source: 'releases',
          email: this.state.email,
          subject: this.state.title || 'Bug report',
          message: this.state.steps,
          // This form builds its payload from state rather than FormData, so
          // the trap has to be read off the DOM. It reads empty when a
          // re-render has dropped it, which is a normal submission.
          company: form.querySelector('[name="company"]')?.value ?? '',
          details: {
            'Report type': this.state.kind,
            Severity: this.state.severity,
            Where: this.state.where,
            Version: 'v0.9.4',
          },
        });
        // The reference now comes from the server and matches the email's
        // subject line, so quoting it back to us actually finds the message.
        this.setState({ submitted: true, ticket: reference });
      } catch (error) {
        showFailure(form, error.kind, english);
        if (button) {
          button.disabled = false;
          button.textContent = buttonLabel;
        }
      }
    }

    renderVals() {
      const isEnglish = document.getElementById('jadawil-rel')?.dataset.lang === 'en';
      const kindLabels = {
        bug: isEnglish ? 'Bug' : 'خلل',
        suggestion: isEnglish ? 'Suggestion' : 'اقتراح',
        question: isEnglish ? 'Question' : 'استفسار',
      };
      const severityLabels = {
        low: isEnglish ? 'Minor' : 'بسيط',
        medium: isEnglish ? 'Affects my work' : 'يعطّل شغلي',
        high: isEnglish ? 'Blocking' : 'موقف الشغل تمامًا',
      };
      return {
        reports: this.state.reports.map((report) => ({
          ...report,
          statusLabel: this.statusMeta(report.status).label,
          chipBg: this.statusMeta(report.status).chipBg,
          chipFg: this.statusMeta(report.status).chipFg,
        })),
        fixedCount: isEnglish ? '17' : '١٧',
        kinds: Object.keys(kindLabels).map((kind) => ({
          label: kindLabels[kind],
          ...this.chip(this.state.kind === kind),
          pick: () => this.setState({ kind }),
        })),
        severities: Object.keys(severityLabels).map((severity) => ({
          label: severityLabels[severity],
          ...this.chip(this.state.severity === severity),
          pick: () => this.setState({ severity }),
        })),
        email: this.state.email,
        where: this.state.where,
        title: this.state.title,
        steps: this.state.steps,
        onEmail: (event) => this.setState({ email: event.target.value }),
        onWhere: (event) => this.setState({ where: event.target.value }),
        onTitle: (event) => this.setState({ title: event.target.value }),
        onSteps: (event) => this.setState({ steps: event.target.value }),
        sendReport: (event) => this.sendReport(event),
        submitted: this.state.submitted,
        notSubmitted: !this.state.submitted,
        successLine: isEnglish
          ? `Report number ${this.state.ticket} — we will email you an update within 24 hours.`
          : `رقم البلاغ ${this.state.ticket} — يوصلك تحديث على بريدك خلال ٢٤ ساعة.`,
        reset: () => this.setState({
          submitted: false,
          title: '',
          steps: '',
          where: '',
        }),
        toggleLang: () => this.swap(),
      };
    }
  };

  registry['Jadawil Landing'] = landingFactory;
  registry['Jadawil Landing (standalone)'] = landingFactory;
  registry['Jadawil Releases'] = releasesFactory;
  registry['Jadawil Releases (standalone)'] = releasesFactory;
})();
