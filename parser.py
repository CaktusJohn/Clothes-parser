import hashlib
import json
import requests
from openpyxl import Workbook
from datetime import datetime





seen_uids = {}

#преобразует один товар (словарь item) в унифицированный JSON-словарь, берёт нужные поля, делает uid и проверяет дубликаты
def map_tsum_product_to_json(item: dict) -> dict:
    # Извлекаем данные
    brand = item.get("brand_name") or ""
    name = item.get("title") or ""
    color = item.get("colorConcrete", {}).get("title", "") or ""

    # уникальность товара определяется комбинацией бренд+название+цвет, затем берётся MD5 хеш этой строки
    base_uid = f"{brand.lower()}_{name.lower()}_{color.lower()}"
    uid = hashlib.md5(base_uid.encode()).hexdigest()

    if uid in seen_uids:
        print("\n⚠️  Найден дубликат UID:", uid)
        print("   Уже был:", seen_uids[uid])
        print("   Новый  :", {"brand": brand, "name": name, "color": color})
    else:
        seen_uids[uid] = {"brand": brand, "name": name, "color": color}

    # Фото (если меньше 2 фото — заполняем None)
    photos = item.get("photos", [])
    photo1 = photos[0]["middle"] if len(photos) > 0 else None
    photo2 = photos[1]["middle"] if len(photos) > 1 else None

    # Цена — берем скидочную, если есть
    sku_list = item.get("skuList", [])
    if sku_list:
        price = sku_list[0].get("price_original")
        price = str(price) if price else None
    else:
        price = None

    # Ссылка на товар
    slug = item.get("slug")
    link = f"https://www.tsum.ru/product/{slug}" if slug else None

    # Детали — краткое описание, если нет — SEO
    details = item.get("description_lit") or item.get("description_seo") or None

    # Пол
    gender = item.get("gender") or None

    # Пока тип не определяем
    typ = None

    return {
        "id": item.get("id"),
        "uid": uid,
        "photo1": photo1,
        "photo2": photo2,
        "link": link,
        "brand": brand or None,
        "name": name or None,
        "price": price,
        "details": details,
        "gender": gender,
        "typ": typ
    }

# with open("/Users/timowey/Desktop/raw.json", "r", encoding="utf-8") as f:
#     data = json.load(f)  # data = список товаров
#
# mapped_products = [map_tsum_product_to_json(item) for item in data]

# вывод (например, первые 2)
# print(json.dumps(mapped_products[:10], indent=2, ensure_ascii=False))

import requests

url = "https://api.tsum.ru/v3/catalog/search"

# headers = {
#     "Accept": "application/json",
#     "Accept-Language": "ru,en;q=0.9",
#     "Connection": "keep-alive",
#     "Content-Type": "application/json",
#     "Origin": "https://www.tsum.ru",
#     "Referer": "https://www.tsum.ru/",
#     "Sec-Fetch-Dest": "empty",
#     "Sec-Fetch-Mode": "cors",
#     "Sec-Fetch-Site": "same-site",
#     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 YaBrowser/25.8.0.0 Safari/537.36",
#     "X-App-Platform": "web",
#     "X-Client-City": "%7B%22fiasId%22%3A%220c5b2444-70a0-4932-980c-b4dc0d3f02b5%22%2C%22fulltitle%22%3A%22%D0%B3%20%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%22%2C%22country%22%3A%22%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%22%2C%22region%22%3A%22%D0%B3%20%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%22%2C%22city%22%3A%22%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%22%7D",
#     "X-Request-Id": "e17a7382-cd07-4164-9a9f-f8ea16eb5802",
#     "X-Segment": '{"AutomerchML":"0"}',
#     "X-Site-Region": "RU",
#     "X-Store": "tsum",
#     "X-Uid": "89393121-2a52-4f85-a738-1b9cfa53fdf8",
#     "X-XID": "7ea725b0-64ff-4e8d-82c0-c4a904481ab4",
#     "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "YaBrowser";v="25.8", "Yowser";v="2.5"',
#     "sec-ch-ua-mobile": "?0",
#     "sec-ch-ua-platform": '"macOS"'
# }

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

payload = {
    "section": "19387,19974",
    "sort": "date",
    "page": "4"
}

# Создаем Workbook
wb = Workbook()
ws = wb.active
ws.title = "Товары"

# Заголовки
headers_row = ["ID", "UID", "Бренд", "Название", "Цвет", "Цена", "Фото 1", "Фото 2", "Ссылка", "Описание", "Пол", "Дата парсинга"]
ws.append(headers_row)

# Парсим все страницы
section = "19387,19974"
all_products = []

for page in range(1, 100):
    payload = {
        "section": section,
        "sort": "date",
        "page": str(page)
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"Страница {page}: {response.status_code}")
    
    if response.status_code != 200:
        break
    
    try:
        data = response.json()
        
        # Если это список товаров, используем напрямую; если словарь, берём items
        if isinstance(data, list):
            items = data
        else:
            items = data.get('items', [])
        
        if not items:
            print(f"Конец категории на странице {page}")
            break
        
        for item in items:
            product = map_tsum_product_to_json(item)
            all_products.append(product)
            
            # Добавляем строку в Excel
            ws.append([
                product['id'],
                product['uid'],
                product['brand'],
                product['name'],
                item.get("colorConcrete", {}).get("title", ""),
                product['price'],
                product['photo1'],
                product['photo2'],
                product['link'],
                product['details'],
                product['gender'],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
                
    except json.JSONDecodeError:
        print(f"Ошибка парсинга JSON на странице {page}")
        break

# Сохраняем в Excel
filename = f"tsum_products_{section.replace(',', '_')}.xlsx"
wb.save(filename)
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