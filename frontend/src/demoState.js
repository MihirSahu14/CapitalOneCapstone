const PHONE_STORAGE_KEY = 'sentinel-demo-phone-number';

export function getSavedPhoneNumber() {
  return window.localStorage.getItem(PHONE_STORAGE_KEY) || '';
}

export function savePhoneNumber(phoneNumber) {
  window.localStorage.setItem(PHONE_STORAGE_KEY, phoneNumber);
}

export function formatCurrency(value) {
  const amount = Number(value);

  if (Number.isNaN(amount)) {
    return '-';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount);
}

export function formatScore(value) {
  const score = Number(value);

  if (Number.isNaN(score)) {
    return '-';
  }

  return score.toFixed(3);
}

export function formatDate(value) {
  if (!value) {
    return '-';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}
