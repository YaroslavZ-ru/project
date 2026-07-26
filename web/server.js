const express = require('express');
const path = require('path');
const http = require('http');

const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE = process.env.AI_API_URL || 'http://127.0.0.1:8000';

app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// --- Прокси-хелпер ---
function proxyRequest(method, apiPath, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(apiPath, API_BASE);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method: method,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode, data: { raw: data } });
        }
      });
    });

    req.on('error', (err) => {
      reject(new Error(`Backend недоступен: ${err.message}`));
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Таймаут соединения с backend'));
    });

    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

// --- API-эндпоинты прокси ---

app.post('/api/query', async (req, res) => {
  try {
    const result = await proxyRequest('POST', '/v1/query', req.body);
    res.status(result.status).json(result.data);
  } catch (err) {
    res.status(503).json({ status: 'error', message: err.message });
  }
});

app.post('/api/feedback', async (req, res) => {
  try {
    const result = await proxyRequest('POST', '/v1/feedback', req.body);
    res.status(result.status).json(result.data);
  } catch (err) {
    res.status(503).json({ status: 'error', message: err.message });
  }
});

app.get('/api/health', async (_req, res) => {
  try {
    const result = await proxyRequest('GET', '/v1/health');
    res.status(result.status).json(result.data);
  } catch (err) {
    res.status(503).json({ status: 'error', message: err.message });
  }
});

app.get('/api/stats', async (_req, res) => {
  try {
    const result = await proxyRequest('GET', '/v1/kb/stats');
    res.status(result.status).json(result.data);
  } catch (err) {
    res.status(503).json({ status: 'error', message: err.message });
  }
});

// --- Старт ---
app.listen(PORT, () => {
  console.log(`[AI-Terminator Web] Сервер запущен: http://localhost:${PORT}`);
  console.log(`[AI-Terminator Web] Backend API: ${API_BASE}`);
});
