// k6 load model for Online Boutique. Rerun: PROFILE=baseline k6 run perf/load.js
// All knobs are env vars so another team can retarget/rescale without editing code.
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

const BASE   = __ENV.BASE_URL || 'http://localhost:8080';
const PROFILE = __ENV.PROFILE || 'baseline';
// Journey mix (percent). Rationale in perf/slis.md: typical e-commerce funnel,
// ~60% browse only, ~30% add to cart and abandon, ~10% complete checkout.
const MIX_BROWSE = +(__ENV.MIX_BROWSE || 60);
const MIX_CART   = +(__ENV.MIX_CART   || 30);   // remainder (100 - browse - cart) = checkout
const THINK = +(__ENV.THINK_SECONDS || 1);     // average think time between steps
const RATE  = +(__ENV.RATE || 20);              // baseline iterations/s (arrival rate)

const PRODUCTS = new SharedArray('p', () => ['OLJCESPC7Z','66VCHSJNUP','1YMWWN1N4O','L9ECAV7KIM','2ZYFJ3GM2N','0PUK6V6EV0','LS4PSXUNUM','9SIQT8TOJO','6E92ZMYYFZ']);
const CURRENCIES = ['USD','EUR','CAD','JPY','GBP','TRY'];

const checkoutOK = new Rate('checkout_success');
const checkoutDur = new Trend('checkout_duration', true);
const browseDur = new Trend('browse_duration', true);
const journeys = new Counter('journeys');

const profiles = {
  baseline: { executor: 'constant-arrival-rate', rate: RATE, timeUnit: '1s', duration: __ENV.DURATION || '5m', preAllocatedVUs: 50, maxVUs: 500 },
  // Ramp to find the knee: step the arrival rate until SLIs break.
  // RAMP_RATES (comma list of it/s steps), RAMP_STEP (per-step duration), MAX_VUS (cap; each VU costs Mac RAM)
  ramp: { executor: 'ramping-arrival-rate', startRate: 5, timeUnit: '1s', preAllocatedVUs: 100, maxVUs: +(__ENV.MAX_VUS || 600),
          stages: (__ENV.RAMP_RATES || '5,10,20,30,40,60,80,100').split(',').map(r => ({ target: +r, duration: __ENV.RAMP_STEP || '2m' })) },
  spike: { executor: 'ramping-arrival-rate', startRate: RATE, timeUnit: '1s', preAllocatedVUs: 100, maxVUs: +(__ENV.MAX_VUS || 600),
           stages: [{target: RATE, duration: '1m'}, {target: RATE*5, duration: '10s'}, {target: RATE*5, duration: __ENV.SPIKE_HOLD || '1m'},
                    {target: RATE, duration: '10s'}, {target: RATE, duration: __ENV.SPIKE_TAIL || '90s'}] },
  soak: { executor: 'constant-arrival-rate', rate: Math.round(RATE*0.7), timeUnit: '1s', duration: __ENV.DURATION || '30m', preAllocatedVUs: 50, maxVUs: 500 },
  // steady load held while a chaos experiment runs (see chaos/gate.sh)
  chaos: { executor: 'constant-arrival-rate', rate: RATE, timeUnit: '1s', duration: __ENV.DURATION || '4m', preAllocatedVUs: 50, maxVUs: 500 },
  smoke: { executor: 'constant-arrival-rate', rate: 2, timeUnit: '1s', duration: '30s', preAllocatedVUs: 5, maxVUs: 20 },
};

// SLI targets. Tags let each threshold target only its journey.
export const options = {
  scenarios: { [PROFILE]: { ...profiles[PROFILE], exec: 'journey' } },
  thresholds: {
    'http_req_failed{journey:checkout}': [{ threshold: 'rate<0.005', abortOnFail: !['ramp', 'spike', 'chaos'].includes(PROFILE) }],
    'checkout_success': ['rate>0.995'],
    'http_req_duration{journey:checkout,step:place_order}': ['p(95)<400'],
    'http_req_duration{journey:browse}': ['p(95)<200'],
    // chaos abort condition: stop the experiment if >ABORT_FAIL_RATE of all requests fail
    ...(PROFILE === 'chaos' ? { 'http_req_failed': [{ threshold: `rate<${__ENV.ABORT_FAIL_RATE || 0.5}`, abortOnFail: true, delayAbortEval: '20s' }] } : {}),
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

const pick = (a) => a[Math.floor(Math.random() * a.length)];

function browse(tag) {
  group('browse', () => {
    let r = http.get(`${BASE}/`, { tags: { journey: tag, step: 'home' } });
    check(r, { 'home 200': (x) => x.status === 200 });
    sleep(Math.random() * THINK * 2);
    r = http.get(`${BASE}/product/${pick(PRODUCTS)}`, { tags: { journey: tag, step: 'product' } });
    check(r, { 'product 200': (x) => x.status === 200 });
    browseDur.add(r.timings.duration);
    if (Math.random() < 0.3) http.post(`${BASE}/setCurrency`, { currency_code: pick(CURRENCIES) }, { tags: { journey: tag, step: 'currency' } });
    sleep(Math.random() * THINK * 2);
  });
}

function addToCart(tag) {
  const r = http.post(`${BASE}/cart`, { product_id: pick(PRODUCTS), quantity: String(1 + Math.floor(Math.random() * 3)) },
                      { tags: { journey: tag, step: 'add_to_cart' } });
  check(r, { 'add to cart ok': (x) => x.status === 200 });
  sleep(Math.random() * THINK * 2);
}

export function journey() {
  journeys.add(1);
  // each VU iteration gets a fresh cookie jar => a new anonymous shopper session
  const roll = Math.random() * 100;
  if (roll < MIX_BROWSE) { browse('browse'); return; }
  if (roll < MIX_BROWSE + MIX_CART) { browse('cart'); addToCart('cart'); http.get(`${BASE}/cart`, { tags: { journey: 'cart', step: 'view_cart' } }); return; }
  // checkout
  browse('checkout'); addToCart('checkout');
  const body = {
    email: 'load@example.com', street_address: '1600 Amphitheatre Pkwy', zip_code: '94043', city: 'Mountain View', state: 'CA', country: 'United States',
    credit_card_number: '4432801561520454', credit_card_expiration_month: '1', credit_card_expiration_year: '2039', credit_card_cvv: '672',
  };
  const t0 = Date.now();
  const r = http.post(`${BASE}/cart/checkout`, body, { tags: { journey: 'checkout', step: 'place_order' } });
  const ok = check(r, { 'order confirmed': (x) => x.status === 200 && x.body.includes('Your order is complete') });
  checkoutOK.add(ok);
  checkoutDur.add(Date.now() - t0);
  sleep(THINK);
}

export function handleSummary(data) {
  const out = __ENV.OUT || `perf/results/${PROFILE}-${new Date().toISOString().replace(/[:.]/g, '-')}`;
  return { [`${out}.json`]: JSON.stringify(data, null, 2), stdout: textSummary(data) };
}
function textSummary(d) {
  const m = d.metrics, g = (k, s) => (m[k] && m[k].values[s] !== undefined ? m[k].values[s].toFixed(1) : 'n/a');
  return `\n${PROFILE}: reqs=${m.http_reqs.values.count} fail=${(m.http_req_failed.values.rate*100).toFixed(2)}% ` +
         `checkout_ok=${m.checkout_success ? (m.checkout_success.values.rate*100).toFixed(2) : 'n/a'}% ` +
         `p95(all)=${g('http_req_duration','p(95)')}ms\n`;
}
