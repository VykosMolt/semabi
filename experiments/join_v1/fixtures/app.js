/* Local presentation only. Learners receive public observations and actions. */
const root = document.querySelector('#console');
let state;
let queue = Promise.resolve();
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function choices(records, selected) {
  return records.map(record => `<option value="${esc(record.name)}"${record.name === selected ? ' selected' : ''}>${esc(record.name)}</option>`).join('');
}

function render() {
  root.innerHTML = `<header><div><h1>Patch console</h1><p>Choose a receiver, then transmit from a transmitter.</p></div><div class="toolbar"><button data-op="clear_message">Clear message</button><button data-op="reset">Reset console</button></div></header>
    <section aria-label="Transmitters"><h2>Transmitters</h2><div class="members transmitters">${state.transmitters.map(record => `<section role="group" aria-label="${esc(record.name)}" class="member"><h3>${esc(record.name)}</h3><button data-op="transmit" data-name="${esc(record.name)}"${state.selected_receiver === null ? ' disabled' : ''}>Transmit</button></section>`).join('')}</div></section>
    <section aria-label="Receivers"><h2>Receivers</h2><div class="members receivers">${state.receivers.map(record => `<section role="group" aria-label="${esc(record.name)}" class="member"><h3>${esc(record.name)}</h3><label><input type="radio" name="receiver" aria-label="Select receiver" data-receiver="${esc(record.name)}"${record.name === state.selected_receiver ? ' checked' : ''}>Select receiver</label><p class="receipt">Received: ${record.received ? 'yes' : 'no'}</p><button data-op="clear_receipt" data-name="${esc(record.name)}">Clear receipt</button></section>`).join('')}</div></section>
    <section aria-label="Patch leads"><h2>Patch leads</h2><div class="members patches">${state.patches.map(record => `<section role="group" aria-label="${esc(record.name)}" class="member"><h3>${esc(record.name)}</h3><div class="endpoints"><label>Transmitter<select aria-label="Transmitter" data-patch="${esc(record.name)}" data-endpoint="transmitter">${choices(state.transmitters, record.transmitter)}</select></label><label>Receiver<select aria-label="Receiver" data-patch="${esc(record.name)}" data-endpoint="receiver">${choices(state.receivers, record.receiver)}</select></label></div></section>`).join('')}</div></section>
    ${state.notice === null ? '' : `<p role="status" class="message">Transmission ${state.notice.delivered ? 'delivered' : 'blocked'}: ${esc(state.notice.transmitter)} → ${esc(state.notice.receiver)}.</p>`}`;
  root.setAttribute('aria-busy', 'false');
}

function send(action) {
  root.setAttribute('aria-busy', 'true');
  queue = queue.then(async () => {
    if (action.op === 'reset') {
      const reset = await fetch('/reset', {method: 'POST'});
      if (!reset.ok) throw new Error('Reset unavailable');
      const response = await fetch('/api/state');
      if (!response.ok) throw new Error('State unavailable');
      state = await response.json();
    } else {
      const response = await fetch('/api/action', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(action)});
      if (!response.ok) throw new Error('Action unavailable');
      state = await response.json();
    }
    render();
  }).catch(error => {
    root.innerHTML = `<p role="alert">${esc(error.message)}</p>`;
    root.setAttribute('aria-busy', 'false');
  });
  return queue;
}

root.addEventListener('click', event => {
  const target = event.target.closest('[data-op]');
  if (!target) return;
  const op = target.dataset.op;
  if (op === 'transmit') send({op, transmitter: target.dataset.name});
  else if (op === 'clear_receipt') send({op, receiver: target.dataset.name});
  else send({op});
});
root.addEventListener('change', event => {
  const target = event.target;
  if (target.matches('[data-receiver]')) send({op: 'select_receiver', receiver: target.dataset.receiver});
  if (target.matches('[data-patch]')) send({op: 'set_endpoint', patch: target.dataset.patch, endpoint: target.dataset.endpoint, value: target.value});
});
fetch('/api/state').then(response => {
  if (!response.ok) throw new Error('State unavailable');
  return response.json();
}).then(value => { state = value; render(); }).catch(error => {
  root.innerHTML = `<p role="alert">${esc(error.message)}</p>`;
  root.setAttribute('aria-busy', 'false');
});
