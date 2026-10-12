'use strict';
const byId = id => document.getElementById(id);
const euro = value => value == null ? 'Missing' : new Intl.NumberFormat('en-IE', {style:'currency',currency:'EUR',maximumFractionDigits:0}).format(Number(value));
const percent = value => value == null ? 'Undefined' : `${(value * 100).toFixed(1)}%`;
const date = value => new Date(value).toLocaleString('en-GB', {timeZone:'UTC'}) + ' UTC';
async function read(path) {const response = await fetch(path);if(!response.ok) throw new Error(`Request failed (${response.status})`);return response.json();}
function cell(row, value) {const element = document.createElement('td');element.textContent=value;row.append(element);}
function tableRows(id, rows) {byId(id).replaceChildren(...rows.map(values => {const row=document.createElement('tr');values.forEach(value=>cell(row,value));return row;}));}
async function search(event) {
  event?.preventDefault();const data=new FormData(byId('search'));const params=new URLSearchParams();
  for(const [key,value] of data) if(value && key!=='allow_cross_microzone') params.set(key,value);
  params.set('allow_cross_microzone', data.has('allow_cross_microzone') ? 'true' : 'false');
  byId('search-status').textContent='Searching…';
  try {const result=await read(`/api/v1/comparables?${params}`);
    byId('search-status').textContent=`${result.comparable_listing_count} inferred properties at ${result.search_radius_used_m}m. Mean asking price ${euro(result.asking_price_statistics_eur.mean)}. Origin: ${result.origin_microzone ?? 'outside demo zones'}. Zone crossing: ${result.cross_microzone_expansion ? 'yes' : 'no'}. Accuracy limit: ${result.coordinate_accuracy_limit_m}m.${result.minimum_met ? '' : ' Minimum requested count was not reached.'}`;
    tableRows('comparables',result.items.map(item=>[`${item.municipality} / ${item.address ?? 'Address missing'}`,euro(item.asking_price_eur),`${item.area_sqm} m²`,`${item.distance_m}m / ±${item.coordinate_accuracy_m}m`,percent(item.deduplication_confidence)]));
  } catch(error) {byId('search-status').textContent=error.message;}
}
async function history(id) {
  byId('history').textContent='Loading history…';
  try {const result=await read(`/api/v1/listings/${id}/history`);
    const lines=[`Synthetic advertisement ${id}`,`Transaction status: ${result.transaction_status}`,'','ASKING-PRICE HISTORY'];
    for(const price of result.asking_price_history) lines.push(`${date(price.observed_at)}  ${price.event_type}: ${euro(price.previous_price_eur)} → ${euro(price.asking_price_eur)}`);
    lines.push('','AVAILABILITY OBSERVATIONS');for(const observation of result.observations) lines.push(`${date(observation.observed_at)}  ${observation.availability}${observation.inferred ? ' (inferred absence)' : ''}`);
    byId('history').textContent=lines.join('\n');
  }catch(error){byId('history').textContent=error.message;}
}
async function initialize() {
  try {const [quality,inventory,runs]=await Promise.all([read('/api/v1/quality/summary'),read('/api/v1/properties?limit=8'),read('/api/v1/ingestion/runs?limit=14')]);
    const stats=[['Distinct advertisements',quality.distinct_source_advertisements],['Inferred properties',quality.unique_deduplicated_properties],['Active advertisements',quality.active_advertisements],['Asking-price changes',quality.price_change_events],['Removed advertisements',quality.removed_advertisements],['Matching precision',percent(quality.deduplication.precision)],['Matching recall',percent(quality.deduplication.recall)],['Simulated cost / 1,000 usable',euro(quality.costs.cost_per_1000_usable)]];
    byId('stats').replaceChildren(...stats.map(([label,value])=>{const card=document.createElement('div');card.className='stat';const strong=document.createElement('strong');strong.textContent=value;const span=document.createElement('span');span.textContent=label;card.append(strong,span);return card;}));
    byId('quality-note').textContent=`${quality.validation_label}. ${quality.alerts.length} local quality alerts. Freshness is measured against simulated observations.`;
    byId('quality').textContent=JSON.stringify({missing_fields:quality.missing_field_percentages,coordinate_accuracy:quality.coordinate_accuracy_distribution,deduplication:quality.deduplication,costs:quality.costs,alerts:quality.alerts},null,2);
    byId('inventory').replaceChildren(...inventory.items.map(item=>{const button=document.createElement('button');button.type='button';const listing=item.representative_listing;button.textContent=`${listing.municipality} · ${listing.original_source_id.trim()} · ${euro(listing.asking_price_eur)}`;button.addEventListener('click',()=>history(listing.id));return button;}));
    tableRows('runs',runs.items.map(run=>[date(run.observed_at),run.status,`${run.stats.raw_records} / ${run.stats.accepted}`,run.stats.price_changes,run.stats.inferred_removals]));
    byId('status').textContent='Synthetic inventory loaded. Read-only demonstration.';await search();
  }catch(error){byId('status').textContent=error.message;byId('status').className='error';}
}
byId('search').addEventListener('submit',search);initialize();
