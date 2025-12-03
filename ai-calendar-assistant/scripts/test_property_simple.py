#!/usr/bin/env python3
"""
Упрощенная версия тестирования поискового бота
Без зависимостей от базы данных и внешних API
"""

import json
import random
from typing import List, Dict, Any
from datetime import datetime


class SimplePropertyTester:
    """Упрощенный тестер"""

    def __init__(self):
        self.mock_properties = self._get_mock_properties()
        self.test_users = []

    def _get_mock_properties(self) -> List[Dict[str, Any]]:
        """Моковые данные недвижимости"""
        return [
            {
                "id": "mock_001",
                "title": "Уютная 1-комнатная квартира в Крылатском",
                "price": 9500000,
                "area": 42.5,
                "rooms": 1,
                "floor": 12,
                "floors_total": 25,
                "district": "Крылатское",
                "metro_time": 8,
                "description": "Уютная квартира в новом доме рядом с парком. Есть балкон, раздельный санузел. Подходит под ипотеку Сбербанка.",
                "features": ["парк рядом", "раздельный санузел", "балкон", "высокий этаж", "ипотека Сбербанк"]
            },
            {
                "id": "mock_002",
                "title": "Отличная 1-комнатная в Строгино с видом на парк",
                "price": 10200000,
                "area": 45.0,
                "rooms": 1,
                "floor": 15,
                "floors_total": 20,
                "district": "Строгино",
                "metro_time": 5,
                "description": "Отличная квартира с видом на парк. Высокий этаж, много света. Раздельный санузел. Ипотека одобрена.",
                "features": ["парк рядом", "раздельный санузел", "высокий этаж", "близко к метро", "ипотека"]
            },
            {
                "id": "mock_003",
                "title": "Просторная однушка в Тушино",
                "price": 9800000,
                "area": 41.0,
                "rooms": 1,
                "floor": 8,
                "floors_total": 17,
                "district": "Тушино",
                "metro_time": 15,
                "description": "Просторная однушка в тихом районе. Окна во двор. Санузел раздельный.",
                "features": ["раздельный санузел", "тихий район"]
            },
            {
                "id": "mock_004",
                "title": "Двухкомнатная квартира для семьи в Крылатском",
                "price": 14500000,
                "area": 65.0,
                "rooms": 2,
                "floor": 10,
                "floors_total": 16,
                "district": "Крылатское",
                "metro_time": 10,
                "description": "Отличная двушка для семьи. Рядом школа и детский сад. Развитая инфраструктура. С ремонтом.",
                "features": ["школа рядом", "детский сад", "ремонт"]
            },
            {
                "id": "mock_005",
                "title": "Студия в новостройке Митино",
                "price": 6800000,
                "area": 25.0,
                "rooms": 0,
                "floor": 5,
                "floors_total": 25,
                "district": "Митино",
                "metro_time": 3,
                "description": "Студия в новостройке. Отличное инвестиционное предложение. Рядом с метро.",
                "features": ["близко к метро", "новостройка"]
            },
            {
                "id": "mock_006",
                "title": "Трехкомнатная для большой семьи",
                "price": 19500000,
                "area": 75.0,
                "rooms": 3,
                "floor": 12,
                "floors_total": 20,
                "district": "Пресненская набережная",
                "metro_time": 7,
                "description": "Трехкомнатная квартира. Рядом школа и детские сады. Два санузла. Кухня 15 кв.м.",
                "features": ["школа рядом", "детский сад", "два санузла", "большая кухня"]
            },
            {
                "id": "mock_007",
                "title": "Элитная квартира с панорамными окнами",
                "price": 24000000,
                "area": 90.0,
                "rooms": 2,
                "floor": 18,
                "floors_total": 25,
                "district": "Живописная набережная",
                "metro_time": 5,
                "description": "Элитная квартира с панорамными окнами и видом на Москву-реку. Консьерж, охрана.",
                "features": ["панорамные окна", "вид на воду", "консьерж", "охрана", "высокий этаж"]
            },
        ]

    def generate_test_users(self, count: int = 30):
        """Генерация тестовых пользователей"""

        first_names = ["Алексей", "Мария", "Дмитрий", "Елена", "Сергей", "Анна",
                      "Иван", "Ольга", "Михаил", "Татьяна"]

        scenarios = [
            {
                "name": "Поиск 1-комнатной с уточнениями",
                "queries": [
                    "Ищу 1 комнатную квартиру за 10 миллионов",
                    "Хочу чтобы рядом был парк",
                    "Не больше 20 минут от метро",
                    "Высокий этаж, от 10-го",
                    "Площадь не меньше 40 квадратов",
                    "Раздельный санузел обязательно",
                    "Подходит под ипотеку Сбербанка"
                ],
                "expected_results": 2  # mock_001 и mock_002 должны подойти
            },
            {
                "name": "Поиск 2-комнатной в районе",
                "queries": [
                    "2-комнатная квартира до 15 млн",
                    "В районе Крылатское или Строгино",
                    "С ремонтом, готова к заселению"
                ],
                "expected_results": 1  # mock_004
            },
            {
                "name": "Студия для инвестиций",
                "queries": [
                    "Студия для сдачи в аренду",
                    "Бюджет до 7 миллионов",
                    "Рядом с метро, максимум 5 минут"
                ],
                "expected_results": 1  # mock_005
            },
        ]

        users = []
        for i in range(count):
            user_id = 900000000 + random.randint(1, 999999)
            name = random.choice(first_names)
            scenario = scenarios[i % len(scenarios)]

            users.append({
                "user_id": user_id,
                "name": name,
                "scenario": scenario
            })

        self.test_users = users
        return users

    def search_properties(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Простой поиск по критериям"""

        results = []

        for prop in self.mock_properties:
            score = 0
            skip = False

            # Обязательные критерии (hard filters)

            # Проверяем комнаты (если указано)
            if "rooms" in criteria:
                if prop["rooms"] != criteria["rooms"]:
                    skip = True

            # Проверяем цену (если указано)
            if "max_price" in criteria and not skip:
                if prop["price"] > criteria["max_price"]:
                    skip = True

            # Проверяем площадь (если указано)
            if "min_area" in criteria and not skip:
                if prop["area"] < criteria["min_area"]:
                    skip = True

            if skip:
                continue

            # Теперь считаем score для прошедших обязательную фильтрацию

            # Базовый балл за соответствие комнатам
            if "rooms" in criteria:
                score += 10

            # Балл за цену
            if "max_price" in criteria:
                score += 5

            # Балл за площадь
            if "min_area" in criteria and prop["area"] >= criteria["min_area"]:
                score += 5

            # Балл за этаж (soft requirement)
            if "min_floor" in criteria:
                if prop["floor"] >= criteria["min_floor"]:
                    score += 5

            # Балл за метро (soft requirement)
            if "max_metro_time" in criteria:
                if prop["metro_time"] <= criteria["max_metro_time"]:
                    score += 5

            # Балл за район (soft requirement)
            if "districts" in criteria:
                district_match = any(d.lower() in prop["district"].lower() for d in criteria["districts"])
                if district_match:
                    score += 5

            # Проверяем требования (soft requirements)
            if "requirements" in criteria:
                for req in criteria["requirements"]:
                    # Более гибкое сопоставление
                    req_lower = req.lower()
                    features_str = " ".join(prop.get("features", [])).lower()
                    desc_lower = prop["description"].lower()

                    if req_lower in features_str or req_lower in desc_lower:
                        score += 3

            if score > 0:
                prop_copy = prop.copy()
                prop_copy["relevance_score"] = score
                results.append(prop_copy)

        # Сортируем по релевантности
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return results

    def parse_query(self, query: str) -> Dict[str, Any]:
        """Простой парсинг запроса"""

        import re

        criteria = {}
        query_lower = query.lower()

        # Комнаты - используем более точные паттерны
        room_patterns = [
            (r'\bстуд', 0),
            (r'\b1[-\s]?комн|\bоднушк|\bоднокомн', 1),
            (r'\b2[-\s]?комн|\bдвушк|\bдвухкомн', 2),
            (r'\b3[-\s]?комн|\bтрешк|\bтрехкомн', 3),
        ]

        for pattern, rooms in room_patterns:
            if re.search(pattern, query_lower):
                criteria["rooms"] = rooms
                break

        # Цена
        price_match = re.search(r'(\d+)\s*(?:млн|миллион)', query_lower)
        if price_match:
            criteria["max_price"] = int(price_match.group(1)) * 1000000

        # Площадь
        area_match = re.search(r'(\d+)\s*квадрат', query_lower)
        if area_match:
            criteria["min_area"] = float(area_match.group(1))

        # Этаж
        if "высок" in query_lower and "этаж" in query_lower:
            criteria["min_floor"] = 10
        floor_match = re.search(r'(\d+).*этаж', query_lower)
        if floor_match:
            criteria["min_floor"] = int(floor_match.group(1))

        # Метро
        metro_patterns = [
            r'не\s+(?:более|больше)\s+(\d+)\s*минут',
            r'максимум\s+(\d+)\s*минут',
            r'(\d+)\s*минут.*(?:от\s+)?метро',
            r'метро.*(\d+)\s*минут',
        ]
        for pattern in metro_patterns:
            metro_match = re.search(pattern, query_lower)
            if metro_match:
                criteria["max_metro_time"] = int(metro_match.group(1))
                break

        # Требования
        requirements = []
        if "парк" in query_lower:
            requirements.append("парк")
        if "раздельн" in query_lower and "санузел" in query_lower:
            requirements.append("раздельный санузел")
        if "ипотек" in query_lower:
            requirements.append("ипотека")
        if "ремонт" in query_lower:
            requirements.append("ремонт")
        if "школ" in query_lower:
            requirements.append("школа")

        if requirements:
            criteria["requirements"] = requirements

        # Районы
        districts = []
        if "крылатск" in query_lower:
            districts.append("Крылатское")
        if "строгин" in query_lower:
            districts.append("Строгино")

        if districts:
            criteria["districts"] = districts

        return criteria

    def run_tests(self):
        """Запуск всех тестов"""

        print("\n" + "="*80)
        print("🧪 ЗАПУСК УПРОЩЕННЫХ ТЕСТОВ ПОИСКОВОГО БОТА")
        print("="*80 + "\n")

        # Генерация пользователей
        print("📝 Генерация 30 тестовых пользователей...")
        users = self.generate_test_users(30)
        print(f"✅ Сгенерировано {len(users)} пользователей\n")

        results = []
        successful = 0
        failed = 0
        total_satisfaction = 0

        for i, user in enumerate(users, 1):
            print(f"\n{'='*80}")
            print(f"Тест {i}/{len(users)}: {user['name']} (ID: {user['user_id']})")
            print(f"Сценарий: {user['scenario']['name']}")
            print(f"{'='*80}\n")

            accumulated_criteria = {}
            final_results = []

            for j, query in enumerate(user['scenario']['queries'], 1):
                print(f"👤 Запрос {j}: {query}")

                # Парсим запрос
                new_criteria = self.parse_query(query)

                # Объединяем критерии - обновляем только если новое значение есть
                for key, value in new_criteria.items():
                    if key == "requirements":
                        # Для требований - добавляем к существующим
                        if key not in accumulated_criteria:
                            accumulated_criteria[key] = []
                        accumulated_criteria[key].extend(value)
                    else:
                        # Для остальных - обновляем
                        accumulated_criteria[key] = value

                # Ищем
                search_results = self.search_properties(accumulated_criteria)

                print(f"🤖 Найдено: {len(search_results)} объектов")

                if search_results:
                    print(f"   Топ: {search_results[0]['title']}")
                    print(f"   Цена: {search_results[0]['price']:,} ₽")
                    print(f"   Релевантность: {search_results[0]['relevance_score']}")

                final_results = search_results

            # Оценка
            expected = user['scenario']['expected_results']
            found = len(final_results)

            satisfaction = 0
            if found >= expected and found > 0:
                satisfaction = 10.0
            elif found > 0:
                satisfaction = 7.0
            else:
                satisfaction = 0.0

            print(f"\n{'='*40}")
            print(f"📊 Оценка: {satisfaction}/10")
            print(f"   Ожидалось: {expected} объектов")
            print(f"   Найдено: {found} объектов")
            print(f"{'='*40}\n")

            if satisfaction >= 7:
                successful += 1
            else:
                failed += 1

            total_satisfaction += satisfaction

            results.append({
                "user": user['name'],
                "user_id": user['user_id'],
                "scenario": user['scenario']['name'],
                "found": found,
                "expected": expected,
                "satisfaction": satisfaction
            })

        # Итоговая статистика
        avg_satisfaction = total_satisfaction / len(users) if users else 0

        print("\n" + "="*80)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("="*80 + "\n")

        print(f"Всего тестов:              {len(users)}")
        print(f"Успешных:                  {successful} ({successful/len(users)*100:.1f}%)")
        print(f"Неудачных:                 {failed}")
        print(f"Средняя удовлетворенность: {avg_satisfaction:.2f}/10")

        print("\n" + "-"*80)
        print("🏆 ТОП-5 ЛУЧШИХ РЕЗУЛЬТАТОВ:")
        print("-"*80 + "\n")

        sorted_results = sorted(results, key=lambda x: x["satisfaction"], reverse=True)

        for i, result in enumerate(sorted_results[:5], 1):
            print(f"{i}. {result['user']} (ID: {result['user_id']})")
            print(f"   Сценарий: {result['scenario']}")
            print(f"   Оценка: {result['satisfaction']}/10")
            print(f"   Найдено: {result['found']} объектов (ожидалось {result['expected']})")
            print()

        # Сохранение результатов
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"property_bot_test_simple_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(users),
                "successful": successful,
                "failed": failed,
                "average_satisfaction": avg_satisfaction,
                "results": results
            }, f, ensure_ascii=False, indent=2)

        print(f"💾 Результаты сохранены: {filename}\n")
        print("="*80 + "\n")

        # Код возврата
        if avg_satisfaction >= 8.0:
            print("✅ Тестирование пройдено успешно!")
            return 0
        elif avg_satisfaction >= 6.0:
            print("⚠️  Тестирование пройдено с замечаниями")
            return 1
        else:
            print("❌ Тестирование провалено")
            return 2


if __name__ == "__main__":
    tester = SimplePropertyTester()
    exit_code = tester.run_tests()
    exit(exit_code)
