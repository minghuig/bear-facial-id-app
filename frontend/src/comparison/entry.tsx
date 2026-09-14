import React from 'react';
import { createRoot } from 'react-dom/client';
import Comparison from './Comparison';
import './comparison.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><Comparison/></React.StrictMode>);
