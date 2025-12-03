#!/usr/bin/env python3
"""
Исправленное тестирование с реальной БД и regex fallback
"""

import asyncio
import sys
import re
from pathlib import Path
import structlog
from datetime import datetime
import json
import random

sys.path.append(str(Path(__file__).parent.parent))

from app.services.property.property_service import PropertyService
from app.models.property import PropertyListing, DealType

logger = structlog.get_logger()


class FixedPropertyTester:
    """Тестер с исправленной логикой"""

    def __init__(self):
        self.property_service = PropertyService()

    def parse_query_with_regex(self, query: str, accumulated: dict) -> dict:
        """Regex парсинг запросов (fallback)"""

        criteria = accumulated.copy()
        query_lower = query.lower()

        # Комнаты
        room_patterns = [
            (r'\bстуд', 0),
            (r'\b1[-\s]?к|\bоднушк|\bоднокомн', 1),
            (r'\b2[-\s]?к|\bдвушк|\bдвухкомн', 2),
            (r'\b3[-\s]?к|\bтрешк|\bтрехкомн', 3),
        ]
        for pattern, rooms in room_patterns:
            if re.search(pattern, query_lower):
                criteria['rooms'] = rooms
                break

        # Цена
        price_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:млн|миллион)', lambda x: float(x) * 1000000),
            (r'(\d+)\s*(?:тыс|тысяч)', lambda x: float(x) * 1000),
        ]

        for pattern, converter in price_patterns:
            match = re.search(pattern, query_lower)
            if match:
                value = converter(match.group(1))

                if 'до' in query_lower or 'максимум' in query_lower:
                    criteria['price_max'] = int(value)
                elif 'от' in query_lower or 'минимум' in query_lower:
                    criteria['price_min'] = int(value)
                elif '-' in query:
                    # Диапазон типа "15-16 млн"
                    criteria['price_min'] = int(value * 0.9)  # примерно от
                    criteria['price_max'] = int(value)
                else:
                    criteria['price_max'] = int(value)
                break

        # Площадь
        area_match = re.search(r'(\d+)\s*(?:квадрат|кв\.?\s*м|м²)', query_lower)
        if area_match:
            area_value = float(area_match.group(1))
            if 'от' in query_lower or 'больше' in query_lower or 'не меньше' in query_lower:
                criteria['area_min'] = area_value
            elif 'около' in query_lower:
                criteria['area_min'] = area_value - 5
                criteria['area_max'] = area_value + 5
            else:
                criteria['area_min'] = area_value

        # Районы
        districts = []
        district_names = [
            'Выборгский', 'Приморский', 'Калининский',
            'Московский', 'Невский', 'Фрунзенский',
            'Красногвардейский', 'Центральный'
        ]

        for district in district_names:
            if district.lower() in query_lower:
                districts.append(district)

        if districts:
            criteria['districts'] = districts

        # Ипотека
        if 'ипотек' in query_lower:
            criteria['mortgage'] = True
            if 'сбер' in query_lower:
                criteria['mortgage_bank'] = 'Сбербанк'

        # Deal type
        if 'купить' in query_lower or 'купля' in query_lower or 'покупка' in query_lower:
            criteria['deal_type'] = 'buy'
        elif 'аренд' in query_lower or 'снять' in query_lower:
            criteria['deal_type'] = 'rent'
        else:
            criteria['deal_type'] = 'buy'  # по умолчанию

        return criteria

    async def search_with_criteria(self, criteria: dict):
        """Поиск в БД с правильными критериями"""

        logger.info("searching_with_criteria", criteria=criteria)

        session = self.property_service.get_session()

        try:
            # Формируем запрос
            query = session.query(PropertyListing)

            # Deal type
            if 'deal_type' in criteria:
                deal = DealType.buy if criteria['deal_type'] == 'buy' else DealType.rent
                query = query.filter(PropertyListing.deal_type == deal)

            # Цена
            if 'price_min' in criteria:
                query = query.filter(PropertyListing.price >= criteria['price_min'])
            if 'price_max' in criteria:
                query = query.filter(PropertyListing.price <= criteria['price_max'])

            # Комнаты
            if 'rooms' in criteria:
                query = query.filter(PropertyListing.rooms == criteria['rooms'])

            # Площадь
            if 'area_min' in criteria:
                query = query.filter(PropertyListing.area_total >= criteria['area_min'])
            if 'area_max' in criteria:
                query = query.filter(PropertyListing.area_total <= criteria['area_max'])

            # Районы
            if 'districts' in criteria:
                from sqlalchemy import or_
                district_filters = [
                    PropertyListing.district.ilike(f'%{d}%')
                    for d in criteria['districts']
                ]
                query = query.filter(or_(*district_filters))

            # Выполняем запрос
            results = query.limit(20).all()

            logger.info("search_completed",
                       found=len(results),
                       criteria=criteria)

            return results

        except Exception as e:
            logger.error("search_error", error=str(e), exc_info=True)
            return []
        finally:
            session.close()

    def generate_30_test_scenarios(self):
        """30 тестовых пользователей"""

        first_names = ["Алексей", "Мария", "Дмитрий", "Елена", "Сергей", "Анна",
                      "Иван", "Ольга", "Михаил", "Татьяна", "Андрей", "Наталья",
                      "Павел", "Светлана", "Николай", "Юлия", "Артем", "Екатерина",
                      "Владимир", "Ирина", "Петр", "Виктория", "Роман", "Дарья",
                      "Максим", "Оксана", "Игорь", "Вера", "Константин", "Людмила"]

        scenarios_templates = [
            {
                "queries": [
                    "Ищу двухкомнатную квартиру",
                    "До 16 миллионов",
                    "В Выборгском районе",
                    "Площадь от 65 квадратов"
                ],
                "expected": {"rooms": 2, "district": "Выборгский"}
            },
            {
                "queries": [
                    "Двушка до 18 млн",
                    "Приморский район",
                    "Площадь от 68 квадратов"
                ],
                "expected": {"rooms": 2, "district": "Приморский"}
            },
            {
                "queries": [
                    "2-комнатная для семьи",
                    "Бюджет до 19 миллионов",
                    "Подходит под ипотеку Сбербанка"
                ],
                "expected": {"rooms": 2, "mortgage": "Сбер"}
            },
            {
                "queries": [
                    "Ищу двухкомнатную",
                    "15-16 миллионов",
                    "Выборгский район"
                ],
                "expected": {"rooms": 2, "district": "Выборгский"}
            },
            {
                "queries": [
                    "Двушка в Калининском",
                    "До 18 млн",
                    "Площадь около 70 квадратов"
                ],
                "expected": {"rooms": 2, "district": "Калининский"}
            },
        ]

        scenarios = []
        for i in range(30):
            template = scenarios_templates[i % len(scenarios_templates)]
            scenarios.append({
                "user_id": 900000000 + i + 1,
                "name": first_names[i],
                "queries": template["queries"],
                "expected": template["expected"]
            })

        return scenarios

    async def test_scenario(self, scenario):
        """Тестирование одного сценария"""

        user_id = scenario['user_id']
        name = scenario['name']

        print(f"\n{'='*70}")
        print(f"👤 {name} (ID: {user_id})")
        print(f"{'='*70}\n")

        accumulated_criteria = {}
        all_results = []

        for i, query in enumerate(scenario['queries'], 1):
            print(f"  📝 Запрос {i}: {query}")

            # Парсим запрос
            accumulated_criteria = self.parse_query_with_regex(query, accumulated_criteria)

            print(f"     Критерии: {accumulated_criteria}")

            # Ищем в БД
            results = await self.search_with_criteria(accumulated_criteria)

            print(f"     ✅ Найдено: {len(results)} объектов")

            if results:
                for j, res in enumerate(results[:3], 1):
                    print(f"        {j}. {res.title} - {res.price:,}₽ - {res.area_total}м² - {res.district}")

            all_results = results
            await asyncio.sleep(0.5)

        # Проверяем соответствие ожиданиям
        score = self._calculate_score(all_results, scenario['expected'])

        print(f"\n  📊 Оценка: {score:.1f}/10")
        print(f"  🎯 Найдено объектов: {len(all_results)}")

        return {
            "user_id": user_id,
            "name": name,
            "queries": scenario['queries'],
            "criteria": accumulated_criteria,
            "found": len(all_results),
            "results": [
                {
                    "title": r.title,
                    "price": r.price,
                    "rooms": r.rooms,
                    "area": r.area_total,
                    "district": r.district
                }
                for r in all_results[:5]
            ],
            "score": score
        }

    def _calculate_score(self, results, expected):
        """Оценка качества результатов"""

        score = 0.0

        # Есть результаты (+3 балла)
        if results:
            score += 3.0
        else:
            return 0.0

        # Правильное количество комнат (+3 балла)
        if 'rooms' in expected:
            if any(r.rooms == expected['rooms'] for r in results):
                score += 3.0

        # Правильный район (+2 балла)
        if 'district' in expected:
            if any(expected['district'] in (r.district or '') for r in results):
                score += 2.0

        # Есть ипотека (+2 балла)
        if 'mortgage' in expected:
            results_text = ' '.join([r.title + ' ' + (r.description or '') for r in results])
            if expected['mortgage'].lower() in results_text.lower():
                score += 2.0

        return min(score, 10.0)

    async def run_all_tests(self):
        """Запуск всех 30 тестов"""

        print("\n" + "="*80)
        print("🧪 ТЕСТИРОВАНИЕ ПОИСКОВОГО БОТА С РЕАЛЬНОЙ БД (30 ПОЛЬЗОВАТЕЛЕЙ)")
        print("="*80 + "\n")

        # Проверяем БД
        print("🔌 Проверка базы данных...")
        session = self.property_service.get_session()
        try:
            count = session.query(PropertyListing).count()
            print(f"✅ Объектов в БД: {count}")

            # Показываем примеры
            samples = session.query(PropertyListing).limit(3).all()
            print("\n📋 Примеры объектов:")
            for s in samples:
                print(f"   • {s.title} - {s.price:,}₽ - {s.rooms}к - {s.area_total}м² - {s.district}")
            print()
        finally:
            session.close()

        # Генерируем сценарии
        scenarios = self.generate_30_test_scenarios()
        print(f"📝 Создано {len(scenarios)} тестовых сценариев\n")

        # Запускаем тесты
        results = []
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'🔹'*35}")
            print(f"ТЕСТ {i}/30")
            print(f"{'🔹'*35}")

            try:
                result = await self.test_scenario(scenario)
                results.append(result)
            except Exception as e:
                logger.error("test_error", scenario=scenario, error=str(e))
                print(f"❌ Ошибка: {e}")

        # Итоги
        self._print_summary(results)
        self._save_results(results)

        return results

    def _print_summary(self, results):
        """Итоговая статистика"""

        print("\n" + "="*80)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("="*80 + "\n")

        total = len(results)
        successful = sum(1 for r in results if r['score'] >= 7.0)
        avg_score = sum(r['score'] for r in results) / total if total > 0 else 0
        total_found = sum(r['found'] for r in results)

        print(f"Всего тестов:              {total}")
        print(f"Успешных (≥7.0):           {successful} ({successful/total*100:.1f}%)")
        print(f"Средний балл:              {avg_score:.2f}/10")
        print(f"Всего найдено объектов:    {total_found}")

        print("\n" + "-"*80)
        print("🏆 ТОП-5 ЛУЧШИХ РЕЗУЛЬТАТОВ:")
        print("-"*80 + "\n")

        sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
        for i, r in enumerate(sorted_results[:5], 1):
            print(f"{i}. {r['name']} (ID: {r['user_id']})")
            print(f"   Балл: {r['score']:.1f}/10")
            print(f"   Найдено: {r['found']} объектов")
            if r['results']:
                print(f"   Лучший: {r['results'][0]['title']}")
            print()

        if successful < total * 0.5:
            print("-"*80)
            print("⚠️  ПРОБЛЕМНЫЕ СЛУЧАИ:")
            print("-"*80 + "\n")

            failed = [r for r in results if r['score'] < 7.0]
            for i, r in enumerate(failed[:5], 1):
                print(f"{i}. {r['name']} - Балл: {r['score']:.1f}/10")
                print(f"   Критерии: {r['criteria']}")
                print(f"   Найдено: {r['found']} объектов")
                print()

    def _save_results(self, results):
        """Сохранение результатов"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_fixed_{timestamp}.json"
        filepath = Path(__file__).parent / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(results),
                "successful": sum(1 for r in results if r['score'] >= 7.0),
                "average_score": sum(r['score'] for r in results) / len(results),
                "results": results
            }, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n💾 Результаты сохранены: {filename}")


async def main():
    tester = FixedPropertyTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
