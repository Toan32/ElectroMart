/* ElectroMart - browser behaviour for the Storefront module */
(function () {
  'use strict';

  function getCookie(name) {
    var m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }

  function post(url, done) {
    fetch(url, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken')
      }
    })
      .then(function (r) { return r.json(); })
      .then(done)
      .catch(function () { /* ignore: leave the interface unchanged */ });
  }

  function setBadge(el, n) {
    if (!el) return;
    el.textContent = n;
    el.classList.toggle('hide', !n);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function money(n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + ' ₫';
  }

  /* ------------------------------------------------ category menu */
  var navCat = document.querySelector('.nav-cat');
  var navCatBtn = navCat && navCat.querySelector('.nav-cat-btn');
  if (navCat && navCatBtn) {
    // click keeps the list open (touch screens have no hover)
    navCatBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      navCat.classList.toggle('open');
    });
    document.addEventListener('click', function (e) {
      if (!navCat.contains(e.target)) navCat.classList.remove('open');
    });
    navCat.addEventListener('mouseleave', function () {
      navCat.classList.remove('open');
    });
  }

  /* ------------------------------------------------ search type-ahead */
  var input = document.getElementById('q');
  var box = document.getElementById('suggest');
  if (input && box) {
    var timer = null;
    input.addEventListener('input', function () {
      var q = input.value.trim();
      clearTimeout(timer);
      if (q.length < 2) { box.classList.remove('on'); return; }
      // 300ms debounce so we do not call the API on every keystroke
      timer = setTimeout(function () {
        fetch('/api/suggest/?q=' + encodeURIComponent(q))
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (!d.items.length) { box.classList.remove('on'); return; }
            box.innerHTML = d.items.map(function (i) {
              return '<a href="' + i.url + '">' +
                '<span class="sg-name">' + escapeHtml(i.name) +
                ' <span class="sg-part">' + escapeHtml(i.part_number) + '</span></span>' +
                '<span class="sg-price">' + money(i.price) + '</span></a>';
            }).join('');
            box.classList.add('on');
          });
      }, 300);
    });
    document.addEventListener('click', function (e) {
      if (!box.contains(e.target) && e.target !== input) box.classList.remove('on');
    });
  }

  /* ------------------------------------------------ compare */
  var bar = document.getElementById('cmp-bar');
  var barN = document.getElementById('cmp-bar-n');
  var cmpBadge = document.getElementById('cmp-badge');

  document.querySelectorAll('.js-compare').forEach(function (cb) {
    cb.addEventListener('change', function () {
      post('/compare/' + cb.dataset.slug + '/', function (d) {
        if (d.full) {
          cb.checked = false;
          alert('You can compare at most ' + d.limit + ' products at a time.');
          return;
        }
        cb.checked = d.added;
        setBadge(cmpBadge, d.count);
        if (barN) barN.textContent = d.count;
        if (bar) bar.classList.toggle('hide', !d.count);
      });
    });
  });

  document.querySelectorAll('.js-compare-off').forEach(function (b) {
    b.addEventListener('click', function () {
      post('/compare/' + b.dataset.slug + '/', function () { location.reload(); });
    });
  });

  /* ------------------------------------------------ wishlist */
  var wishBadge = document.getElementById('wish-badge');
  document.querySelectorAll('.js-wish').forEach(function (b) {
    b.addEventListener('click', function (e) {
      e.preventDefault();
      post('/wishlist/' + b.dataset.slug + '/', function (d) {
        b.classList.toggle('on', d.added);
        setBadge(wishBadge, d.count);
        if (window.location.pathname.indexOf('/wishlist') !== -1 && !d.added) {
          var card = b.closest('.card');
          if (card) card.remove();
          var countEl = document.querySelector('.results-head .count b');
          if (countEl) countEl.textContent = d.count;
          if (d.count === 0) window.location.reload();
        }
      });
    });
  });

  /* ------------------------------------------------ filters submit on change */
  var form = document.getElementById('filter-form');
  if (form) {
    form.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
      cb.addEventListener('change', function () { form.submit(); });
    });
  }

  /* ------------------------------------------------ client-side form validation
     Shared by every app (Storefront, Sales & Payment, Accounts, Admin): shows
     the same styled inline message for every form on the site, computed from
     whatever required/pattern/minlength/type constraints the template already
     declares, instead of each browser's own "Please fill out this field"
     bubble (wording/style differs per browser, and clashes with the red
     .form-error text already used for errors coming back from the server).
     The native bubble itself is already turned off site-wide by the small
     inline script in base.html <head> (which also runs when this file fails
     to load); the block below adds the inline .form-error message and blocks
     submit before the page's own handlers run.
     Runs on every <form> - including the GET filter/search/toolbar forms
     (product list, order tracking, admin search boxes) - because none of
     those declare any required/pattern field, so checkValidity() is always
     true for them and this is a no-op there. A form that truly wants no
     part of this (none today) can opt out with data-no-client-validate. */
  var VALIDATION_MESSAGES = {
    valueMissing: 'This field is required.',
    typeMismatch: function (f) {
      return f.type === 'email' ? 'Please enter a valid email address.' : 'Please enter a valid value.';
    },
    tooShort: function (f) { return 'Please use at least ' + f.minLength + ' characters.'; },
    tooLong: function (f) { return 'Please use no more than ' + f.maxLength + ' characters.'; },
    patternMismatch: function (f) { return f.dataset.patternMsg || 'Please match the requested format.'; },
    rangeUnderflow: function (f) { return 'Value must be at least ' + f.min + '.'; },
    rangeOverflow: function (f) { return 'Value must be at most ' + f.max + '.'; },
    badInput: 'Please enter a valid value.',
  };

  function validationMessage(field) {
    if (field.validity.customError) return field.validationMessage; // e.g. a "passwords must match" check
    for (var key in VALIDATION_MESSAGES) {
      if (field.validity[key]) {
        var m = VALIDATION_MESSAGES[key];
        return typeof m === 'function' ? m(field) : m;
      }
    }
    return field.validationMessage || 'Please check this field.';
  }

  // Reuse the message box the template already renders for this field when
  // there is one - either the .form-error convention (accounts, admin,
  // sales admin) or checkout.html's own .invalid-feedback - and only create
  // a new .form-error for forms that never had a per-field box (mock-up
  // admin forms, the review form, ...).
  function validationErrorBox(field, createIfMissing) {
    var host = field.closest('.form-group') || field.closest('td') || field.parentElement;
    var box = host && host.querySelector('.form-error, .invalid-feedback');
    if (!box && createIfMissing) {
      box = document.createElement('div');
      box.className = 'form-error';
      field.insertAdjacentElement('afterend', box);
    }
    return box;
  }

  function validateField(field) {
    if (!field.willValidate || field.type === 'radio') return true;
    var valid = field.checkValidity();
    field.classList.toggle('is-invalid', !valid);
    field.setAttribute('aria-invalid', valid ? 'false' : 'true');
    var box = validationErrorBox(field, !valid);
    if (box) box.textContent = valid ? '' : validationMessage(field);
    return valid;
  }

  function isFormField(el) {
    return !!(el && el.matches && el.matches('input, textarea, select'));
  }

  document.querySelectorAll('form').forEach(function (form) {
    if (form.dataset.noClientValidate !== undefined) return;
    form.setAttribute('novalidate', 'novalidate');

    // Delegated on the form (not bound per-field) so a row a page adds
    // later - the RFQ "+ Add row" button, an admin "+ Add variant" modal,
    // ... - is validated too, with nothing extra for that page to wire up.
    // 'focusout' is used instead of 'blur' because only focusout bubbles.
    form.addEventListener('focusout', function (e) {
      if (isFormField(e.target)) validateField(e.target);
    });
    form.addEventListener('input', function (e) {
      if (isFormField(e.target) && e.target.classList.contains('is-invalid')) validateField(e.target);
    });
    form.addEventListener('change', function (e) {
      if (isFormField(e.target) && e.target.classList.contains('is-invalid')) validateField(e.target);
    });

    form.addEventListener('submit', function (e) {
      var firstInvalid = null;
      // Queried fresh (not captured once) for the same reason: fields added
      // after page load must still be checked before the form submits.
      form.querySelectorAll('input, textarea, select').forEach(function (field) {
        var ok = validateField(field);
        if (!ok && !firstInvalid) firstInvalid = field;
      });
      if (firstInvalid) {
        e.preventDefault();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
        firstInvalid.focus();
      }
    }, true); // capture: run before any page-specific submit handler (checkout.js, cart.js, admin mock-up scripts, ...) so an invalid field always blocks them too.
  });
})();
