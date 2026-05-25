import requests
import json
import logging
from datetime import datetime

# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== АДРЕСА МОДУЛЕЙ =====
REQUEST_SERVICE_URL = "http://localhost:5001"
TRANSPORT_SERVICE_URL = "http://localhost:5002"
ROUTE_SERVICE_URL = "http://localhost:3000"


class TransportOrchestrator:
    """
    Интеграционный слой (оркестратор) для транспортной логистики
    Координирует: Заявки → Транспорт → Маршруты
    """
    
    def __init__(self):
        logger.info("Оркестратор инициализирован")
    
    def create_transport_request(self, cargo_weight_kg, pickup_address, delivery_address):
        """
        Основной метод: создаёт заявку, находит транспорт, строит маршрут
        """
        logger.info(f"Начало процесса: вес={cargo_weight_kg}кг, адреса={pickup_address}→{delivery_address}")
        
        # ===== ШАГ 1: Создать заявку (модуль Request Service) =====
        request_data = {
            "cargo_weight_kg": cargo_weight_kg,
            "pickup_address": pickup_address,
            "delivery_address": delivery_address,
            "cargo_volume_m3": 10
        }
        
        logger.info(f"Вызов модуля Request: POST {REQUEST_SERVICE_URL}/requests")
        response1 = requests.post(f"{REQUEST_SERVICE_URL}/requests", json=request_data)
        
        if response1.status_code != 201:
            logger.error(f"Ошибка при создании заявки: {response1.status_code}")
            return None
        
        request_result = response1.json()
        request_id = request_result.get('request_id')
        logger.info(f"Заявка создана: ID={request_id}")
        
        # ===== ШАГ 2: Найти доступный транспорт (модуль Transport Service) =====
        logger.info(f"Вызов модуля Transport: GET {TRANSPORT_SERVICE_URL}/vehicles/available?weight_kg={cargo_weight_kg}")
        response2 = requests.get(f"{TRANSPORT_SERVICE_URL}/vehicles/available", params={"weight_kg": cargo_weight_kg})
        
        if response2.status_code != 200:
            logger.error(f"Ошибка при проверке транспорта: {response2.status_code}")
            return None
        
        vehicles = response2.json()
        if not vehicles:
            logger.warning("Нет доступного транспорта!")
            return {"status": "no_vehicles_available", "request_id": request_id}
        
        selected_vehicle = vehicles[0]
        logger.info(f"Найден транспорт: {selected_vehicle}")
        
        # ===== ШАГ 3: Построить маршрут (модуль Route Service) =====
        route_data = {
            "vehicle_id": selected_vehicle.get('id'),
            "waypoints": [
                {"address": pickup_address, "type": "pickup"},
                {"address": delivery_address, "type": "delivery"}
            ]
        }
        
        logger.info(f"Вызов модуля Route: POST {ROUTE_SERVICE_URL}/routes/build")
        response3 = requests.post(f"{ROUTE_SERVICE_URL}/routes/build", json=route_data)
        
        if response3.status_code != 201:
            logger.error(f"Ошибка при построении маршрута: {response3.status_code}")
            return None
        
        route_result = response3.json()
        logger.info(f"Маршрут построен: ID={route_result.get('route_id')}, расстояние={route_result.get('distance_km')}км")
        
        # ===== РЕЗУЛЬТАТ =====
        result = {
            "status": "success",
            "request_id": request_id,
            "vehicle": selected_vehicle,
            "route": route_result
        }
        
        logger.info(f"Процесс завершён успешно: {json.dumps(result, indent=2)}")
        return result


def main():
    """Демонстрация работы оркестратора"""
    print("\n" + "="*60)
    print("ТРАНСПОРТНЫЙ ОРКЕСТРАТОР - ИНТЕГРАЦИОННЫЙ СЛОЙ")
    print("="*60 + "\n")
    
    orchestrator = TransportOrchestrator()
    
    # Тестовые данные
    result = orchestrator.create_transport_request(
        cargo_weight_kg=5000,
        pickup_address="Москва, ул. Тверская 1",
        delivery_address="Санкт-Петербург, Невский пр. 10"
    )
    
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТ РАБОТЫ:")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\nЛоги сохранены в файл: integration.log")


if __name__ == "__main__":
    main()