import React from 'react';
import { BrowserRouter as Router, NavLink, Route, Routes } from 'react-router-dom';
import Transactions from './components/Transactions';
import User from './components/User';
import NewTransaction from './components/NewTransaction';
import './App.css';

const navItems = [
  { to: '/', label: 'Past Transactions' },
  { to: '/user', label: 'User Details' },
  { to: '/new-transaction', label: 'New Transaction' }
];

function App() {
  return (
    <Router>
      <div className="appShell">
        <header className="hero">
          <div className="heroContent">
            <p className="eyebrow">Fraud Detection System</p>
            <h1>Sentinel.AI</h1>
          </div>
        </header>

        <nav className="topNav" aria-label="Primary">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              end={item.to === '/'}
              to={item.to}
              className={({ isActive }) => `navLink${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <main className="pageFrame">
          <Routes>
            <Route path="/" element={<Transactions />} />
            <Route path="/user" element={<User />} />
            <Route path="/new-transaction" element={<NewTransaction />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
