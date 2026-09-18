import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = {
  status: () => axios.get(`${API}/bot/status`).then((r) => r.data),
  start: () => axios.post(`${API}/bot/start`).then((r) => r.data),
  stop: () => axios.post(`${API}/bot/stop`).then((r) => r.data),
  reset: () => axios.post(`${API}/bot/reset`).then((r) => r.data),
  updateConfig: (patch) => axios.put(`${API}/bot/config`, patch).then((r) => r.data),
  trades: (limit = 100) => axios.get(`${API}/trades`, { params: { limit } }).then((r) => r.data),
  logs: (limit = 100) => axios.get(`${API}/logs`, { params: { limit } }).then((r) => r.data),
  equity: () => axios.get(`${API}/equity`).then((r) => r.data),
  signals: () => axios.get(`${API}/market/signals`).then((r) => r.data),
  symbols: () => axios.get(`${API}/market/symbols`).then((r) => r.data),
  klines: (symbol, interval = "1m", limit = 120) =>
    axios.get(`${API}/market/klines`, { params: { symbol, interval, limit } }).then((r) => r.data),
  closePosition: (id) => axios.post(`${API}/positions/${id}/close`).then((r) => r.data),
  closeAll: () => axios.post(`${API}/positions/close-all`).then((r) => r.data),
};
