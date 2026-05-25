from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
from functools import wraps
from time import sleep
import uuid
import logging
import json
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__)
CORS(app)

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ (ФИКС #3: UTF-8) ==========
if not os.path.exists('logs'):
    os.mkdir('logs')

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'message': record.getMessage(),
        }
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        return json.dumps(log_entry, ensure_ascii=False)

file_handler = RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5, encoding='utf-8')
file_handler.setFormatter(JsonFormatter())
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
console_handler.setLevel(logging.DEBUG)

logger = logging.getLogger('transport_logistics')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ========== RETRY ==========
def retry(max_attempts=3, delay_seconds=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"Попытка {attempt}/{max_attempts}")
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Ошибка (попытка {attempt}): {str(e)}")
                    if attempt < max_attempts:
                        sleep(delay_seconds * attempt)
            raise last_exception
        return wrapper
    return decorator

# ========== CIRCUIT BREAKER (ФИКС #2: правильный таймаут) ==========
class CircuitBreaker:
    def __init__(self, failure_threshold=2, timeout_seconds=10):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'
    
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if self.last_failure_time:
                seconds_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if seconds_since_failure > self.timeout_seconds:
                    self.state = 'HALF_OPEN'
                    logger.info(f"Circuit Breaker -> HALF_OPEN (прошло {seconds_since_failure:.0f} сек)")
                else:
                    remaining = int(self.timeout_seconds - seconds_since_failure)
                    raise Exception(f"Circuit Breaker OPEN. Повторите через {remaining} сек")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                logger.info(f"Circuit Breaker -> CLOSED (запрос успешен)")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.error(f"Circuit Breaker -> OPEN (сбоев: {self.failure_count})")
            raise e

circuit_breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=10)
requests_storage = []

