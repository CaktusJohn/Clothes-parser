import hashlib
import json
from openpyxl import Workbook
from datetime import datetime
import pandas as pd


seen_uids = {}
SUBCATEGORY_ID_MAP = {
    # Одежда
    "19387": "Пальто",
    "21338": "Куртка",
    "19967": "Шуба",
    "19402": "Жилет",
    # Обувь
    "19401": "Ботинки",
    "19740": "Кроссовки",
    "19741": "Кеды",
    "20063": "Сапоги",
    "19759": "Тапки",
    # Аксессуары
    "19790": "Сумка",
    "19537": "Ремни",
    "20874": "Очки",
    "19816": "Брелки",
    "19060": "Перчатки",
    "18843": "Шапки",
    "19417": "Шляпы",
    "18609": "Кепки",
    "18377": "Украшения",
    
}
'''
SUBCATEGORY_ID_MAP = {
    # Одежда
    "19387": "Пальто",
    "18777": "Пальто",
    "18726": "Пальто",
    "19068": "Куртка",
    "18910": "Куртка",
    "13771245": "Куртка",
    "19967": "Шуба",
    "18631": "Шуба",
    "19402": "Жилет",
    "18432": "Жилет",
    # Обувь
    "19401": "Ботинки",
    "19740": "Кроссовки",
    "19014": "Кроссовки",

    "20063": "Сапоги",
    "18441": "Сапоги",
    "21385": "Сапоги",
    "19759": "Тапки",
    "18961": "Тапки",
    # Аксессуары
    "19790": "Сумка",
    "18561": "Сумка",
    "18754": "Сумка",
    "20588": "Сумка",
    "19537": "Ремни",
    "18808": "Ремни",
    "20874": "Очки",
    "18959": "Очки",
    "18457": "Очки",
    "21379": "Очки",
    "19816": "Брелки",
    "18716": "Брелки",
    "19060": "Перчатки",
    "21358": "Перчатки",
    "18843": "Шапки",
    "19417": "Шляпы",
    "18609": "Кепки",
    "18377": "Украшения",
    "18378": "Украшения",
    "18629": "Украшения",
}
'''
#преобразует один товар (словарь item) в унифицированный JSON-словарь, берёт нужные поля, делает uid и проверяет дубликаты
def map_tsum_product_to_json(item: dict, category_name: str) -> dict:
    # Извлекаем данные
    brand = item.get("brand_name") or ""
    name = item.get("title") or ""
    color = item.get("colorConcrete", {}).get("title", "") or ""

    # уникальность товара определяется комбинацией бренд+название+цвет, затем берётся MD5 хеш этой строки
    base_uid = f"{brand.lower()}_{name.lower()}_{color.lower()}"
    uid = hashlib.md5(base_uid.encode()).hexdigest()

    if uid in seen_uids:
        print(f"⚠️  Найден дубликат UID: {uid}, товар '{(seen_uids[uid]['brand'] or '')} {(seen_uids[uid]['name'] or '')}' пропускается.")
        return None # <--- Пропускаем дубликат
    else:
        seen_uids[uid] = {"brand": brand, "name": name, "color": color}


    # Фото (если меньше 2 фото — заполняем None)
    photos = item.get("photos", [])
    photo1 = photos[0]["middle"] if len(photos) > 0 else None
    photo2 = photos[1]["middle"] if len(photos) > 1 else None

    # Цена — берем первую SKU и стараемся извлечь значение и валюту
    sku_list = item.get("skuList", [])
    price = None
    if sku_list:
        sku = sku_list[0]
        price_value = sku.get("price") or sku.get("price_original") or sku.get("priceNumeric") or sku.get("price_value")
        currency = sku.get("currency") or sku.get("price_currency") or sku.get("currency_code") or item.get("currency")
        if price_value is not None:
            price = f"{price_value} {currency}" if currency else str(price_value)

    # Ссылка на товар
    slug = item.get("slug")
    link = f"https://www.tsum.ru/product/{slug}" if slug else None

    # Детали — краткое описание, если нет — SEO
    details = item.get("description_lit") or item.get("description_seo") or None


    # Пол — нормализуем к 'm' / 'w'
    raw_gender = item.get("gender") or ""
    gender = None
    if raw_gender:
        g = str(raw_gender).lower()
        if g == "male":
            gender = "m"
        elif g == "female":
            gender = "w"
        elif g == "unisex":
            gender = "m"
    
    # Категория теперь передается напрямую
    detected_subcat = category_name

    # Источник
    source = "цум"

    return {
        "id": item.get("id"),
        "uid": uid,
        "photo1": photo1,
        "photo2": photo2,
        "link": link,
        "brand": brand or None,
        "name": name or None,
        "subcategory": detected_subcat,
        "color": color,  # Добавляем цвет в выходной словарь
        "price": price,
        "details": details,
        "gender": gender,
        "source": source,
        "typ": None,
        "parsing_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Добавляем дату парсинга
    }


