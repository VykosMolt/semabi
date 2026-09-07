/* The learner is restricted to accessibility snapshots and public actions. */
const root = document.querySelector('#app');
let state;
let queue = Promise.resolve();
const escapeText = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const button = (name, op, target = null, disabled = false) => `<button data-op="${op}"${target === null ? '' : ` data-name="${escapeText(target)}"`}${disabled ? ' disabled' : ''}>${escapeText(name)}</button>`;
const job = () => state.jobs.find(item => item.name === state.selected_job);
const resource = () => state.resources.find(item => item.name === state.selected_resource);
const result = () => state.result ? `<p role="status" data-attempt-result>${escapeText(state.result)}</p>` : '';

function detail(dispatch) {
  const selected = resource();
  const quantityLabel = dispatch ? 'Packed weight (kg)' : 'Required span (cm)';
  const capacityLabel = dispatch ? 'Payload limit' : 'Work span';
  return `${button(dispatch ? 'Back to dispatch board' : 'Return to registry','back')}<h1>${escapeText(job().name)}</h1>
    <p>${escapeText(job().note)}</p><section aria-label="${dispatch ? 'Packing details' : 'Job requirements'}"><h2>${dispatch ? 'Packing details' : 'Job requirements'}</h2>
    <label>${quantityLabel}<input type="number" min="0" step="any" aria-label="${quantityLabel}" value="${escapeText(job().quantity)}" data-quantity></label></section>
    <section aria-label="${dispatch ? 'Assigned carrier' : 'Assigned station'}"><h2>${dispatch ? 'Assigned carrier' : 'Assigned station'}</h2>
    ${selected ? `<dl><dt>${dispatch ? 'Carrier' : 'Station'}</dt><dd>${escapeText(selected.name)}</dd><dt>${capacityLabel}</dt><dd>${selected.capacity} ${dispatch ? 'kg' : 'cm'}</dd></dl>` : `<p>${dispatch ? 'No carrier selected' : 'No station attached'}</p>`}
    ${button(dispatch ? 'Choose carrier' : 'Browse stations','choose')}</section>${button(dispatch ? 'Check dispatch' : 'Start job','attempt')}${result()}
    <aside aria-label="${dispatch ? 'Seal review' : 'Release review'}"><h2>${dispatch ? 'Seal review' : 'Release review'}</h2><p>Recorded review measurements are read-only.</p>
    <dl><dt>${dispatch ? 'Recorded seal load' : 'Recorded clearance span'}</dt><dd>${job().review_load} ${dispatch ? 'kg' : 'cm'}</dd><dt>${dispatch ? 'Seal rating' : 'Release limit'}</dt><dd>${job().review_limit} ${dispatch ? 'kg' : 'cm'}</dd></dl>
    ${button(dispatch ? 'Review seal' : 'Request release','review',null,state.review_done)}${state.review_result ? `<p role="status">${escapeText(state.review_result)}</p>` : ''}</aside>`;
}

function chooser(dispatch) {
  if (dispatch) return `<section role="dialog" aria-label="Choose a carrier"><h1>Choose a carrier</h1><div class="cards">${state.resources.map(r => `<article><h2>${escapeText(r.name)}</h2><p>Payload limit: ${r.capacity} kg</p>${button(`Select ${r.name}`,'select',r.name)}</article>`).join('')}</div></section>`;
  return `<h1>Station chooser</h1><table><caption>Available stations</caption><thead><tr><th scope="col">Selection</th><th scope="col">Station</th><th scope="col">Work span</th></tr></thead><tbody>${state.resources.map(r => `<tr><td><input type="radio" name="station" aria-label="Select ${escapeText(r.name)}" data-resource="${escapeText(r.name)}"${state.pending_resource === r.name ? ' checked' : ''}></td><th scope="row">${escapeText(r.name)}</th><td>${r.capacity} cm</td></tr>`).join('')}</tbody></table>${button('Attach station','attach',null,!state.pending_resource)}`;
}

