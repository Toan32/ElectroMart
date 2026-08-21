/* ElectroMart - Accounts & B2B module JS (Loc).
   GUI-only behaviour for the mock-ups built in Viec 6 (CV30): no fetch/API
   calls yet, those are wired up when the real views (CV58, CV60, CV62) are
   written in GD5. Every function below checks the element exists first, so
   this single file can be loaded on every accounts/ page without errors. */

document.addEventListener('DOMContentLoaded', function () {
  initAccountTypeToggle();
  initPasswordStrength();
  initAvatarPreview();
  initRfqRows();
  initBomDropZone();
});

/* ---- register.html: show Company name + Tax code only for Wholesale ---- */
function initAccountTypeToggle() {
  var radios = document.querySelectorAll('input[name="account_type"]');
  var companyBox = document.getElementById('company-fields');
  if (!radios.length || !companyBox) return;

  function sync() {
    var picked = document.querySelector('input[name="account_type"]:checked');
    var isWholesale = picked && picked.value === 'wholesale';
    companyBox.classList.toggle('hide', !isWholesale);
    companyBox.querySelectorAll('input').forEach(function (el) {
      el.required = isWholesale;
    });
  }
  radios.forEach(function (r) { r.addEventListener('change', sync); });
  sync();
}

/* ---- register.html / change_password.html: simple strength meter ---- */
function initPasswordStrength() {
  var input = document.getElementById('id_password');
  var bar = document.getElementById('pwd-strength-bar');
  var label = document.getElementById('pwd-strength-label');
  if (!input || !bar || !label) return;

  var levels = [
    { min: 0, text: 'Too weak', color: '#e30019', pct: 20 },
    { min: 2, text: 'Weak', color: '#e39b00', pct: 45 },
    { min: 3, text: 'Medium', color: '#e39b00', pct: 65 },
    { min: 4, text: 'Strong', color: '#0a8a3c', pct: 100 },
  ];

  input.addEventListener('input', function () {
    var v = input.value;
    var score = 0;
    if (v.length >= 8) score++;
    if (/[A-Z]/.test(v)) score++;
    if (/[0-9]/.test(v)) score++;
    if (/[^A-Za-z0-9]/.test(v)) score++;

    var level = levels[0];
    for (var i = levels.length - 1; i >= 0; i--) {
      if (score >= levels[i].min) { level = levels[i]; break; }
    }
    bar.style.width = (v ? level.pct : 0) + '%';
    bar.style.background = level.color;
    label.textContent = v ? level.text : '';
  });
}

/* ---- edit_profile.html: preview the picked avatar before it is saved ---- */
function initAvatarPreview() {
  var input = document.getElementById('id_avatar');
  var img = document.getElementById('avatar-preview');
  if (!input || !img) return;

  input.addEventListener('change', function () {
    var file = input.files && input.files[0];
    if (!file) return;

    var MAX_BYTES = 2 * 1024 * 1024; // 2MB, matches Viec 11 (CV60) rule
    var okType = file.type === 'image/jpeg' || file.type === 'image/png';
    var errBox = document.getElementById('avatar-error');
    if (errBox) errBox.textContent = '';

    if (!okType) {
      if (errBox) errBox.textContent = 'Only JPG or PNG images are accepted.';
      input.value = '';
      return;
    }
    if (file.size > MAX_BYTES) {
      if (errBox) errBox.textContent = 'Image must be 2MB or smaller.';
      input.value = '';
      return;
    }
    img.src = URL.createObjectURL(file);
  });
}

/* ---- rfq_form.html: add another component row to the RFQ table ---- */
function initRfqRows() {
  var addBtn = document.getElementById('rfq-add-row');
  var body = document.getElementById('rfq-rows');
  if (!addBtn || !body) return;

  addBtn.addEventListener('click', function () {
    var row = body.rows[0].cloneNode(true);
    row.querySelectorAll('input').forEach(function (el) { el.value = ''; });
    body.appendChild(row);
  });

  // Delegate delete-row clicks so rows added later work too.
  body.addEventListener('click', function (e) {
    if (e.target.matches('.rfq-del-row') && body.rows.length > 1) {
      e.target.closest('tr').remove();
    }
  });
}

/* ---- rfq_form.html: drag-and-drop visual feedback for the BOM file ---- */
function initBomDropZone() {
  var zone = document.getElementById('bom-drop');
  var input = document.getElementById('id_bom_file');
  var nameLabel = document.getElementById('bom-filename');
  if (!zone || !input) return;

  ['dragenter', 'dragover'].forEach(function (evt) {
    zone.addEventListener(evt, function (e) {
      e.preventDefault();
      zone.classList.add('drag-over');
    });
  });
  ['dragleave', 'drop'].forEach(function (evt) {
    zone.addEventListener(evt, function (e) {
      e.preventDefault();
      zone.classList.remove('drag-over');
    });
  });
  zone.addEventListener('drop', function (e) {
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      if (nameLabel) nameLabel.textContent = e.dataTransfer.files[0].name;
    }
  });
  zone.addEventListener('click', function () { input.click(); });
  input.addEventListener('change', function () {
    if (nameLabel && input.files[0]) nameLabel.textContent = input.files[0].name;
  });
}
