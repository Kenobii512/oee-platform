// Chart.js bileşen kaydı + premium varsayılanlar (Jinja dashboard.js'ten port).
// Bir kez import edilir (main.tsx); react-chartjs-2 instance'ları yönetir.
import {
  BarElement,
  CategoryScale,
  Chart,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from 'chart.js'

import { C } from '../styles/theme'

Chart.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
)

Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif"
Chart.defaults.font.weight = 500
Chart.defaults.color = C.muted
