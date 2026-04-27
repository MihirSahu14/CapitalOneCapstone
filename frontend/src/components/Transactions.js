import React, { useEffect, useState } from 'react';
import api, { getApiErrorMessage } from '../api';
import {
  formatCurrency,
  formatDate,
  formatScore,
  getSavedPhoneNumber,
  savePhoneNumber
} from '../demoState';
import styles from './Transactions.module.css';

function Transactions() {
  const [phoneNumber, setPhoneNumber] = useState(getSavedPhoneNumber);
  const [account, setAccount] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('Enter a registered phone number to load account history.');
  const [error, setError] = useState('');

  const loadTransactions = async (event) => {
    if (event) {
      event.preventDefault();
    }

    const trimmedPhone = phoneNumber.trim();
    if (!trimmedPhone) {
      setError('Enter the demo user phone number in E.164 format.');
      return;
    }

    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await api.get(`/accounts/by-phone/${encodeURIComponent(trimmedPhone)}`);
      setAccount(response.data.account);
      setTransactions(response.data.transactions || []);
      savePhoneNumber(trimmedPhone);
      setMessage('Transaction history loaded from the deployed AWS account service.');
    } catch (fetchError) {
      setAccount(null);
      setTransactions([]);
      setError(getApiErrorMessage(fetchError, 'Unable to load transaction history.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (phoneNumber) {
      loadTransactions();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className={styles.container}>
      <div className={styles.headerRow}>
        <div>
          <p className={styles.sectionLabel}>Page 1</p>
          <h2>Past Transactions</h2>
          <p className={styles.sectionCopy}>
            Pull the latest account details and recent scored transactions from the deployed API.
          </p>
        </div>
      </div>

      <form className={styles.lookupForm} onSubmit={loadTransactions}>
        <label htmlFor="transactions-phone">Registered Phone Number</label>
        <div className={styles.inlineControls}>
          <input
            id="transactions-phone"
            type="text"
            placeholder="+16085551234"
            value={phoneNumber}
            onChange={(event) => setPhoneNumber(event.target.value)}
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Loading...' : 'Load History'}
          </button>
        </div>
      </form>

      {error ? <p className={styles.error}>{error}</p> : null}
      {!error && message ? <p className={styles.message}>{message}</p> : null}

      {account ? (
        <div className={styles.accountGrid}>
          <article className={styles.statCard}>
            <span>Account ID</span>
            <strong>{account.account_id}</strong>
          </article>
          <article className={styles.statCard}>
            <span>Phone</span>
            <strong>{account.phone_number}</strong>
          </article>
          <article className={styles.statCard}>
            <span>Threshold</span>
            <strong>{formatScore(account.threshold)}</strong>
          </article>
          <article className={styles.statCard}>
            <span>Home State</span>
            <strong>{account.home_state || '-'}</strong>
          </article>
        </div>
      ) : null}

      <div className={styles.tableCard}>
        <div className={styles.tableHeader}>
          <h3>Recent Transactions</h3>
          <span>{transactions.length} loaded</span>
        </div>

        {transactions.length === 0 ? (
          <p className={styles.emptyState}>No transactions returned for this account yet.</p>
        ) : (
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Amount</th>
                  <th>Merchant</th>
                  <th>Category</th>
                  <th>State</th>
                  <th>Created</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((transaction) => (
                  <tr key={transaction.transaction_id}>
                    <td>{transaction.transaction_id}</td>
                    <td>{formatCurrency(transaction.amount)}</td>
                    <td>{transaction.merchant || '-'}</td>
                    <td>{transaction.category || '-'}</td>
                    <td>{transaction.state || '-'}</td>
                    <td>{formatDate(transaction.created_at)}</td>
                    <td>{formatScore(transaction.score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

export default Transactions;
