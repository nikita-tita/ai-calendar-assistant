#!/usr/bin/env python3
"""
Тестирование с реальной БД объектов недвижимости
Использует существующую инфраструктуру property bot
"""

import asyncio
import sys
from pathlib import Path
import structlog
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))

from app.services.property.property_service import PropertyService
from app.services.property.llm_agent_property import PropertyLLMAgent

logger = structlog.get_logger()


class RealDatabaseTester:
    """Тестер с реальной БД"""

    def __init__(self):
        self.property_service = PropertyService()
        self.llm_agent = PropertyLLMAgent()
        self.test_results = []

    def generate_test_scenarios(self):
        """Генерация тестовых сценариев для реальных объектов"""

        return [
            {
                "user_id": 900000001,
                "name": "Алексей Иванов",
                "queries": [
                    "Ищу двухкомнатную квартиру",
                    "До 16 миллионов",
                    "В Выборгском или Приморском районе",
                    "Площадь не меньше 65 квадратов"
                ],
                "expected_matches": ["Выборгский", "Приморский"]
            },
            {
                "user_id": 900000002,
                "name": "Мария Петрова",
                "queries": [
                    "Двушка до 18 млн",
                    "Приморский район предпочтительно",
                    "Площадь от 68 квадратов"
                ],
                "expected_matches": ["Приморский"]
            },
            {
                "user_id": 900000003,
                "name": "Дмитрий Сидоров",
                "queries": [
                    "2-комнатная квартира для семьи",
                    "Бюджет до 19 миллионов",
                    "Подходит под ипотеку Сбербанка",
                    "Площадь больше 70 квадратов"
                ],
                "expected_matches": ["Сбер", "ипотека"]
            },
            {
                "user_id": 900000004,
                "name": "Елена Смирнова",
                "queries": [
                    "Ищу двухкомнатную",
                    "15-16 миллионов",
                    "Выборгский район"
                ],
                "expected_matches": ["Выборгский"]
            },
            {
                "user_id": 900000005,
                "name": "Сергей Козлов",
                "queries": [
                    "Двушка в Калининском",
                    "До 18 млн",
                    "Площадь около 70 квадратов"
                ],
                "expected_matches": ["Калининский"]
            }
        ]

    async def test_search_with_criteria(self, user_id: str, queries: list):
        """Тестирование поиска с накоплением критериев"""

        print(f"\n{'='*60}")
        print(f"Тестирование пользователя {user_id}")
        print(f"{'='*60}\n")

        # Накапливаем критерии через LLM агента
        all_criteria = {}
        conversation_history = []

        for i, query in enumerate(queries, 1):
            print(f"📝 Запрос {i}: {query}")

            conversation_history.append({
                "role": "user",
                "content": query
            })

            try:
                # Извлекаем критерии через LLM
                criteria = await self.llm_agent.extract_search_criteria(
                    user_message=query,
                    user_id=user_id,
                    conversation_history=conversation_history
                )

                print(f"   Извлеченные критерии: {criteria}")

                # Объединяем с предыдущими
                all_criteria.update(criteria)

                # Поиск в БД
                results = await self.property_service.search_listings(
                    deal_type=all_criteria.get("deal_type"),
                    price_min=all_criteria.get("min_price"),
                    price_max=all_criteria.get("max_price"),
                    rooms_min=all_criteria.get("rooms"),
                    rooms_max=all_criteria.get("rooms"),
                    area_min=all_criteria.get("min_area"),
                    districts=all_criteria.get("districts"),
                    limit=10
                )

                print(f"   ✅ Найдено: {len(results)} объектов")

                if results:
                    for j, res in enumerate(results[:3], 1):
                        print(f"      {j}. {res.title}")
                        print(f"         Цена: {res.price:,} ₽")
                        print(f"         Площадь: {res.area_total} м²")
                        print(f"         Район: {res.district}")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                logger.error("search_error", user_id=user_id, error=str(e))

        return {
            "user_id": user_id,
            "total_queries": len(queries),
            "final_criteria": all_criteria,
            "final_results": results if results else []
        }

    async def run_all_tests(self):
        """Запуск всех тестов"""

        print("\n" + "="*80)
        print("🧪 ТЕСТИРОВАНИЕ С РЕАЛЬНОЙ БАЗОЙ ДАННЫХ")
        print("="*80 + "\n")

        # Проверяем подключение к БД
        print("🔌 Проверка подключения к БД...")
        try:
            session = self.property_service.get_session()
            from app.models.property import PropertyListing
            count = session.query(PropertyListing).count()
            session.close()
            print(f"✅ БД доступна, объектов в базе: {count}\n")
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}\n")
            return

        # Генерируем сценарии
        scenarios = self.generate_test_scenarios()
        print(f"📋 Создано {len(scenarios)} тестовых сценариев\n")

        # Запускаем тесты
        results = []
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'🔹'*30}")
            print(f"ТЕСТ {i}/{len(scenarios)}: {scenario['name']}")
            print(f"{'🔹'*30}")

            try:
                result = await self.test_search_with_criteria(
                    str(scenario['user_id']),
                    scenario['queries']
                )

                # Проверяем соответствие ожиданиям
                matches = self._check_expectations(
                    result['final_results'],
                    scenario.get('expected_matches', [])
                )

                result['expected_matches'] = scenario.get('expected_matches', [])
                result['actual_matches'] = matches
                result['score'] = len(matches) / len(scenario.get('expected_matches', [])) * 10 if scenario.get('expected_matches') else 0

                results.append(result)

                print(f"\n📊 Оценка: {result['score']:.1f}/10")
                print(f"   Ожидаемые совпадения: {scenario.get('expected_matches', [])}")
                print(f"   Найденные совпадения: {matches}")

            except Exception as e:
                print(f"❌ Ошибка теста: {e}")
                logger.error("test_error", error=str(e))

        # Итоговая статистика
        self._print_summary(results)
        self._save_results(results)

        return results

    def _check_expectations(self, results, expected):
        """Проверка соответствия результатов ожиданиям"""
        matches = []

        for result in results:
            result_text = f"{result.title} {result.description or ''} {result.district or ''}".lower()

            for expect in expected:
                if expect.lower() in result_text:
                    matches.append(expect)
                    break

        return list(set(matches))

    def _print_summary(self, results):
        """Вывод итоговой статистики"""

        print("\n" + "="*80)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("="*80 + "\n")

        total_tests = len(results)
        avg_score = sum(r.get('score', 0) for r in results) / total_tests if total_tests > 0 else 0

        successful = sum(1 for r in results if r.get('score', 0) >= 7.0)

        print(f"Всего тестов:        {total_tests}")
        print(f"Успешных:            {successful} ({successful/total_tests*100:.1f}%)")
        print(f"Средний балл:        {avg_score:.2f}/10")

        print("\n" + "-"*80)
        print("🏆 ЛУЧШИЕ РЕЗУЛЬТАТЫ:")
        print("-"*80 + "\n")

        sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)

        for i, res in enumerate(sorted_results[:3], 1):
            print(f"{i}. User {res['user_id']}")
            print(f"   Балл: {res.get('score', 0):.1f}/10")
            print(f"   Найдено объектов: {len(res.get('final_results', []))}")
            print()

    def _save_results(self, results):
        """Сохранение результатов"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_real_db_{timestamp}.json"
        filepath = Path(__file__).parent / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": results
            }, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n💾 Результаты сохранены: {filepath}")


async def main():
    """Главная функция"""

    tester = RealDatabaseTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
