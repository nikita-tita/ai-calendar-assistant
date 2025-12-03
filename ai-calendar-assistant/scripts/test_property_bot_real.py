#!/usr/bin/env python3
"""
Реальное тестирование поискового бота по недвижимости
с отправкой запросов через API и детальным логированием
"""

import asyncio
import aiohttp
import json
import random
import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Добавляем путь к приложению
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings

# Настройка логирования
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


class RealPropertyBotTester:
    """Тестер с реальными API вызовами"""

    def __init__(self):
        self.base_url = "http://localhost:8000"  # URL вашего API
        self.test_users = []
        self.results = []
        self.detailed_logs = []

    def generate_test_users(self, count: int = 30) -> List[Dict[str, Any]]:
        """Генерация тестовых пользователей с уникальными сценариями"""

        first_names = ["Алексей", "Мария", "Дмитрий", "Елена", "Сергей", "Анна",
                      "Иван", "Ольга", "Михаил", "Татьяна", "Андрей", "Наталья",
                      "Павел", "Светлана", "Николай", "Юлия", "Артем", "Екатерина",
                      "Владимир", "Ирина", "Петр", "Виктория", "Роман", "Дарья"]

        last_names = ["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов",
                     "Попов", "Васильев", "Соколов", "Морозов", "Новиков",
                     "Федоров", "Михайлов", "Александров", "Козлов", "Лебедев"]

        # Расширенные сценарии поиска
        scenarios = [
            {
                "name": "Молодая пара ищет первую квартиру",
                "queries": [
                    "Ищу 1 комнатную квартиру за 10 миллионов",
                    "Хочу чтобы рядом был парк для прогулок",
                    "Не больше 20 минут от метро пешком",
                    "Высокий этаж, от 10-го, чтобы вид был",
                    "Площадь не меньше 40 квадратов",
                    "Раздельный санузел обязательно",
                    "Подходит под ипотеку Сбербанка"
                ],
                "expected_features": ["парк", "высокий этаж", "раздельный санузел", "ипотека"]
            },
            {
                "name": "Семья с детьми ищет трешку",
                "queries": [
                    "Трешка для большой семьи",
                    "До 20 миллионов максимум",
                    "Рядом обязательно школа",
                    "И детский сад неподалеку",
                    "Площадь от 70 квадратов минимум",
                    "Два санузла нужно",
                    "Кухня больше 12 метров",
                    "Не первый и не последний этаж"
                ],
                "expected_features": ["школа", "детский сад", "два санузела", "большая кухня"]
            },
            {
                "name": "Инвестор ищет студию",
                "queries": [
                    "Студия для сдачи в аренду",
                    "Бюджет до 7 миллионов",
                    "Близко к метро, максимум 5 минут",
                    "Новостройка желательно",
                    "Развитый район с хорошей инфраструктурой"
                ],
                "expected_features": ["студия", "метро близко", "новостройка"]
            },
            {
                "name": "Двушка в спокойном районе",
                "queries": [
                    "2-комнатная квартира до 15 млн",
                    "В районе Крылатское или Строгино",
                    "С хорошим ремонтом",
                    "Окна во двор, чтобы тихо было",
                    "Балкон застеклен",
                    "Интеллигентный дом с хорошими соседями"
                ],
                "expected_features": ["ремонт", "тихо", "балкон"]
            },
            {
                "name": "Элитная квартира с видом",
                "queries": [
                    "Квартира с видом на воду",
                    "Бюджет до 25 миллионов",
                    "Панорамные окна обязательно",
                    "Высокий этаж от 15-го",
                    "Элитный жилой комплекс",
                    "С консьержем и охраной"
                ],
                "expected_features": ["вид на воду", "панорамные окна", "элитный", "охрана"]
            },
            {
                "name": "Компактная однушка для студента",
                "queries": [
                    "Однокомнатная квартира недорого",
                    "До 8 миллионов",
                    "Около университета или метро",
                    "Площадь 30-35 квадратов",
                    "С мебелью желательно"
                ],
                "expected_features": ["недорого", "компактная", "метро"]
            },
            {
                "name": "Просторная двушка для работы из дома",
                "queries": [
                    "Двухкомнатная квартира до 13 млн",
                    "Одна комната под кабинет",
                    "Хороший интернет в доме",
                    "Тихое место для работы",
                    "Балкон или лоджия",
                    "Площадь от 55 квадратов"
                ],
                "expected_features": ["тихо", "просторная", "балкон"]
            }
        ]

        users = []
        for i in range(count):
            # Генерируем уникальный ID
            user_id = 900000000 + random.randint(100000, 999999)

            # Случайное имя
            name = f"{random.choice(first_names)} {random.choice(last_names)}"

            # Выбираем сценарий (циклически или случайно)
            if i < len(scenarios):
                scenario = scenarios[i].copy()
            else:
                scenario = random.choice(scenarios).copy()

            # Добавляем вариации
            if random.random() > 0.7:
                # Укорачиваем список запросов
                scenario["queries"] = scenario["queries"][:random.randint(3, len(scenario["queries"]))]

            users.append({
                "user_id": user_id,
                "name": name,
                "scenario": scenario,
                "telegram_username": f"test_user_{user_id}"
            })

        self.test_users = users
        logger.info("test_users_generated", count=len(users))
        return users

    async def send_message_to_bot(
        self,
        user_id: int,
        message: str,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Отправка сообщения боту через API
        Имитация реального Telegram запроса
        """

        # Формируем запрос как от Telegram
        telegram_update = {
            "update_id": random.randint(100000000, 999999999),
            "message": {
                "message_id": random.randint(1000, 9999),
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": f"TestUser{user_id}",
                    "username": f"test_user_{user_id}"
                },
                "chat": {
                    "id": user_id,
                    "type": "private"
                },
                "date": int(datetime.now().timestamp()),
                "text": message
            }
        }

        logger.info("sending_message_to_bot",
                   user_id=user_id,
                   message=message[:50])

        try:
            # Отправляем через webhook endpoint
            async with session.post(
                f"{self.base_url}/telegram/webhook",
                json=telegram_update,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:

                status = response.status
                response_text = await response.text()

                logger.info("bot_response_received",
                           user_id=user_id,
                           status=status,
                           response_length=len(response_text))

                return {
                    "status": status,
                    "response": response_text,
                    "success": status == 200
                }

        except asyncio.TimeoutError:
            logger.error("bot_request_timeout", user_id=user_id)
            return {
                "status": 408,
                "response": "Timeout",
                "success": False,
                "error": "Request timeout"
            }
        except Exception as e:
            logger.error("bot_request_error",
                        user_id=user_id,
                        error=str(e),
                        exc_info=True)
            return {
                "status": 500,
                "response": str(e),
                "success": False,
                "error": str(e)
            }

    async def get_user_search_results(
        self,
        user_id: int,
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """Получение результатов поиска пользователя через API"""

        try:
            async with session.get(
                f"{self.base_url}/api/property/search-results/{user_id}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:

                if response.status == 200:
                    data = await response.json()
                    return data.get("results", [])
                else:
                    logger.warning("failed_to_get_results",
                                 user_id=user_id,
                                 status=response.status)
                    return []

        except Exception as e:
            logger.error("error_getting_results",
                        user_id=user_id,
                        error=str(e))
            return []

    async def check_bot_logs(
        self,
        user_id: int,
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """Проверка логов бота для конкретного пользователя"""

        try:
            async with session.get(
                f"{self.base_url}/api/logs/user/{user_id}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:

                if response.status == 200:
                    data = await response.json()
                    return data.get("logs", [])
                else:
                    return []

        except Exception as e:
            logger.error("error_checking_logs",
                        user_id=user_id,
                        error=str(e))
            return []

    async def test_user_scenario(
        self,
        user: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Полное тестирование сценария одного пользователя"""

        user_id = user["user_id"]
        name = user["name"]
        scenario = user["scenario"]

        logger.info("starting_user_test",
                   user_id=user_id,
                   name=name,
                   scenario_name=scenario["name"])

        print(f"\n{'='*80}")
        print(f"🧪 Тест: {name} (ID: {user_id})")
        print(f"📋 Сценарий: {scenario['name']}")
        print(f"{'='*80}\n")

        conversation_log = []
        all_responses = []

        # Отправляем серию запросов
        for i, query in enumerate(scenario["queries"], 1):
            print(f"👤 Запрос {i}/{len(scenario['queries'])}: {query}")

            # Отправляем сообщение
            response = await self.send_message_to_bot(user_id, query, session)

            conversation_log.append({
                "query_number": i,
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "response": response
            })

            if response["success"]:
                print(f"✅ Ответ получен (статус {response['status']})")
            else:
                print(f"❌ Ошибка: {response.get('error', 'Unknown')}")

            all_responses.append(response)

            # Задержка между запросами
            await asyncio.sleep(2)

        # Получаем финальные результаты поиска
        print(f"\n📊 Получение результатов поиска...")
        search_results = await self.get_user_search_results(user_id, session)

        print(f"🔍 Найдено объектов: {len(search_results)}")

        if search_results:
            print(f"\n🏆 Топ-3 результата:")
            for i, result in enumerate(search_results[:3], 1):
                print(f"  {i}. {result.get('title', 'Без названия')}")
                print(f"     Цена: {result.get('price', 'не указана')}")
                print(f"     Площадь: {result.get('area', 'не указана')} м²")
                print(f"     Релевантность: {result.get('relevance_score', 0):.1f}")

        # Проверяем логи
        print(f"\n📝 Проверка логов...")
        logs = await self.check_bot_logs(user_id, session)
        print(f"📜 Записей в логах: {len(logs)}")

        # Анализ качества результатов
        quality_score = self._analyze_result_quality(
            scenario,
            search_results,
            conversation_log
        )

        print(f"\n{'='*40}")
        print(f"📊 Оценка качества: {quality_score:.1f}/10")
        print(f"{'='*40}\n")

        return {
            "user": name,
            "user_id": user_id,
            "scenario": scenario["name"],
            "conversation_log": conversation_log,
            "search_results": search_results,
            "logs": logs,
            "quality_score": quality_score,
            "total_queries": len(scenario["queries"]),
            "successful_responses": sum(1 for r in all_responses if r["success"]),
            "found_properties": len(search_results),
            "timestamp": datetime.now().isoformat()
        }

    def _analyze_result_quality(
        self,
        scenario: Dict[str, Any],
        results: List[Dict[str, Any]],
        conversation: List[Dict[str, Any]]
    ) -> float:
        """Анализ качества результатов поиска"""

        score = 0.0

        # 1. Есть результаты (2 балла)
        if results:
            score += 2.0

        # 2. Количество результатов адекватно (2 балла)
        if 1 <= len(results) <= 20:
            score += 2.0

        # 3. Все запросы обработаны успешно (2 балла)
        successful_queries = sum(
            1 for entry in conversation
            if entry["response"]["success"]
        )
        success_rate = successful_queries / len(conversation) if conversation else 0
        score += success_rate * 2.0

        # 4. Соответствие ожидаемым фичам (4 балла)
        if results and "expected_features" in scenario:
            expected = scenario["expected_features"]
            best_result = results[0]

            # Проверяем наличие ожидаемых фич
            result_text = json.dumps(best_result, ensure_ascii=False).lower()
            matches = sum(1 for feature in expected if feature.lower() in result_text)

            feature_score = (matches / len(expected)) * 4.0 if expected else 0
            score += feature_score

        return min(score, 10.0)

    async def run_all_tests(self):
        """Запуск всех тестов"""

        print("\n" + "="*80)
        print("🚀 ЗАПУСК РЕАЛЬНОГО ТЕСТИРОВАНИЯ ПОИСКОВОГО БОТА")
        print("="*80 + "\n")

        # Генерируем пользователей
        print("📝 Генерация 30 тестовых пользователей...")
        users = self.generate_test_users(30)
        print(f"✅ Сгенерировано {len(users)} пользователей\n")

        # Проверяем доступность API
        print("🔌 Проверка доступности API...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        print("✅ API доступен\n")
                    else:
                        print(f"⚠️  API вернул статус {response.status}\n")
        except Exception as e:
            print(f"❌ API недоступен: {e}")
            print("💡 Убедитесь что бот запущен на {self.base_url}\n")
            return

        # Запускаем тесты
        results = []
        successful = 0
        failed = 0
        total_quality = 0

        async with aiohttp.ClientSession() as session:
            for i, user in enumerate(users, 1):
                print(f"\n{'🔹'*40}")
                print(f"Тест {i}/{len(users)}")
                print(f"{'🔹'*40}")

                try:
                    result = await self.test_user_scenario(user, session)
                    results.append(result)

                    if result["quality_score"] >= 7.0:
                        successful += 1
                    else:
                        failed += 1

                    total_quality += result["quality_score"]

                except Exception as e:
                    logger.error("test_failed",
                                user_id=user["user_id"],
                                error=str(e),
                                exc_info=True)
                    print(f"❌ Критическая ошибка теста: {e}\n")
                    failed += 1

                # Задержка между тестами
                await asyncio.sleep(3)

        # Итоговая статистика
        avg_quality = total_quality / len(users) if users else 0

        self.results = {
            "total_tests": len(users),
            "successful": successful,
            "failed": failed,
            "average_quality": avg_quality,
            "success_rate": (successful / len(users) * 100) if users else 0,
            "detailed_results": results,
            "timestamp": datetime.now().isoformat()
        }

        self._print_summary()
        self._save_results()

        return self.results

    def _print_summary(self):
        """Вывод итоговой статистики"""

        print("\n" + "="*80)
        print("📊 ИТОГОВАЯ СТАТИСТИКА РЕАЛЬНОГО ТЕСТИРОВАНИЯ")
        print("="*80 + "\n")

        r = self.results

        print(f"Всего тестов:              {r['total_tests']}")
        print(f"Успешных:                  {r['successful']} ({r['success_rate']:.1f}%)")
        print(f"Неудачных:                 {r['failed']}")
        print(f"Средняя оценка качества:   {r['average_quality']:.2f}/10")

        print("\n" + "-"*80)
        print("🏆 ТОП-5 ЛУЧШИХ РЕЗУЛЬТАТОВ:")
        print("-"*80 + "\n")

        sorted_results = sorted(
            r['detailed_results'],
            key=lambda x: x.get('quality_score', 0),
            reverse=True
        )

        for i, result in enumerate(sorted_results[:5], 1):
            print(f"{i}. {result['user']} (ID: {result['user_id']})")
            print(f"   Сценарий: {result['scenario']}")
            print(f"   Оценка: {result['quality_score']:.1f}/10")
            print(f"   Найдено: {result['found_properties']} объектов")
            print(f"   Успешных запросов: {result['successful_responses']}/{result['total_queries']}")
            print()

        print("-"*80)
        print("⚠️  ПРОБЛЕМНЫЕ СЛУЧАИ:")
        print("-"*80 + "\n")

        problem_results = [r for r in sorted_results if r.get('quality_score', 0) < 7.0]
        if problem_results:
            for i, result in enumerate(problem_results[:5], 1):
                print(f"{i}. {result['user']} (ID: {result['user_id']})")
                print(f"   Сценарий: {result['scenario']}")
                print(f"   Оценка: {result['quality_score']:.1f}/10")
                print(f"   Найдено: {result['found_properties']} объектов")
                print()
        else:
            print("✅ Проблемных случаев не обнаружено!\n")

        print("="*80 + "\n")

    def _save_results(self):
        """Сохранение результатов"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"property_bot_real_test_{timestamp}.json"
        filepath = Path(__file__).parent / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"💾 Результаты сохранены: {filepath}\n")


async def main():
    """Главная функция"""

    tester = RealPropertyBotTester()
    results = await tester.run_all_tests()

    # Код возврата
    if results['average_quality'] >= 8.0 and results['success_rate'] >= 80:
        print("✅ Тестирование пройдено успешно!")
        return 0
    elif results['average_quality'] >= 6.0 and results['success_rate'] >= 60:
        print("⚠️  Тестирование пройдено с замечаниями")
        return 1
    else:
        print("❌ Тестирование выявило серьезные проблемы")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
