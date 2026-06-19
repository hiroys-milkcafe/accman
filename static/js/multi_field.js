function addRow(containerId, attrName, attrType) {
  var container = document.getElementById(containerId);
  var row = document.createElement('div');
  row.className = 'multi-row';
  var inputType = attrType === 'number' ? 'number' : 'text';
  row.innerHTML =
    '<input type="' + inputType + '" name="' + attrName + '">' +
    '<button type="button" class="btn-sm" onclick="removeRow(this)">－</button>';
  container.appendChild(row);
}

function removeRow(btn) {
  var row = btn.parentElement;
  var container = row.parentElement;
  if (container.querySelectorAll('.multi-row').length > 1) {
    row.remove();
  }
}

/* ---- パスワード変更モーダル ---- */
var _pwAttr = null;

function openPasswordModal(attrName, label) {
  _pwAttr = attrName;
  document.getElementById('modal-pw-title').textContent = label + 'の変更';
  document.getElementById('modal-pw-input').value = '';
  document.getElementById('password-modal').style.display = 'flex';
  document.getElementById('modal-pw-input').focus();
}

function closePasswordModal() {
  document.getElementById('password-modal').style.display = 'none';
  _pwAttr = null;
}

function confirmPassword() {
  var pw = document.getElementById('modal-pw-input').value;
  if (!pw) return;
  document.getElementById('hidden-pw-' + _pwAttr).value = pw;
  document.getElementById('pw-badge-' + _pwAttr).style.display = 'inline';
  closePasswordModal();
}
