#!/usr/bin/env python3
"""
Комплексное тестирование поискового бота по недвижимости
с симуляцией 30 реальных пользователей и их диалогов
"""

import asyncio
import random
import json
import sys
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Добавляем путь к приложению
sys.path.append(str(Path(__file__).parent.parent))

from app.services.property.search_service import PropertySearchService
from app.services.property.feed_loader_wrapper import PropertyFeedLoader


class TestUser:
    """Тестовый пользователь с уникальными предпочтениями"""

    def __init__(self, user_id: int, name: str, scenario: Dict[str, Any]):
        self.user_id = user_id
        self.name = name
        self.scenario = scenario
        self.conversation_history = []
        self.found_properties = []
        self.satisfaction_score = 0

    def add_message(self, role: str, content: str):
        """Добавить сообщение в историю"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })


class PropertyBotTester:
    """Тестер бота по недвижимости"""

    def __init__(self):
        self.search_service = PropertySearchService()
        self.feed_loader = PropertyFeedLoader()
        self.test_users = []
        self.results = {
            "total_tests": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "average_satisfaction": 0,
            "detailed_results": []
        }

    def generate_test_users(self, count: int = 30) -> List[TestUser]:
        """Генерация тестовых пользователей с разными сценариями"""

        # Шаблоны имен
        first_names = ["Алексей", "Мария", "Дмитрий", "Елена", "Сергей", "Анна",
                      "Иван", "Ольга", "Михаил", "Татьяна", "Андрей", "Наталья",
                      "Павел", "Светлана", "Николай", "Юлия", "Артем", "Екатерина"]

        last_names = ["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов",
                     "Попов", "Васильев", "Соколов", "Морозов", "Новиков"]

        # Разнообразные сценарии поиска
        scenarios = [
            {
                "initial_query": "Ищу 1 комнатную квартиру за 10 миллионов",
                "refinements": [
                    "Хочу чтобы рядом был парк",
                    "Не больше 20 минут от метро",
                    "Высокий этаж, от 10-го",
                    "Площадь не меньше 40 квадратов",
                    "Раздельный санузел обязательно",
                    "Подходит под ипотеку Сбербанка"
                ],
                "expected_criteria": {
                    "rooms": 1,
                    "max_price": 10000000,
                    "near_park": True,
                    "max_metro_time": 20,
                    "min_floor": 10,
                    "min_area": 40,
                    "separate_bathroom": True,
                    "mortgage_compatible": "Сбербанк"
                }
            },
            {
                "initial_query": "2-комнатная квартира до 15 млн",
                "refinements": [
                    "В районе Крылатское или Строгино",
                    "С ремонтом, готова к заселению",
                    "Окна во двор, тихо",
                    "Балкон застеклен",
                    "Хорошие соседи, интеллигентный дом"
                ],
                "expected_criteria": {
                    "rooms": 2,
                    "max_price": 15000000,
                    "districts": ["Крылатское", "Строгино"],
                    "with_repair": True,
                    "quiet": True,
                    "glazed_balcony": True
                }
            },
            {
                "initial_query": "Студия для сдачи в аренду",
                "refinements": [
                    "Бюджет до 7 миллионов",
                    "Рядом с метро, максимум 5 минут",
                    "Новостройка с хорошей инфраструктурой",
                    "Развитый район для арендаторов"
                ],
                "expected_criteria": {
                    "rooms": 0,  # студия
                    "max_price": 7000000,
                    "max_metro_time": 5,
                    "new_building": True,
                    "investment_purpose": True
                }
            },
            {
                "initial_query": "Трешка для большой семьи",
                "refinements": [
                    "До 20 миллионов",
                    "Рядом школа и детский сад",
                    "Площадь от 70 квадратов",
                    "Два санузла",
                    "Кухня больше 12 метров",
                    "Не первый и не последний этаж"
                ],
                "expected_criteria": {
                    "rooms": 3,
                    "max_price": 20000000,
                    "near_school": True,
                    "near_kindergarten": True,
                    "min_area": 70,
                    "bathrooms": 2,
                    "min_kitchen_area": 12,
                    "avoid_edge_floors": True
                }
            },
            {
                "initial_query": "Квартира с видом на воду",
                "refinements": [
                    "Бюджет 25 млн",
                    "Панорамные окна",
                    "Высокий этаж от 15-го",
                    "Элитный жилой комплекс",
                    "Консьерж и охрана"
                ],
                "expected_criteria": {
                    "max_price": 25000000,
                    "water_view": True,
                    "panoramic_windows": True,
                    "min_floor": 15,
                    "elite_complex": True,
                    "concierge": True
                }
            }
        ]

        users = []
        for i in range(count):
            # Генерируем уникальный ID в диапазоне тестовых ID
            user_id = 900000000 + random.randint(1, 999999)

            # Случайное имя
            name = f"{random.choice(first_names)} {random.choice(last_names)}"

            # Случайный или циклический сценарий
            scenario = scenarios[i % len(scenarios)].copy()

            # Добавляем случайные вариации
            if random.random() > 0.7:
                scenario["refinements"] = scenario["refinements"][:random.randint(2, len(scenario["refinements"]))]

            user = TestUser(user_id, name, scenario)
            users.append(user)

        self.test_users = users
        return users

    async def simulate_conversation(self, user: TestUser) -> Dict[str, Any]:
        """Симуляция полного диалога с пользователем"""

        print(f"\n{'='*80}")
        print(f"🧪 Тестирование пользователя: {user.name} (ID: {user.user_id})")
        print(f"{'='*80}\n")

        # Начальный запрос
        initial_query = user.scenario["initial_query"]
        print(f"👤 Пользователь: {initial_query}")
        user.add_message("user", initial_query)

        # Первый поиск
        try:
            initial_results = await self.search_service.search_properties(
                user_id=user.user_id,
                query=initial_query
            )

            print(f"🤖 Бот: Найдено {len(initial_results)} объектов")
            user.add_message("bot", f"Найдено {len(initial_results)} объектов")

            if initial_results:
                print(f"   Например: {initial_results[0].get('title', 'Без названия')}")
                print(f"   Цена: {initial_results[0].get('price', 'не указана')}")
        except Exception as e:
            print(f"❌ Ошибка первого поиска: {e}")
            return {
                "user": user.name,
                "user_id": user.user_id,
                "status": "failed",
                "error": str(e),
                "stage": "initial_search"
            }

        # Уточнения
        all_results = initial_results
        for i, refinement in enumerate(user.scenario["refinements"], 1):
            print(f"\n👤 Пользователь (уточнение {i}): {refinement}")
            user.add_message("user", refinement)

            try:
                # Поиск с учетом уточнения
                refined_results = await self.search_service.search_properties(
                    user_id=user.user_id,
                    query=refinement,
                    previous_results=all_results
                )

                print(f"🤖 Бот: Уточненный поиск, найдено {len(refined_results)} объектов")
                user.add_message("bot", f"Найдено {len(refined_results)} подходящих объектов")

                all_results = refined_results

                if refined_results:
                    print(f"   Лучший вариант: {refined_results[0].get('title', 'Без названия')}")
                    print(f"   Цена: {refined_results[0].get('price', 'не указана')}")
                    print(f"   Площадь: {refined_results[0].get('area', 'не указана')} м²")

                # Небольшая задержка между запросами
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"⚠️  Ошибка при уточнении {i}: {e}")
                user.add_message("bot", f"Ошибка обработки: {e}")

        # Финальная оценка результатов
        satisfaction_score = self._evaluate_results(user, all_results)
        user.satisfaction_score = satisfaction_score
        user.found_properties = all_results[:5]  # топ-5

        print(f"\n{'='*40}")
        print(f"📊 Оценка удовлетворенности: {satisfaction_score:.1f}/10")
        print(f"{'='*40}\n")

        return {
            "user": user.name,
            "user_id": user.user_id,
            "status": "success",
            "total_messages": len(user.conversation_history),
            "found_properties": len(all_results),
            "top_properties": all_results[:3],
            "satisfaction_score": satisfaction_score,
            "conversation": user.conversation_history
        }

    def _evaluate_results(self, user: TestUser, results: List[Dict]) -> float:
        """Оценка качества результатов поиска"""

        score = 0.0
        max_score = 10.0

        # Критерии оценки
        if not results:
            return 0.0

        # 1. Найдены результаты (2 балла)
        score += 2.0

        # 2. Количество результатов адекватно (не слишком мало, не слишком много)
        if 3 <= len(results) <= 20:
            score += 2.0
        elif len(results) > 0:
            score += 1.0

        # 3. Проверка соответствия критериям из сценария
        expected = user.scenario.get("expected_criteria", {})
        if results:
            best_match = results[0]

            # Проверяем основные критерии
            criteria_match = 0
            total_criteria = 0

            # Цена
            if "max_price" in expected:
                total_criteria += 1
                try:
                    price = best_match.get("price", "")
                    if isinstance(price, str):
                        price = int(''.join(filter(str.isdigit, price)))
                    if price <= expected["max_price"]:
                        criteria_match += 1
                except:
                    pass

            # Количество комнат
            if "rooms" in expected:
                total_criteria += 1
                if str(best_match.get("rooms", "")) == str(expected["rooms"]):
                    criteria_match += 1

            # Площадь
            if "min_area" in expected:
                total_criteria += 1
                try:
                    area = float(best_match.get("area", 0))
                    if area >= expected["min_area"]:
                        criteria_match += 1
                except:
                    pass

            # Добавляем баллы за соответствие критериям
            if total_criteria > 0:
                criteria_score = (criteria_match / total_criteria) * 4.0
                score += criteria_score

        # 4. Разнообразие результатов (2 балла)
        if len(results) >= 3:
            unique_prices = len(set(str(r.get("price", "")) for r in results[:5]))
            if unique_prices >= 3:
                score += 2.0
            else:
                score += 1.0

        return min(score, max_score)

    async def run_all_tests(self):
        """Запуск всех тестов"""

        print("\n" + "="*80)
        print("🚀 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ ПОИСКОВОГО БОТА")
        print("="*80 + "\n")

        # Генерируем пользователей
        print("📝 Генерация 30 тестовых пользователей...")
        users = self.generate_test_users(30)
        print(f"✅ Сгенерировано {len(users)} пользователей\n")

        # Загружаем фид
        print("📥 Загрузка данных из фида...")
        try:
            properties = await self.feed_loader.load_feed()
            print(f"✅ Загружено {len(properties)} объектов из фида\n")
        except Exception as e:
            print(f"⚠️  Предупреждение: не удалось загрузить фид: {e}\n")

        # Запускаем тесты для каждого пользователя
        results = []
        successful = 0
        failed = 0
        total_satisfaction = 0

        for i, user in enumerate(users, 1):
            print(f"\n{'🔹'*40}")
            print(f"Тест {i}/{len(users)}")
            print(f"{'🔹'*40}")

            try:
                result = await self.simulate_conversation(user)
                results.append(result)

                if result["status"] == "success":
                    successful += 1
                    total_satisfaction += result["satisfaction_score"]
                else:
                    failed += 1

            except Exception as e:
                print(f"❌ Критическая ошибка теста: {e}")
                failed += 1
                results.append({
                    "user": user.name,
                    "user_id": user.user_id,
                    "status": "failed",
                    "error": str(e)
                })

            # Пауза между тестами
            await asyncio.sleep(1)

        # Подсчет итоговой статистики
        avg_satisfaction = total_satisfaction / successful if successful > 0 else 0

        self.results = {
            "total_tests": len(users),
            "successful_searches": successful,
            "failed_searches": failed,
            "average_satisfaction": avg_satisfaction,
            "success_rate": (successful / len(users) * 100),
            "detailed_results": results,
            "timestamp": datetime.now().isoformat()
        }

        # Вывод итоговой статистики
        self._print_summary()

        # Сохранение результатов
        self._save_results()

        return self.results

    def _print_summary(self):
        """Вывод итоговой статистики"""

        print("\n" + "="*80)
        print("📊 ИТОГОВАЯ СТАТИСТИКА ТЕСТИРОВАНИЯ")
        print("="*80 + "\n")

        r = self.results

        print(f"Всего тестов:              {r['total_tests']}")
        print(f"Успешных поисков:          {r['successful_searches']} ({r['success_rate']:.1f}%)")
        print(f"Неудачных поисков:         {r['failed_searches']}")
        print(f"Средняя удовлетворенность: {r['average_satisfaction']:.2f}/10")

        print("\n" + "-"*80)
        print("🏆 ТОП-5 ЛУЧШИХ РЕЗУЛЬТАТОВ:")
        print("-"*80 + "\n")

        # Сортируем по удовлетворенности
        sorted_results = sorted(
            [r for r in r['detailed_results'] if r['status'] == 'success'],
            key=lambda x: x.get('satisfaction_score', 0),
            reverse=True
        )

        for i, result in enumerate(sorted_results[:5], 1):
            print(f"{i}. {result['user']} (ID: {result['user_id']})")
            print(f"   Оценка: {result['satisfaction_score']:.1f}/10")
            print(f"   Найдено объектов: {result['found_properties']}")
            if result.get('top_properties'):
                print(f"   Лучший вариант: {result['top_properties'][0].get('title', 'Без названия')}")
            print()

        print("-"*80)
        print("⚠️  ПРОБЛЕМНЫЕ СЛУЧАИ:")
        print("-"*80 + "\n")

        failed_results = [r for r in r['detailed_results'] if r['status'] == 'failed']
        if failed_results:
            for i, result in enumerate(failed_results[:5], 1):
                print(f"{i}. {result['user']} (ID: {result['user_id']})")
                print(f"   Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                print(f"   Этап: {result.get('stage', 'Неизвестно')}")
                print()
        else:
            print("✅ Проблемных случаев не обнаружено!\n")

        print("="*80 + "\n")

    def _save_results(self):
        """Сохранение результатов в файл"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"property_bot_test_results_{timestamp}.json"
        filepath = Path(__file__).parent / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"💾 Результаты сохранены: {filepath}\n")


async def main():
    """Главная функция"""

    tester = PropertyBotTester()
    results = await tester.run_all_tests()

    # Возвращаем код выхода в зависимости от результатов
    if results['success_rate'] >= 80 and results['average_satisfaction'] >= 7.0:
        print("✅ Тестирование пройдено успешно!")
        return 0
    elif results['success_rate'] >= 60:
        print("⚠️  Тестирование пройдено с замечаниями")
        return 1
    else:
        print("❌ Тестирование провалено")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
