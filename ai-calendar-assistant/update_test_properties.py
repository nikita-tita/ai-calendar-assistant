#!/usr/bin/env python3
"""Update test properties with full data."""

import os
import psycopg2

# Database connection
conn = psycopg2.connect(
    dbname="property_bot",
    user="property_user",
    password=os.getenv("DB_PASSWORD", ""),
    host="91.229.8.221",
    port=5432
)

cur = conn.cursor()

# Update 2-room apartments
updates = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "building_name": "ЖК Северная Столица",
        "address_raw": "пр. Просвещения, 85к1",
        "ready_quarter": 2,
        "building_year": 2025,
        "developer_name": "ЛСР. Недвижимость-Северо-Запад"
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "building_name": "ЖК Светлый мир",
        "address_raw": "ул. Руставели, 12",
        "ready_quarter": 4,
        "building_year": 2025,
        "developer_name": "ЛСР. Недвижимость-Северо-Запад"
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "building_name": "ЖК Шуваловский",
        "address_raw": "пр. Испытателей, 25",
        "ready_quarter": 1,
        "building_year": 2025,
        "developer_name": "Setl Group"
    },
    {
        "id": "44444444-4444-4444-4444-444444444444",
        "building_name": "ЖК Цветной город",
        "address_raw": "ул. Руднева, 22к1",
        "ready_quarter": 3,
        "building_year": 2025,
        "developer_name": "Группа ЦДС"
    },
    {
        "id": "55555555-5555-5555-5555-555555555555",
        "building_name": "ЖК Лахта Парк",
        "address_raw": "Береговая ул., 25",
        "ready_quarter": 1,
        "building_year": 2026,
        "developer_name": "Газпром"
    },
    {
        "id": "1room-vasilievsky-1",
        "building_name": "ЖК Морская симфония",
        "address_raw": "Наличная ул., 40",
        "ready_quarter": 2,
        "building_year": 2025,
        "developer_name": "ЛСР. Недвижимость-Северо-Запад"
    },
    {
        "id": "1room-vasilievsky-2",
        "building_name": "ЖК Остров",
        "address_raw": "Кораблестроителей ул., 32",
        "ready_quarter": 4,
        "building_year": 2025,
        "developer_name": "Setl City"
    },
    {
        "id": "1room-vasilievsky-3",
        "building_name": "ЖК Riverside",
        "address_raw": "Уральская ул., 17",
        "ready_quarter": 1,
        "building_year": 2026,
        "developer_name": "Setl City"
    }
]

for update in updates:
    cur.execute("""
        UPDATE property_listings
        SET building_name = %s,
            address_raw = %s,
            ready_quarter = %s,
            building_year = %s,
            developer_name = %s
        WHERE id = %s
    """, (
        update["building_name"],
        update["address_raw"],
        update["ready_quarter"],
        update["building_year"],
        update["developer_name"],
        update["id"]
    ))
    print(f"Updated {update['id']}: {update['building_name']}")

conn.commit()

# Verify
cur.execute("""
    SELECT id, title, building_name, address_raw, ready_quarter, developer_name
    FROM property_listings
    WHERE is_active = true
    ORDER BY rooms, price
""")

print("\n✅ Updated properties:")
for row in cur.fetchall():
    print(f"  {row[1][:30]:30} | {row[2][:25]:25} | Q{row[4] or '?'}/{row[5] or 'No dev'}")

cur.close()
conn.close()
print("\n✅ Done!")