import requests

url = "https://api.tsum.ru/v3/catalog/search"

headers = {
  "User-Agent": "...Chrome...",
  "Accept": "application/json",
  "Content-Type": "application/json",
  "Origin": "https://www.tsum.ru",
  "Referer": "https://www.tsum.ru/",
  "X-Store": "tsum",
}

cookies = {
    "xid": "7ea725b0-64ff-4e8d-82c0-c4a904481ab4",
    # ... остальные cookies можно добавить, но часто НЕ нужны
}



# Парсим все страницы
all_products = []

for category_id, category_name in SUBCATEGORY_ID_MAP.items():
    print(f"\n--- Парсинг категории: {category_name} (ID: {category_id}) ---")
    for page in range(1, 200):
        payload = {
            "section": category_id,
            "sort": "date",
            "page": str(page)
        }
        
        response = requests.post(url, headers=headers, json=payload)
        print(f"Страница {page}: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Ошибка запроса на странице {page}, код: {response.status_code}. Переход к следующей категории.")
            break
        
        try:
            data = response.json()
            
            # Если это список товаров, используем напрямую; если словарь, берём items
            if isinstance(data, list):
                items = data
            else:
                items = data.get('items', [])
            
            if not items:
                print(f"Категория '{category_name}' закончилась на странице {page}.")
                break
            
            for item in items:
                product = map_tsum_product_to_json(item, category_name)
                if product: # <--- Добавляем проверку на None
                    all_products.append(product)
                    
        except json.JSONDecodeError:
            print(f"Ошибка парсинга JSON на странице {page}. Переход к следующей категории.")
            break

# Создаем DataFrame из всех продуктов
df = pd.DataFrame(all_products)

# Определяем порядок столбцов и переименовываем их для удобства
df = df[["id", "uid", "brand", "name", "subcategory", "color", "price", "photo1", "photo2", "link", "details", "gender", "source", "parsing_date"]]
df.columns = ["ID", "UID", "Бренд", "Название", "Подкатегория", "Цвет", "Цена", "Фото 1", "Фото 2", "Ссылка", "Описание", "Пол", "Источник", "Дата парсинга"]

# Сохраняем в Excel
filename = "parsing v2.xlsx"
df.to_excel(filename, index=False)
print(f"\nВсего спарсено: {len(all_products)} товаров")
print(f"Сохранено в: {filename}")

