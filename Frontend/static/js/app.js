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
})();
