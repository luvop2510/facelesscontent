import { companies } from '../data.js';

const pickKey = 'launchplan-preview-pick';
const draftsKey = 'launchplan-listing-drafts';
const signs = document.querySelectorAll('[data-place]');
const places = document.querySelectorAll('#map-places article');
const pickForm = document.querySelector('#pick-form');
const pickFeedback = document.querySelector('#pick-feedback');
const pickBoard = document.querySelector('#pick-board');
const listingForm = document.querySelector('#listing-form');
const listingFeedback = document.querySelector('#listing-feedback');
const websiteInput = document.querySelector('#company-url');
const savedListings = document.querySelector('#saved-listings');
const listingItems = document.querySelector('#listing-items');

function selectPlace(id) {
  for (const sign of signs) {
    if (sign.dataset.place === id) sign.setAttribute('aria-current', 'true');
    else sign.removeAttribute('aria-current');
  }
  for (const place of places) place.hidden = place.id !== id;
}

for (const sign of signs) {
  sign.addEventListener('click', (event) => {
    event.preventDefault();
    selectPlace(sign.dataset.place);
    document.getElementById(sign.dataset.place).scrollIntoView({ block: 'nearest' });
  });
}
const requestedPlace = location.hash.slice(1);
selectPlace(Array.from(places).some((place) => place.id === requestedPlace) ? requestedPlace : 'cafe');

try {
  const choice = localStorage.getItem(pickKey);
  if (Object.hasOwn(companies, choice)) {
    pickForm.elements.company.value = choice;
    pickBoard.textContent = companies[choice].name;
    pickFeedback.textContent = `Your saved preview pick is ${companies[choice].name}. You can change it.`;
  }
} catch {
  pickFeedback.textContent = 'Browser storage is unavailable.';
}

pickForm.addEventListener('change', () => {
  const choice = pickForm.elements.company.value;
  if (Object.hasOwn(companies, choice)) pickBoard.textContent = companies[choice].name;
});

pickForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const choice = new FormData(pickForm).get('company');
  if (!Object.hasOwn(companies, choice)) return;
  try {
    localStorage.setItem(pickKey, choice);
    pickFeedback.textContent = `Your preview pick for ${companies[choice].name} is saved in this browser.`;
  } catch {
    pickFeedback.textContent = 'Your pick could not be saved. Check whether this browser allows local storage.';
  }
});
pickForm.querySelector('button').disabled = false;

function companyWebsite(value) {
  try {
    const url = new URL(value);
    if (url.protocol === 'https:' && url.hostname.includes('.') && !url.username && !url.password) {
      return url.href;
    }
  } catch { /* Native form validation handles ordinary mistyped URLs. */ }
  return '';
}

function readDrafts() {
  try {
    const saved = JSON.parse(localStorage.getItem(draftsKey) ?? '[]');
    return Array.isArray(saved) ? saved.filter((draft) => (
      typeof draft?.name === 'string' && typeof draft.note === 'string' && companyWebsite(draft.url)
    )) : [];
  } catch {
    return [];
  }
}

function showDrafts(drafts) {
  listingItems.replaceChildren();
  for (const draft of drafts) {
    const entry = document.createElement('li');
    const link = document.createElement('a');
    const status = document.createElement('small');
    link.href = draft.url;
    link.textContent = draft.name;
    status.textContent = 'Draft · saved here for your review';
    entry.append(link, status);
    if (draft.note) {
      const description = document.createElement('p');
      description.textContent = draft.note;
      entry.append(description);
    }
    listingItems.append(entry);
  }
  savedListings.hidden = drafts.length === 0;
}

websiteInput.addEventListener('input', () => websiteInput.setCustomValidity(''));
const nameInput = document.querySelector('#company-name');
nameInput.addEventListener('input', () => nameInput.setCustomValidity(''));
listingForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const fields = new FormData(listingForm);
  const name = fields.get('name').trim();
  const url = companyWebsite(fields.get('url'));
  if (!name) {
    nameInput.setCustomValidity('Enter a company name.');
    nameInput.reportValidity();
    return;
  }
  if (!url) {
    websiteInput.setCustomValidity('Enter a complete public website URL starting with https://.');
    websiteInput.reportValidity();
    return;
  }
  const draft = { name, url, note: fields.get('note').trim() };
  const drafts = [draft, ...readDrafts().filter((saved) => saved.url !== url)];
  try {
    localStorage.setItem(draftsKey, JSON.stringify(drafts));
    showDrafts(drafts);
    listingForm.reset();
    listingFeedback.textContent = `The ${name} draft is saved in this browser for your review.`;
  } catch {
    listingFeedback.textContent = 'Your draft could not be saved. The form still has your details.';
  }
});
showDrafts(readDrafts());
listingForm.querySelector('button').disabled = false;

if ('IntersectionObserver' in window && matchMedia('(prefers-reduced-motion: no-preference)').matches) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add('town-enter');
      observer.unobserve(entry.target);
    }
  }, { threshold: .22 });
  document.querySelectorAll('.directory-intro > *, .directory-entry > *, .pick-picture, .pick-copy > *, .join-copy > *, .join-workspace').forEach((part) => observer.observe(part));
}
