import urllib.request

URL = "https://www.goldtraders.or.th/dailyprices"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}

request = urllib.request.Request(
    URL,
    headers=headers
)

try:
    with urllib.request.urlopen(
        request,
        timeout=15
    ) as response:

        html = response.read().decode(
            "utf-8",
            errors="ignore"
        )

        print("HTTP:", response.status)
        print("SIZE:", len(html))
        print()
        print("TITLE / GOLD KEYWORDS:")

        keywords = [
            "ทองคำแท่ง",
            "ทองรูปพรรณ",
            "รับซื้อ",
            "ขายออก",
            "เวลา",
            "ครั้งที่"
        ]

        for keyword in keywords:
            print(
                keyword,
                "=>",
                keyword in html
            )

        with open(
            "gold_page.html",
            "w",
            encoding="utf-8"
        ) as file:

            file.write(html)

        print()
        print("บันทึกหน้าเว็บไว้ที่:")
        print("gold_page.html")

except Exception as error:

    print("ERROR:", error)
