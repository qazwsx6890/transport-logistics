from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)

# Хранилище заявок (в памяти)
requests_db = []

# HTML шаблон
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Транспортная логистика - Интеграционная платформа</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .main-card { border-radius: 15px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; }
        .status-badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status-pending { background: #ffc107; color: #000; }
        .status-success { background: #28a745; color: white; }
        .status-error { background: #dc3545; color: white; }
        .status-progress { background: #17a2b8; color: white; }
        .log-area { background: #1e1e1e; color: #d4d4d4; font-family: 'Courier New', monospace; font-size: 12px; height: 200px; overflow-y: auto; padding: 10px; border-radius: 8px; }
        .log-line { margin: 0; padding: 2px 0; border-bottom: 1px solid #333; font-family: monospace; }
        .log-info { color: #4ec9b0; }
        .log-error { color: #f48771; }
        .log-warning { color: #dcdcaa; }
        .nav-tabs .nav-link { color: #667eea; font-weight: bold; }
        .nav-tabs .nav-link.active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; }
        .table-responsive { max-height: 400px; overflow-y: auto; }
        .btn-submit { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; padding: 12px 30px; font-weight: bold; transition: transform 0.2s; }
        .btn-submit:hover { transform: scale(1.02); background: linear-gradient(135deg, #5a67d8 0%, #6b46a0 100%); }
        .vehicle-card { border-left: 4px solid #28a745; margin-bottom: 10px; transition: all 0.2s; }
        .vehicle-card:hover { transform: translateX(5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .route-card { border-left: 4px solid #17a2b8; margin-bottom: 10px; }
        .waybill-card { border-left: 4px solid #ffc107; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card main-card">
            <div class="header text-center">
                <h1><i class="fas fa-truck-moving me-2"></i>Транспортная логистика</h1>
                <p class="mb-0">Интеграционная платформа | Заявки → Транспорт → Маршруты → Путевые листы</p>
            </div>
            
            <div class="card-body p-4">
                <!-- Вкладки -->
                <ul class="nav nav-tabs mb-4" id="myTab" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="create-tab" data-bs-toggle="tab" data-bs-target="#create" type="button" role="tab">
                            <i class="fas fa-plus-circle me-2"></i>Создать заявку
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="history-tab" data-bs-toggle="tab" data-bs-target="#history" type="button" role="tab">
                            <i class="fas fa-history me-2"></i>История заявок
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="vehicles-tab" data-bs-toggle="tab" data-bs-target="#vehicles" type="button" role="tab">
                            <i class="fas fa-truck me-2"></i>Транспорт
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="logs-tab" data-bs-toggle="tab" data-bs-target="#logs" type="button" role="tab">
                            <i class="fas fa-terminal me-2"></i>Логи интеграции
                        </button>
                    </li>
                </ul>
                
                <div class="tab-content">
                    <!-- Вкладка создания заявки -->
                    <div class="tab-pane fade show active" id="create" role="tabpanel">
                        <div class="row">
                            <div class="col-md-6">
                                <h5><i class="fas fa-info-circle me-2"></i>Данные груза</h5>
                                <div class="mb-3">
                                    <label class="form-label">Вес груза (кг)</label>
                                    <input type="number" class="form-control" id="weight" value="5000">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Объем груза (м³)</label>
                                    <input type="number" class="form-control" id="volume" value="20">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Тип груза</label>
                                    <select class="form-control" id="cargo_type">
                                        <option value="обычный">Обычный</option>
                                        <option value="опасный">Опасный</option>
                                        <option value="скоропортящийся">Скоропортящийся</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h5><i class="fas fa-location-dot me-2"></i>Маршрут</h5>
                                <div class="mb-3">
                                    <label class="form-label">Адрес загрузки</label>
                                    <input type="text" class="form-control" id="pickup" value="Москва, ул. Тверская 1">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Адрес доставки</label>
                                    <input type="text" class="form-control" id="delivery" value="Санкт-Петербург, Невский пр. 10">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Дедлайн</label>
                                    <input type="date" class="form-control" id="deadline">
                                </div>
                            </div>
                        </div>
                        <div class="text-center mt-3">
                            <button class="btn btn-submit text-white" onclick="createRequest()">
                                <i class="fas fa-play me-2"></i>Запустить интеграционный сценарий
                            </button>
                        </div>
                        <div id="createResult" class="mt-4" style="display: none;">
                            <div class="alert" id="resultAlert"></div>
                            <div class="mt-3" id="resultDetails"></div>
                        </div>
                    </div>
                    
                    <!-- Вкладка истории -->
                    <div class="tab-pane fade" id="history" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>ID</th>
                                        <th>Дата</th>
                                        <th>Вес</th>
                                        <th>Откуда</th>
                                        <th>Куда</th>
                                        <th>Транспорт</th>
                                        <th>Статус</th>
                                    </tr>
                                </thead>
                                <tbody id="historyTable">
                                    <tr><td colspan="7" class="text-center">Нет заявок</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- Вкладка транспорта -->
                    <div class="tab-pane fade" id="vehicles" role="tabpanel">
                        <div id="vehiclesList"></div>
                    </div>
                    
                    <!-- Вкладка логов -->
                    <div class="tab-pane fade" id="logs" role="tabpanel">
                        <div class="log-area" id="logArea">
                            <div class="log-line log-info">[INFO] Система готова к работе</div>
                        </div>
                        <button class="btn btn-sm btn-secondary mt-2" onclick="clearLogs()">
                            <i class="fas fa-trash me-1"></i>Очистить логи
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let logs = ['[INFO] Система готова к работе'];
        
        function addLog(message, type = 'info') {
            const logLine = `<div class="log-line log-${type}">[${new Date().toLocaleTimeString()}] ${message}</div>`;
            logs.push(`[${type.toUpperCase()}] ${message}`);
            document.getElementById('logArea').innerHTML += logLine;
            document.getElementById('logArea').scrollTop = document.getElementById('logArea').scrollHeight;
        }
        
        function clearLogs() {
            logs = [];
            document.getElementById('logArea').innerHTML = '';
            addLog('Логи очищены', 'warning');
        }
        
        async function createRequest() {
            const weight = document.getElementById('weight').value;
            const volume = document.getElementById('volume').value;
            const cargo_type = document.getElementById('cargo_type').value;
            const pickup = document.getElementById('pickup').value;
            const delivery = document.getElementById('delivery').value;
            const deadline = document.getElementById('deadline').value;
            
            addLog(`Создание заявки: ${weight}кг из ${pickup} в ${delivery}`, 'info');
            
            document.getElementById('createResult').style.display = 'block';
            document.getElementById('resultAlert').innerHTML = '<div class="spinner-border text-primary" role="status"></div> Обработка...';
            
            try {
                const response = await fetch('/api/create-request', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({weight, volume, cargo_type, pickup, delivery, deadline})
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    addLog(`Заявка ${data.request_id} создана успешно`, 'info');
                    addLog(`Назначен транспорт: ${data.transport}`, 'info');
                    addLog(`Маршрут построен: ${data.route}`, 'info');
                    addLog(`Путевой лист: ${data.waybill}`, 'info');
                    
                    document.getElementById('resultAlert').innerHTML = `<div class="alert alert-success">✅ Успешно! Заявка создана.</div>`;
                    document.getElementById('resultDetails').innerHTML = `
                        <div class="row">
                            <div class="col-md-4"><div class="card vehicle-card p-3"><small><i class="fas fa-truck"></i> Транспорт</small><br><strong>${data.transport}</strong></div></div>
                            <div class="col-md-4"><div class="card route-card p-3"><small><i class="fas fa-route"></i> Маршрут</small><br><strong>${data.route}</strong></div></div>
                            <div class="col-md-4"><div class="card waybill-card p-3"><small><i class="fas fa-file-alt"></i> Путевой лист</small><br><strong>${data.waybill}</strong></div></div>
                        </div>
                    `;
                    loadHistory();
                    loadVehicles();
                } else {
                    addLog(`Ошибка: ${data.error || 'Неизвестная ошибка'}`, 'error');
                    document.getElementById('resultAlert').innerHTML = `<div class="alert alert-danger">❌ ${data.error || 'Ошибка выполнения'}</div>`;
                }
            } catch(e) {
                addLog(`Ошибка подключения: ${e.message}`, 'error');
                document.getElementById('resultAlert').innerHTML = `<div class="alert alert-danger">❌ Ошибка: ${e.message}</div>`;
            }
        }
        
        async function loadHistory() {
            try {
                const response = await fetch('/api/requests');
                const requests = await response.json();
                const tbody = document.getElementById('historyTable');
                if (requests.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center">Нет заявок</td></tr>';
                } else {
                    tbody.innerHTML = requests.map(r => `
                        <tr>
                            <td><code>${r.id}</code></td>
                            <td>${r.date || '-'}</td>
                            <td>${r.weight} кг</td>
                            <td>${r.pickup}</td>
                            <td>${r.delivery}</td>
                            <td>${r.transport || '-'}</td>
                            <td><span class="status-badge status-${r.status === 'success' ? 'success' : 'pending'}">${r.status || 'pending'}</span></td>
                        </tr>
                    `).join('');
                }
            } catch(e) {
                console.error(e);
            }
        }
        
        async function loadVehicles() {
            const vehicles = [
                { id: 'v1', driver: 'Иван', status: 'free', max_weight: 10000 },
                { id: 'v2', driver: 'Петр', status: 'free', max_weight: 8000 },
                { id: 'v3', driver: 'Сидор', status: 'on_route', max_weight: 12000 }
            ];
            const html = vehicles.map(v => `
                <div class="vehicle-card card p-3">
                    <div class="d-flex justify-content-between align-items-center">
                        <div><i class="fas fa-truck fa-2x text-primary me-3"></i></div>
                        <div><strong>${v.id}</strong> - ${v.driver}<br><small>Грузоподъемность: ${v.max_weight} кг</small></div>
                        <div><span class="status-badge status-${v.status === 'free' ? 'success' : 'progress'}">${v.status}</span></div>
                    </div>
                </div>
            `).join('');
            document.getElementById('vehiclesList').innerHTML = html;
        }
        
        setInterval(() => {
            const activeTab = document.querySelector('.nav-link.active');
            if (activeTab && activeTab.id === 'history-tab') loadHistory();
        }, 3000);
        
        loadHistory();
        loadVehicles();
    </script>
</body>
</html>
'''

requests_storage = []

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/create-request', methods=['POST'])
def create_request():
    data = request.json
    request_id = str(uuid.uuid4())[:8]
    
    # Имитация интеграции
    request_data = {
        'id': request_id,
        'weight': data.get('weight'),
        'volume': data.get('volume'),
        'cargo_type': data.get('cargo_type'),
        'pickup': data.get('pickup'),
        'delivery': data.get('delivery'),
        'deadline': data.get('deadline'),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'success',
        'transport': 'Автомобиль v1 (водитель Иван)',
        'route': 'Маршрут построен, расстояние 720 км',
        'waybill': f'Путевой лист №{request_id}'
    }
    requests_storage.insert(0, request_data)
    
    return jsonify({
        'status': 'success',
        'request_id': request_id,
        'transport': request_data['transport'],
        'route': request_data['route'],
        'waybill': request_data['waybill']
    })

@app.route('/api/requests', methods=['GET'])
def get_requests():
    return jsonify(requests_storage)

if __name__ == '__main__':
    print("="*50)
    print("СЕРВЕР ЗАПУЩЕН!")
    print("Открой браузер: http://localhost:5000")
    print("="*50)
    app.run(host='0.0.0.0', port=5000, debug=False)