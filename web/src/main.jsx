  import React from 'react';
  import ReactDOM from 'react-dom/client';
  import { RouterProvider } from 'react-router/dom';
  import { router } from './router';
  import { migrateStorageKeys } from './lib/storage';
  import './index.css';

  // Move any legacy (un-prefixed) browser storage keys to the `bf:` scheme
  // before the app reads them.
  migrateStorageKeys();

  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <RouterProvider router={router} />
    </React.StrictMode>
  );