function reservoir() {
  if (state.view === 'amount') return `<p class="step">Watering request · Step 1 of 3</p><h1>Orchard watering</h1><p>West orchard</p><label>Water requested (L)<input type="number" min="0" step="any" aria-label="Water requested (L)" value="${escapeText(job().quantity)}" data-quantity></label>${button('Continue to water sources','continue')}`;
  if (state.view === 'source') return `<p class="step">Watering request · Step 2 of 3</p><h1>Choose a water source</h1><fieldset><legend>Stored water</legend>${state.resources.map(r => `<label><input type="radio" name="source" aria-label="Use ${escapeText(r.name)}" data-resource="${escapeText(r.name)}"${state.pending_resource === r.name ? ' checked' : ''}>${escapeText(r.name)} — Water available: ${r.capacity} L</label>`).join('')}</fieldset>${button('Review watering request','continue',null,!state.pending_resource)}`;
  return `<p class="step">Watering request · Step 3 of 3</p><h1>Review watering request</h1><dl><dt>Water requested</dt><dd>${job().quantity} L</dd><dt>Water source</dt><dd>${escapeText(resource().name)}</dd><dt>Water available</dt><dd>${resource().capacity} L</dd></dl>${button('Edit watering request','edit')}${button('Schedule watering','attempt')}${result()}<aside><h2>Water access review</h2><p>Recorded review measurements are read-only.</p><dl><dt>Recorded draw</dt><dd>${resource().review_load} L</dd><dt>Access allowance</dt><dd>${resource().review_limit} L</dd></dl>${button('Review water access','review',null,state.review_done)}${state.review_result ? `<p role="status">${escapeText(state.review_result)}</p>` : ''}</aside>`;
}

function render() {
  const dispatch = state.fixture === 'dispatch';
  let markup;
  if (state.fixture === 'reservoir') markup = reservoir();
  else if (state.view === 'board') markup = `<h1>Dispatch board</h1><p>Choose a run to prepare its shipment.</p><div class="cards">${state.jobs.map(j => `<article><h2>${escapeText(j.name)}</h2><p>Destination: ${escapeText(j.note)}</p><p>Packed weight: ${j.quantity} kg</p>${button(`Open ${j.name}`,'open',j.name)}</article>`).join('')}</div>`;
  else if (state.view === 'registry') markup = `<h1>Production registry</h1><p>Open a category to find a job.</p><ul class="tree">${[...new Set(state.jobs.map(j => j.note))].map(category => `<li>${button(`${state.expanded.includes(category) ? 'Collapse' : 'Expand'} ${category}`,'expand',category)}${state.expanded.includes(category) ? `<ul>${state.jobs.filter(j => j.note === category).map(j => `<li>${button(`Open ${j.name}`,'open',j.name)}<span>Required span: ${j.quantity} cm</span></li>`).join('')}</ul>` : ''}</li>`).join('')}</ul>`;
  else if (state.view === 'chooser') markup = chooser(dispatch);
  else markup = detail(dispatch);
  root.innerHTML = markup;
  root.setAttribute('aria-busy','false');
  document.title = dispatch ? 'Packing desk' : state.fixture === 'workshop' ? 'Workshop registry' : 'Watering console';
}

function send(action, redraw = true) {
  root.setAttribute('aria-busy','true');
  queue = queue.then(async () => {
    const response = await fetch('/api/action', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(action)});
    if (!response.ok) throw new Error(`Action failed: ${response.status}`);
    state = await response.json();
    if (redraw) render(); else {
      root.querySelectorAll('[data-attempt-result]').forEach(node => node.remove());
      root.setAttribute('aria-busy','false');
    }
  }).catch(error => { root.innerHTML = `<p role="alert">${escapeText(error.message)}</p>`; root.setAttribute('aria-busy','false'); });
  return queue;
}

root.addEventListener('click', event => {
  const target = event.target.closest('[data-op]');
  if (target) send({op:target.dataset.op,...(target.dataset.name ? {name:target.dataset.name} : {})});
});
root.addEventListener('change', event => {
  if (event.target.matches('[data-resource]')) send({op:'select',name:event.target.dataset.resource});
});
root.addEventListener('input', event => {
  if (event.target.matches('[data-quantity]')) send({op:'quantity',value:event.target.value},false);
});
fetch(`/api/state?fixture=${encodeURIComponent(location.pathname.slice(1))}`).then(response => response.json()).then(value => { state=value; render(); });