'''     скопировал search запро as sutl
curl ^"https://api.tsum.ru/v3/catalog/search^" ^
  -H ^"Accept: application/json^" ^
  -H ^"Accept-Language: ru,en;q=0.9^" ^
  -H ^"Connection: keep-alive^" ^
  -H ^"Content-Type: application/json^" ^
  -b ^"selectedGender=women; xid=f65ce594-b955-4e66-a35b-de4716997ef7; gtmc_yclid=15751640301847445503; mindboxDeviceUUID=620abcee-88c8-4633-a3b0-7d59307051cf; directCrm-session=^%^7B^%^22deviceGuid^%^22^%^3A^%^22620abcee-88c8-4633-a3b0-7d59307051cf^%^22^%^7D; popmechanic_sbjs_migrations=popmechanic_1418474375998^%^3D1^%^7C^%^7C^%^7C1471519752600^%^3D1^%^7C^%^7C^%^7C1471519752605^%^3D1; wishlist_sid=Qh8R4WuHsMy6t2_Thz3ijMjyh1h1u3Qj; _ym_uid=1762817491635545640; _ym_d=1762817491; _userGUID=0:mhts0pfh:U52kOGYRa5jPZxQlEgEGfrXc_6uQTg6v; tmr_lvid=208457c0b45f4b86bad0177065a922b3; tmr_lvidTS=1762817491548; tt_deduplication_cookie=yandex; utmctr=ph:55932739457; _utm_term=ph:55932739457; x-segment=eyJBdXRvbWVyY2hNTCI6IjAifQ==; __utmzzses=1; _ym_isad=1; uuid=0b47689d-d975-40d1-b872-3916d2b8618b; CITY_Z=^%^7B^%^22fiasId^%^22^%^3A^%^220c5b2444-70a0-4932-980c-b4dc0d3f02b5^%^22^%^2C^%^22fulltitle^%^22^%^3A^%^22^%^D0^%^A0^%^D0^%^BE^%^D1^%^81^%^D1^%^81^%^D0^%^B8^%^D1^%^8F^%^2C^%^20^%^D0^%^B3^%^20^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^2C^%^22country^%^22^%^3A^%^22^%^D0^%^A0^%^D0^%^BE^%^D1^%^81^%^D1^%^81^%^D0^%^B8^%^D1^%^8F^%^22^%^2C^%^22region^%^22^%^3A^%^22^%^D0^%^B3^%^20^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^2C^%^22city^%^22^%^3A^%^22^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^2C^%^22mainTitle^%^22^%^3A^%^22^%^D0^%^B3^%^20^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^2C^%^22subTitle^%^22^%^3A^%^22^%^22^%^2C^%^22name^%^22^%^3A^%^22^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^7D; _gid=GA1.2.1465798913.1763081636; __utma=75424919.1852321538.1762817489.1762817491.1763081636.2; __utmc=75424919; __utmz=75424919.1763081636.2.2.utmcsr=r.tsum.ru^|utmccn=(referral)^|utmcmd=referral^|utmcct=/; digsearch=1; dSesn=18d2edc3-410a-3d6d-d17b-807523b9884d; _ym_visorc=w; utmcsr=r.tsum.ru; utmccn=(referral); utmcmd=referral; utmcct=/; __utmzz=utmcsr=r.tsum.ru^|utmccn=(referral)^|utmcmd=referral^|utmcct=/; _calltracking=+7 800 500 73 03,+7 495 933 73 03; _utm_source=r.tsum.ru; _utm_medium=referral; _utm_campaign=(referral); _utm_content=/; _channelGrouping=Referral; _ga=GA1.2.1852321538.1762817489; __utmb=75424919.2.10.1763081636; _vbmd=0JN1CzNorBJw2YTprmDp-serZhRUBDyi; digi_uc=^|c:176308:13750663:13764425; gtmc_userAuth=0; gtmc_ppview30day=1; p_count=4; hits_count=9; _ga_GRGD1C90XP=GS2.1.s1763081635^$o2^$g1^$t1763082804^$j60^$l0^$h0^" ^
  -H ^"Origin: https://www.tsum.ru^" ^
  -H ^"Referer: https://www.tsum.ru/^" ^
  -H ^"Sec-Fetch-Dest: empty^" ^
  -H ^"Sec-Fetch-Mode: cors^" ^
  -H ^"Sec-Fetch-Site: same-site^" ^
  -H ^"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 YaBrowser/25.8.0.0 Safari/537.36^" ^
  -H ^"X-App-Platform: web^" ^
  -H ^"X-Client-City: ^%^7B^%^22fiasId^%^22^%^3A^%^220c5b2444-70a0-4932-980c-b4dc0d3f02b5^%^22^%^2C^%^22fulltitle^%^22^%^3A^%^22^%^D0^%^A0^%^D0^%^BE^%^D1^%^81^%^D1^%^81^%^D0^%^B8^%^D1^%^8F^%^2C^%^20^%^D0^%^B3^%^20^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^2C^%^22country^%^22^%^3A^%^22^%^D0^%^A0^%^D0^%^BE^%^D1^%^81^%^D1^%^81^%^D0^%^B8^%^D1^%^8F^%^22^%^2C^%^22region^%^22^%^3A^%^22^%^D0^%^B3^%^20^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^2C^%^22city^%^22^%^3A^%^22^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^2C^%^22mainTitle^%^22^%^3A^%^22^%^D0^%^B3^%^20^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^2C^%^22subTitle^%^22^%^3A^%^22^%^22^%^2C^%^22name^%^22^%^3A^%^22^%^D0^%^9C^%^D0^%^BE^%^D1^%^81^%^D0^%^BA^%^D0^%^B2^%^D0^%^B0^%^22^%^7D^" ^
  -H ^"X-Request-Id: 97660b61-25b1-4e54-bb03-809567832a2d^" ^
  -H ^"X-Segment: ^{^\^"AutomerchML^\^":^\^"0^\^"^}^" ^
  -H ^"X-Site-Region: RU^" ^
  -H ^"X-Store: tsum^" ^
  -H ^"X-Uid: 0b47689d-d975-40d1-b872-3916d2b8618b^" ^
  -H ^"X-XID: f65ce594-b955-4e66-a35b-de4716997ef7^" ^
  -H ^"sec-ch-ua: ^\^"Not)A;Brand^\^";v=^\^"8^\^", ^\^"Chromium^\^";v=^\^"138^\^", ^\^"YaBrowser^\^";v=^\^"25.8^\^", ^\^"Yowser^\^";v=^\^"2.5^\^"^" ^
  -H ^"sec-ch-ua-mobile: ?0^" ^
  -H ^"sec-ch-ua-platform: ^\^"Windows^\^"^" ^
  --data-raw ^"^{^\^"section^\^":^\^"19822^\^",^\^"page^\^":^\^"3^\^"^}^"
'''


