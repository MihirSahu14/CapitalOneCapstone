import React, { useEffect, useState } from 'react';
import api, { getApiErrorMessage } from '../api';
import { formatDate, formatScore, getSavedPhoneNumber, savePhoneNumber } from '../demoState';
import styles from './User.module.css';

const defaultCreateForm = {
  phone_number: '',
  threshold: '0.800',
  home_state: 'WI',
  dob: '2000-01-01'
};

function User() {
  const [lookupPhone, setLookupPhone] = useState(getSavedPhoneNumber);
  const [createForm, setCreateForm] = useState({
    ...defaultCreateForm,
    phone_number: getSavedPhoneNumber()
  });
  const [account, setAccount] = useState(null);
  const [threshold, setThreshold] = useState('0.800');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('Load an account to review profile data or update the threshold.');
  const [error, setError] = useState('');

  const syncPhone = (phoneNumber) => {
    setLookupPhone(phoneNumber);
    setCreateForm((current) => ({ ...current, phone_number: phoneNumber }));
  };

  const loadAccount = async (event) => {
    if (event) {
      event.preventDefault();
    }

    const trimmedPhone = lookupPhone.trim();
    if (!trimmedPhone) {
      setError('Enter a phone number before loading account details.');
      return;
    }

    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await api.get(`/accounts/by-phone/${encodeURIComponent(trimmedPhone)}`);
      const loadedAccount = response.data.account;
      setAccount(loadedAccount);
      setThreshold(formatScore(loadedAccount.threshold));
      savePhoneNumber(trimmedPhone);
      syncPhone(trimmedPhone);
      setMessage('Account details loaded from AWS.');
    } catch (fetchError) {
      setAccount(null);
      setError(getApiErrorMessage(fetchError, 'Unable to load account details.'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAccount = async (event) => {
    event.preventDefault();

    const payload = {
      ...createForm,
      phone_number: createForm.phone_number.trim(),
      home_state: createForm.home_state.trim().toUpperCase(),
      threshold: Number(createForm.threshold)
    };

    setLoading(true);
    setError('');
    setMessage('');

    try {
      await api.post('/accounts', payload);
      savePhoneNumber(payload.phone_number);
      syncPhone(payload.phone_number);
      setMessage('Account created. Loading fresh details now.');
      await loadAccount();
    } catch (createError) {
      setError(getApiErrorMessage(createError, 'Unable to create account.'));
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateThreshold = async () => {
    const trimmedPhone = lookupPhone.trim();
    if (!trimmedPhone) {
      setError('Load an account before updating the threshold.');
      return;
    }

    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await api.patch(
        `/accounts/by-phone/${encodeURIComponent(trimmedPhone)}/threshold`,
        { threshold: Number(threshold) }
      );
      setMessage(
        `Threshold updated from ${formatScore(response.data.old_threshold)} to ${formatScore(response.data.new_threshold)}.`
      );
      await loadAccount();
    } catch (updateError) {
      setError(getApiErrorMessage(updateError, 'Unable to update threshold.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (lookupPhone) {
      loadAccount();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className={styles.container}>
      <div className={styles.pageHeader}>
        <div>
          <p className={styles.sectionLabel}>Page 2</p>
          <h2>User Details And Threshold Setup</h2>
          <p className={styles.sectionCopy}>
            Load an existing user by phone number, create one if needed, and update the fraud threshold.
          </p>
        </div>
      </div>

      <div className={styles.twoColumn}>
        <article className={styles.card}>
          <h3>Lookup Existing User</h3>
          <form onSubmit={loadAccount}>
            <label htmlFor="lookup-phone">Phone Number</label>
            <input
              id="lookup-phone"
              type="text"
              placeholder="+16085551234"
              value={lookupPhone}
              onChange={(event) => syncPhone(event.target.value)}
            />
            <button type="submit" disabled={loading}>
              {loading ? 'Loading...' : 'Load User'}
            </button>
          </form>

          {account ? (
            <div className={styles.accountSummary}>
              <div>
                <span>Account ID</span>
                <strong>{account.account_id}</strong>
              </div>
              <div>
                <span>Home State</span>
                <strong>{account.home_state || '-'}</strong>
              </div>
              <div>
                <span>Date of Birth</span>
                <strong>{account.dob || '-'}</strong>
              </div>
              <div>
                <span>Created</span>
                <strong>{formatDate(account.created_at)}</strong>
              </div>
            </div>
          ) : (
            <p className={styles.helperText}>No loaded account yet. Use the create form if this number is new.</p>
          )}
        </article>

        <article className={styles.card}>
          <h3>Create Demo User</h3>
          <form onSubmit={handleCreateAccount}>
            <label htmlFor="create-phone">Phone Number</label>
            <input
              id="create-phone"
              type="text"
              placeholder="+16085551234"
              value={createForm.phone_number}
              onChange={(event) => syncPhone(event.target.value)}
            />

            <label htmlFor="create-state">Home State</label>
            <input
              id="create-state"
              type="text"
              maxLength="2"
              value={createForm.home_state}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, home_state: event.target.value }))
              }
            />

            <label htmlFor="create-dob">Date Of Birth</label>
            <input
              id="create-dob"
              type="date"
              value={createForm.dob}
              onChange={(event) => setCreateForm((current) => ({ ...current, dob: event.target.value }))}
            />

            <label htmlFor="create-threshold">Starting Threshold</label>
            <input
              id="create-threshold"
              type="number"
              min="0"
              max="1"
              step="0.001"
              value={createForm.threshold}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, threshold: event.target.value }))
              }
            />

            <button type="submit" disabled={loading}>
              {loading ? 'Saving...' : 'Create User'}
            </button>
          </form>
        </article>
      </div>

      <article className={styles.card}>
        <h3>Update Threshold</h3>
        <div className={styles.thresholdRow}>
          <div className={styles.thresholdField}>
            <label htmlFor="threshold-input">Fraud Threshold</label>
            <input
              id="threshold-input"
              type="number"
              min="0"
              max="1"
              step="0.001"
              value={threshold}
              onChange={(event) => setThreshold(event.target.value)}
            />
          </div>
          <button type="button" onClick={handleUpdateThreshold} disabled={loading || !account}>
            {loading ? 'Updating...' : 'Update Threshold'}
          </button>
        </div>
      </article>

      {error ? <p className={styles.error}>{error}</p> : null}
      {!error && message ? <p className={styles.message}>{message}</p> : null}
    </section>
  );
}

export default User;