# ========== HTML ШАБЛОН ==========
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Транспортная логистика | Мониторинг</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); font-family: 'Segoe UI', sans-serif; padding: 20px; min-height: 100vh; }
        .container { max-width: 1400px; margin: 0 auto; }
        .main-card { background: rgba(255,255,255,0.95); border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 35px; text-align: center; color: white; }
        .header h1 { font-size: 2.2rem; margin-bottom: 10px; font-weight: 600; }
        .header p { opacity: 0.9; font-size: 1rem; }
        .content { padding: 35px; }
        .card-custom { background: #f8f9fa; border-radius: 20px; padding: 25px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: transform 0.2s; }
        .card-custom:hover { transform: translateY(-3px); }
        .btn-custom { border: none; padding: 12px 24px; border-radius: 12px; font-weight: 600; transition: all 0.3s; margin: 5px; }
        .btn-success-custom { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }
        .btn-danger-custom { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); color: white; }
        .btn-custom:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .log-container { background: #1a1a2e; border-radius: 16px; padding: 20px; font-family: 'Courier New', monospace; font-size: 13px; height: 320px; overflow-y: auto; }
        .log-info { color: #4ec9b0; border-left: 3px solid #4ec9b0; padding: 6px 12px; margin: 4px 0; background: rgba(78,201,176,0.1); border-radius: 8px; }
        .log-warning { color: #dcdcaa; border-left: 3px solid #dcdcaa; padding: 6px 12px; margin: 4px 0; background: rgba(220,220,170,0.1); border-radius: 8px; }
        .log-error { color: #f48771; border-left: 3px solid #f48771; padding: 6px 12px; margin: 4px 0; background: rgba(244,135,113,0.1); border-radius: 8px; }
        .circuit-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; padding: 25px; color: white; text-align: center; }
        .circuit-closed { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .circuit-open { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
        .circuit-half { background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%); }
        .table-custom { background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .table-custom thead { background: #667eea; color: white; }
        .table-custom th, .table-custom td { padding: 12px 15px; vertical-align: middle; }
        .badge-custom { padding: 6px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; }
        .badge-success { background: #28a745; color: white; }
        .badge-error { background: #dc3545; color: white; }
        .form-control-custom { width: 100%; padding: 12px 16px; border: 2px solid #e0e0e0; border-radius: 12px; margin-bottom: 15px; transition: all 0.3s; }
        .form-control-custom:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        hr { margin: 35px 0; border: none; border-top: 2px solid #e0e0e0; }
        h5 { font-weight: 600; margin-bottom: 20px; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-card">
            <div class="header">
                <h1><i class="fas fa-chart-line me-3"></i>Транспортная логистика</h1>
                <p>Мониторинг, обработка ошибок и структурированное логирование</p>
            </div>
            <div class="content">
                <div class="row">
                    <div class="col-md-6">
                        <div class="card-custom">
                            <h5><i class="fas fa-plus-circle me-2" style="color: #667eea;"></i>Создание заявки</h5>
                            <input type="number" id="weight" class="form-control-custom" placeholder="Вес груза (кг)" value="5000">
                            <input type="text" id="pickup" class="form-control-custom" placeholder="Адрес загрузки" value="Москва, ул. Тверская 1">
                            <input type="text" id="delivery" class="form-control-custom" placeholder="Адрес доставки" value="Санкт-Петербург, Невский пр. 10">
                            <div class="d-flex gap-3 mt-3">
                                <button class="btn btn-success-custom btn-custom flex-fill" onclick="createRequest(false)">✅ Успешный сценарий</button>
                                <button class="btn btn-danger-custom btn-custom flex-fill" onclick="createRequest(true)">❌ Сценарий с ошибкой</button>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="circuit-card" id="circuitCard">
                            <h5><i class="fas fa-shield-alt me-2"></i>Circuit Breaker</h5>
                            <div id="circuitStatus" style="font-size: 1.2rem; margin: 15px 0;">Загрузка...</div>
                            <div id="circuitDetails" style="font-size: 0.9rem;"></div>
                            <button class="btn btn-light mt-3" onclick="resetCircuit()" style="border-radius: 10px;">🔄 Сбросить Circuit Breaker</button>
                        </div>
                    </div>
                </div>
                <hr>
                <h5><i class="fas fa-terminal me-2" style="color: #667eea;"></i>Логи интеграции</h5>
                <div class="log-container" id="logArea"><div class="log-info">[INFO] Система готова к работе</div></div>
                <h5 class="mt-4"><i class="fas fa-history me-2" style="color: #667eea;"></i>История заявок</h5>
                <div class="table-responsive">
                    <table class="table table-custom">
                        <thead><tr><th>ID</th><th>Время</th><th>Вес</th><th>Маршрут</th><th>Статус</th><th>Ошибка</th></tr></thead>
                        <tbody id="historyTable"><tr><td colspan="6" class="text-center">Нет заявок</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <script>
        function addLog(message, type) {
            const logDiv = document.createElement('div');
            logDiv.className = `log-${type}`;
            logDiv.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            document.getElementById('logArea').appendChild(logDiv);
            document.getElementById('logArea').scrollTop = document.getElementById('logArea').scrollHeight;
        }
        
        async function createRequest(forceError) {
            addLog(`🔄 Создание заявки`, 'info');
            let attempt = 1;
            const maxAttempts = 3;
            for (attempt = 1; attempt <= maxAttempts; attempt++) {
                addLog(`📡 Попытка ${attempt}/${maxAttempts}...`, 'info');
                try {
                    const response = await fetch('/api/create-request', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            weight: document.getElementById('weight').value,
                            pickup: document.getElementById('pickup').value,
                            delivery: document.getElementById('delivery').value,
                            force_error: forceError,
                            attempt: attempt
                        })
                    });
                    const data = await response.json();
                    if (response.ok) {
                        addLog(`✅ ${data.message}`, 'info');
                        break;
                    } else {
                        addLog(`❌ Ошибка: ${data.error}`, 'error');
                        if (attempt === maxAttempts) addLog(`⛔ Все ${maxAttempts} попытки не удались`, 'error');
                    }
                } catch(e) {
                    addLog(`❌ Ошибка сети: ${e.message}`, 'error');
                }
                if (attempt < maxAttempts) await new Promise(r => setTimeout(r, 1000 * attempt));
            }
            loadHistory();
            loadCircuitStatus();
        }
        
        async function loadHistory() {
            const response = await fetch('/api/requests');
            const requests = await response.json();
            const tbody = document.getElementById('historyTable');
            if (requests.length === 0) tbody.innerHTML = '<tr><td colspan="6" class="text-center">Нет заявок</td></tr>';
            else tbody.innerHTML = requests.map(r => `<tr style="background: ${r.status === 'error' ? '#fff5f5' : '#f0fff4'}"><td><code>${r.id}</code></td><td>${r.date || '-'}</td><td>${r.weight} кг</td><td>${r.pickup} → ${r.delivery}</td><td><span class="badge-custom ${r.status === 'success' ? 'badge-success' : 'badge-error'}">${r.status}</span></td><td style="color: #dc3545;">${r.error || '-'}</td></tr>`).join('');
        }
        
        async function loadCircuitStatus() {
            const response = await fetch('/api/circuit-status');
            const data = await response.json();
            const card = document.getElementById('circuitCard');
            const statusDiv = document.getElementById('circuitStatus');
            const detailsDiv = document.getElementById('circuitDetails');
            card.classList.remove('circuit-closed', 'circuit-open', 'circuit-half');
            if (data.state === 'CLOSED') { card.classList.add('circuit-closed'); statusDiv.innerHTML = '✅ СОСТОЯНИЕ: CLOSED (работает)'; }
            else if (data.state === 'OPEN') { card.classList.add('circuit-open'); statusDiv.innerHTML = '🔴 СОСТОЯНИЕ: OPEN (заблокирован)'; }
            else { card.classList.add('circuit-half'); statusDiv.innerHTML = '🟡 СОСТОЯНИЕ: HALF-OPEN (тестовый режим)'; }
            detailsDiv.innerHTML = `Сбоев: ${data.failure_count} / ${data.failure_threshold}<br>Последний сбой: ${data.last_failure_time || '—'}`;
        }
        
        async function resetCircuit() {
            await fetch('/api/reset-circuit', {method: 'POST'});
            addLog('Circuit Breaker сброшен принудительно', 'warning');
            loadCircuitStatus();
        }
        
        setInterval(() => { loadCircuitStatus(); loadHistory(); }, 3000);
        loadHistory();
        loadCircuitStatus();
    </script>
</body>
</html>
'''

# ========== API ==========
@retry(max_attempts=3, delay_seconds=1)
def call_external_service_with_retry(should_fail):
    logger.info(f"Вызов внешнего сервиса (fail={should_fail})")
    if should_fail:
        raise Exception("Сервис транспорта временно недоступен")
    return {"status": "ok", "vehicle": "v1", "driver": "Иван"}

@app.route('/api/create-request', methods=['POST'])
def create_request():
    data = request.json
    request_id = str(uuid.uuid4())[:8]
    force_error = data.get('force_error', False)
    
    # Проверка дубликатов
    for r in requests_storage[:5]:
        if r.get('weight') == data.get('weight'):
            last_time = r.get('date')
            if last_time and (datetime.now() - datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')).seconds < 2:
                logger.warning(f"Дубликат заявки")
                return jsonify({'status': 'error', 'error': 'Дубликат заявки'}), 429
            break
    
    logger.info(f"Создание заявки {request_id}")
    
    try:
        result = circuit_breaker.call(call_external_service_with_retry, force_error)
        
        # ТОЛЬКО ПРИ УСПЕХЕ сохраняем заявку
        request_data = {
            'id': request_id,
            'weight': data.get('weight'),
            'pickup': data.get('pickup'),
            'delivery': data.get('delivery'),
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'success',
            'error': None
        }
        requests_storage.insert(0, request_data)
        
        return jsonify({
            'status': 'success',
            'request_id': request_id,
            'message': f'Заявка {request_id} создана. Назначен {result["vehicle"]} (водитель {result["driver"]})'
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка заявки {request_id}: {error_msg}")
        
        # НЕ СОХРАНЯЕМ заявку с ошибкой (компенсация не нужна)
        return jsonify({'status': 'error', 'error': error_msg}), 500

@app.route('/api/requests', methods=['GET'])
def get_requests():
    return jsonify(requests_storage[:20])

@app.route('/api/circuit-status', methods=['GET'])
def get_circuit_status():
    return jsonify({
        'state': circuit_breaker.state,
        'failure_count': circuit_breaker.failure_count,
        'failure_threshold': circuit_breaker.failure_threshold,
        'last_failure_time': str(circuit_breaker.last_failure_time) if circuit_breaker.last_failure_time else None
    })

@app.route('/api/reset-circuit', methods=['POST'])
def reset_circuit():
    global circuit_breaker
    circuit_breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=10)
    logger.info("Circuit Breaker сброшен")
    return jsonify({'status': 'ok'})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    print("=" * 60)
    print("ТРАНСПОРТНАЯ ЛОГИСТИКА - ЗАПУЩЕНА")
    print("=" * 60)
    print("Логи: logs/app.log (JSON формат, UTF-8)")
    print("Retry: 3 попытки с задержкой")
    print("Circuit Breaker: после 2 сбоев -> OPEN на 10 сек")
    print("Компенсация: заявки с ошибкой НЕ сохраняются")
    print("Защита от дубликатов: 2 секунды между одинаковыми заявками")
    print("")
    print("Открой браузер: http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)