'''
{id: 13756765, modelId: 13835462, modelExtId: "7073859", codeVnd: "G052KT/FM2G4",…}



additional
: 
{sizing: "", isClickAndCollectEnabled: false, hasAlternatives: true, isFitting: false, fittingType: "",…}
brand
: 
{id: 165399, title: "Dolce & Gabbana", slug: "dolce_gabbana",…}
category
: 
{id: 19387, title: "Пальто", titleLink: "Пальто", slug: "men-palto-19387"}
codeVnd
: 
"G052KT/FM2G4"
color
: 
{id: 661006, title: "Темно-серый", imageUrl: ""}
id
: 
13756765
images
: 
[{,…}, {,…}, {,…}, {,…}, {,…}]
information
: 
[{id: "product", title: "О товаре",…}, {id: "sizes", title: "Размеры и посадка", description: "",…},…]
isBuyable
: 
true
modelExtId
: 
"7073859"
modelId
: 
13835462
offers
: 
[{id: 14675174, extId: "56246025",…}, {id: 14675010, extId: "56246026",…},…]
productLine
: 
[]
products
: 
[{id: 13756765, slug: "7073859-sherstyanoe-palto-dolce-gabbana-temno-seryi",…}]
sizeTable
: 
{title: "Размеры мужской одежды", description: {title: "Российский размер", code: "RU"},…}
slug
: 
"7073859-sherstyanoe-palto-dolce-gabbana-temno-seryi"
tags
: 
[{id: 13052547, title: "TSUM COLLECT", slug: "tsum-collect"}]
title
: 
"Шерстяное пальто"
type
: 
"regular"
video
: 
""
view
: 
"noGroup"
'''