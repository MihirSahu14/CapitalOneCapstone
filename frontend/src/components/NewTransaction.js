import React, { useState } from 'react';
import api, { getApiErrorMessage } from '../api';
import { formatCurrency, formatScore, getSavedPhoneNumber, savePhoneNumber } from '../demoState';
import styles from './NewTransaction.module.css';

const initialFormState = {
  phone_number: getSavedPhoneNumber(),
  amount: '125.00',
  merchant: 'Best Buy',
  category: 'electronics',
  state: 'IL'
};

function NewTransaction() {
  const [formData, setFormData] = useState(initialFormState);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('Submit a transaction to score it against the deployed model.');

  const handleChange = (field, value) => {
    setFormData((current) => ({
      ...current,
      [field]: value
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const payload = {
      ...formData,
      phone_number: formData.phone_number.trim(),
      amount: Number(formData.amount),
      state: formData.state.trim().toUpperCase()
    };

    setLoading(true);
    setError('');
    setMessage('');
    setResult(null);

    try {
      const response = await api.post('/transactions', payload);
      savePhoneNumber(payload.phone_number);
      setResult(response.data);
      setMessage('Transaction submitted successfully. The Lambda scorer returned a live fraud result.');
    } catch (submitError) {
      setError(getApiErrorMessage(submitError, 'Failed to submit transaction.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className={styles.container}>
      <div className={styles.pageHeader}>
        <div>
          <p className={styles.sectionLabel}>Page 3</p>
          <h2>New Transaction Simulation</h2>
          <p className={styles.sectionCopy}>
            Post a transaction to the deployed transaction Lambda and inspect the returned fraud score.
          </p>
        </div>
      </div>

      <div className={styles.grid}>
        <article className={styles.card}>
          <h3>Transaction Input</h3>
          <form onSubmit={handleSubmit}>
            <label htmlFor="tx-phone">Phone Number</label>
            <input
              id="tx-phone"
              type="text"
              placeholder="+16085551234"
              value={formData.phone_number}
              onChange={(event) => handleChange('phone_number', event.target.value)}
            />

            <label htmlFor="tx-amount">Amount</label>
            <input
              id="tx-amount"
              type="number"
              min="0.01"
              step="0.01"
              value={formData.amount}
              onChange={(event) => handleChange('amount', event.target.value)}
            />

            <label htmlFor="tx-merchant">Merchant</label>
            <input
              id="tx-merchant"
              type="text"
              value={formData.merchant}
              onChange={(event) => handleChange('merchant', event.target.value)}
            />

            <label htmlFor="tx-category">Category</label>
            <input
              id="tx-category"
              type="text"
              value={formData.category}
              onChange={(event) => handleChange('category', event.target.value)}
            />

            <label htmlFor="tx-state">Merchant State</label>
            <input
              id="tx-state"
              type="text"
              maxLength="2"
              value={formData.state}
              onChange={(event) => handleChange('state', event.target.value)}
            />

            <button type="submit" disabled={loading}>
              {loading ? 'Scoring...' : 'Score Transaction'}
            </button>
          </form>
        </article>

        <article className={styles.card}>
          <h3>Fraud Output</h3>
          {result ? (
            <div className={styles.resultGrid}>
              <div>
                <span>Transaction ID</span>
                <strong>{result.transaction_id}</strong>
              </div>
              <div>
                <span>Amount</span>
                <strong>{formatCurrency(formData.amount)}</strong>
              </div>
              <div>
                <span>Fraud Score</span>
                <strong>{formatScore(result.score)}</strong>
              </div>
              <div>
                <span>Threshold Triggered</span>
                <strong className={result.flagged ? styles.flagged : styles.clear}>
                  {result.flagged ? 'Flagged' : 'Clear'}
                </strong>
              </div>
            </div>
          ) : (
            <p className={styles.helperText}>
              No transaction submitted yet. The response payload from AWS will appear here.
            </p>
          )}
        </article>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}
      {!error && message ? <p className={styles.message}>{message}</p> : null}
    </section>
  );
}

export default NewTransaction;
