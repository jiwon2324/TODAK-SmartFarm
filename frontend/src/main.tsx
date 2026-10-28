import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { SNAPSHOT, startSnapshot } from './snapshot';

const render = () =>
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );

if (SNAPSHOT) startSnapshot().then(render);
else render();
