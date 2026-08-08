(() => {
  const registry = globalThis.__dcLogicFactories ||
    (globalThis.__dcLogicFactories = Object.create(null));

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

    submitEmail(event) {
      event.preventDefault();
      const form = event.currentTarget;
      const fields = Array.from(new FormData(form).entries());
      const body = fields
        .map(([name, value]) => `${name}: ${value}`)
        .join('\n');
      const subject = form.dataset.emailSubject || 'Jadawil website message';
      window.location.href = `mailto:info@jadawl.site?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
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

    submit() {
      const ticket = 'JD-' + String(Date.now()).slice(-6);
      this.setState({ submitted: true, ticket });
    }

    sendReport(event) {
      event.preventDefault();
      const subject = `[Jadawil] ${this.state.title || 'Bug report'}`;
      const body = [
        `Report type: ${this.state.kind}`,
        `Severity: ${this.state.severity}`,
        `Work email: ${this.state.email}`,
        `Where: ${this.state.where}`,
        `Title: ${this.state.title}`,
        `Steps: ${this.state.steps}`,
        'Version: v0.9.4',
      ].join('\n');
      this.submit();
      window.location.href = `mailto:info@jadawl.site?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
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
