import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Chart as ChartJS } from 'chart.js'
import App from './App.jsx'
import './styles.css'

ChartJS.defaults.font.family = 'Manrope, ui-sans-serif, system-ui, sans-serif'
ChartJS.defaults.color = '#696d66'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
