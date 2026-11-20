"""자취 냉장고 계산 로직 (화면과 분리 → 테스트하기 쉽게)

모든 날짜 계산은 today 를 인자로 받는다 (테스트에서 날짜를 고정하기 위해).
"""
import json
import uuid
from datetime import date, timedelta

LOCATIONS = ["냉장", "냉동", "실온"]
LOCATION_ICONS = {"냉장": "🧊", "냉동": "❄️", "실온": "🧺"}
CATEGORIES = {
    "채소": "🥬", "과일": "🍎", "육류": "🥩", "해산물": "🐟", "유제품": "🥛", "달걀·두부": "🥚",
    "김치·반찬": "🌶️", "냉동식품": "🥟", "가공식품": "🥫", "곡류·면": "🍚", "양념·소스": "🧂", "기타": "📦",
}
UNITS = ["개", "g", "ml", "모", "장", "캔", "봉", "팩"]
URGENT_DAYS = 3  # 오늘 ~ 3일 이내 = 임박(노랑)

# 자주 쓰는 재료: 아이콘, 카테고리, 기본 위치, 위치별 보관 일수(일반적인 참고 기준), 기본 단위, 기본 수량
_P = lambda icon, cat, loc, days, unit, qty: {"icon": icon, "category": cat, "location": loc,
                                              "days": days, "unit": unit, "qty": qty}
INGREDIENTS = {
    "계란": _P("🥚", "달걀·두부", "냉장", {"냉장": 21}, "개", 10),
    "두부": _P("🧈", "달걀·두부", "냉장", {"냉장": 5, "냉동": 30}, "모", 1),
    "우유": _P("🥛", "유제품", "냉장", {"냉장": 7}, "ml", 1000),
    "치즈": _P("🧀", "유제품", "냉장", {"냉장": 30}, "장", 10),
    "요거트": _P("🥛", "유제품", "냉장", {"냉장": 10}, "개", 4),
    "대파": _P("🌿", "채소", "냉장", {"냉장": 7, "냉동": 30}, "개", 1),
    "양파": _P("🧅", "채소", "실온", {"실온": 30, "냉장": 30}, "개", 3),
    "감자": _P("🥔", "채소", "실온", {"실온": 30}, "개", 3),
    "당근": _P("🥕", "채소", "냉장", {"냉장": 14}, "개", 1),
    "양배추": _P("🥬", "채소", "냉장", {"냉장": 14}, "개", 1),
    "애호박": _P("🥒", "채소", "냉장", {"냉장": 7}, "개", 1),
    "버섯": _P("🍄", "채소", "냉장", {"냉장": 5}, "g", 200),
    "콩나물": _P("🌱", "채소", "냉장", {"냉장": 3}, "g", 300),
    "시금치": _P("🥬", "채소", "냉장", {"냉장": 3}, "g", 200),
    "토마토": _P("🍅", "채소", "냉장", {"냉장": 7, "실온": 3}, "개", 3),
    "사과": _P("🍎", "과일", "냉장", {"냉장": 30}, "개", 4),
    "김치": _P("🌶️", "김치·반찬", "냉장", {"냉장": 60}, "g", 1000),
    "돼지고기": _P("🥩", "육류", "냉장", {"냉장": 3, "냉동": 30}, "g", 500),
    "소고기": _P("🥩", "육류", "냉장", {"냉장": 3, "냉동": 30}, "g", 300),
    "닭고기": _P("🍗", "육류", "냉장", {"냉장": 2, "냉동": 30}, "g", 500),
    "햄": _P("🥓", "가공식품", "실온", {"실온": 365, "냉장": 7}, "캔", 1),
    "소시지": _P("🌭", "가공식품", "냉장", {"냉장": 14, "냉동": 30}, "개", 6),
    "어묵": _P("🍢", "가공식품", "냉장", {"냉장": 7, "냉동": 30}, "봉", 1),
    "참치캔": _P("🐟", "가공식품", "실온", {"실온": 365}, "캔", 2),
    "만두": _P("🥟", "냉동식품", "냉동", {"냉동": 180}, "개", 20),
    "떡": _P("🍡", "곡류·면", "냉장", {"냉장": 3, "냉동": 60}, "g", 500),
    "식빵": _P("🍞", "곡류·면", "실온", {"실온": 4, "냉동": 30}, "장", 10),
    "밥": _P("🍚", "곡류·면", "실온", {"실온": 180, "냉장": 2, "냉동": 30}, "개", 3),
    "라면": _P("🍜", "곡류·면", "실온", {"실온": 150}, "개", 5),
}
QUICK_ADD = ["계란", "우유", "두부", "대파", "양파", "라면", "밥", "김치"]

# 같은 재료 다른 이름
ALIASES = {"달걀": "계란", "파": "대파", "스팸": "햄", "햇반": "밥", "즉석밥": "밥", "참치": "참치캔",
           "돼지": "돼지고기", "닭": "닭고기", "소세지": "소시지", "요구르트": "요거트", "슬라이스치즈": "치즈"}

# 자취 요리. 양은 각 재료의 기본 단위 기준. 소금·간장·고추장·된장·식용유 같은 양념은 있다고 가정
_R = lambda name, icon, minutes, need, plus: {"name": name, "icon": icon, "min": minutes, "need": need, "plus": plus}
RECIPES = [
    _R("계란볶음밥", "🍳", 10, {"밥": 1, "계란": 2}, {"대파": 0.5, "햄": 0.3, "양파": 0.5, "당근": 0.3}),
    _R("김치볶음밥", "🍛", 15, {"밥": 1, "김치": 150}, {"햄": 0.3, "계란": 1, "대파": 0.5, "치즈": 1}),
    _R("계란말이", "🥚", 10, {"계란": 3}, {"대파": 0.3, "당근": 0.2, "햄": 0.2, "치즈": 1}),
    _R("업그레이드 라면", "🍜", 5, {"라면": 1}, {"계란": 1, "대파": 0.3, "치즈": 1, "떡": 100, "만두": 4}),
    _R("김치찌개", "🍲", 25, {"김치": 200, "돼지고기": 150}, {"두부": 0.5, "대파": 0.5, "양파": 0.5}),
    _R("참치김치찌개", "🍲", 20, {"김치": 200, "참치캔": 1}, {"두부": 0.5, "대파": 0.5, "양파": 0.5}),
    _R("된장찌개", "🥘", 20, {"두부": 0.5, "애호박": 0.5}, {"양파": 0.5, "버섯": 100, "감자": 1, "대파": 0.3}),
    _R("제육볶음", "🥘", 20, {"돼지고기": 300, "양파": 1}, {"대파": 0.5, "당근": 0.3, "양배추": 0.2}),
    _R("소불고기", "🥩", 20, {"소고기": 300, "양파": 1}, {"대파": 0.5, "당근": 0.3, "버섯": 100}),
    _R("감자볶음", "🥔", 15, {"감자": 2}, {"양파": 0.5, "당근": 0.3, "햄": 0.3}),
    _R("떡볶이", "🍢", 20, {"떡": 300, "어묵": 0.5}, {"대파": 0.5, "양배추": 0.2, "계란": 2}),
    _R("에그 토스트", "🍞", 10, {"식빵": 2, "계란": 1}, {"치즈": 1, "햄": 0.2, "양배추": 0.1}),
    _R("프렌치 토스트", "🍞", 10, {"식빵": 2, "계란": 2, "우유": 100}, {}),
    _R("두부부침", "🧈", 15, {"두부": 1}, {"대파": 0.3}),
    _R("콩나물국", "🍵", 15, {"콩나물": 200}, {"대파": 0.3}),
    _R("닭볶음탕", "🍗", 40, {"닭고기": 500, "감자": 2}, {"당근": 0.5, "양파": 1, "대파": 0.5}),
    _R("소시지 야채볶음", "🌭", 15, {"소시지": 4, "양파": 0.5}, {"당근": 0.3, "버섯": 100, "양배추": 0.2}),
    _R("버섯볶음", "🍄", 10, {"버섯": 200}, {"양파": 0.5, "대파": 0.3}),
    _R("시금치나물", "🥬", 10, {"시금치": 200}, {}),
    _R("토마토 달걀볶음", "🍅", 10, {"토마토": 2, "계란": 2}, {"대파": 0.3}),
    _R("부대찌개", "🍲", 25, {"햄": 1, "김치": 150}, {"소시지": 3, "라면": 1, "두부": 0.5, "대파": 0.5, "떡": 100}),
    _R("만둣국", "🥟", 15, {"만두": 8}, {"계란": 1, "대파": 0.3, "떡": 100}),
    _R("요거트 사과볼", "🍎", 5, {"요거트": 1, "사과": 0.5}, {}),
]


# ------------------------------------------------------------------ 기본 도구
def normalize(name):
    """표기 통일: 모든 공백 제거 + 별명 → 대표 이름. 예: ' 달 걀 ' -> '계란'"""
    key = "".join(str(name).split())
    return ALIASES.get(key, key)


def josa(word, pair="은는"):
    """받침에 맞는 조사. josa("두부") -> "는", josa("계란") -> "은", josa("대파", "을를") -> "를"
    pair: "은는", "이가", "을를", "과와", "으로로" 중 하나 (받침 있을 때, 없을 때 순서)"""
    first, second = {"은는": ("은", "는"), "이가": ("이", "가"), "을를": ("을", "를"),
                     "과와": ("과", "와"), "으로로": ("으로", "로")}[pair]
    last = str(word).strip()[-1:]
    if not ("가" <= last <= "힣"):
        return f"{first}({second})"
    jong = (ord(last) - ord("가")) % 28
    if pair == "으로로" and jong == 8:  # ㄹ 받침은 '로' (예: 서울로)
        return second
    return first if jong else second


def with_josa(words, pair):
    """여러 단어를 쉼표로 잇고 마지막 단어에 맞는 조사를 붙인다."""
    text = ", ".join(words)
    return text + josa(words[-1], pair)


def preset(name):
    return INGREDIENTS.get(normalize(name))


def icon_for(name, category=None):
    p = preset(name)
    if p:
        return p["icon"]
    return CATEGORIES.get(category or "기타", "📦")


def unit_of(name):
    p = preset(name)
    return p["unit"] if p else "개"


def fmt_qty(q):
    """0.30000000000000004 -> '0.3', 2.0 -> '2', 1234.5 -> '1,234.5'"""
    q = round(float(q), 2)
    if q == int(q):
        return f"{int(q):,}"
    return f"{q:,.2f}".rstrip("0").rstrip(".")


def suggest_expiry(name, location, bought):
    """자주 쓰는 재료면 보관 위치에 맞는 유통기한 추천. 모르면 None."""
    p = preset(name)
    if not p or location not in p["days"]:
        return None
    return bought + timedelta(days=p["days"][location])


def days_left(item, today):
    return (date.fromisoformat(item["expiry"]) - today).days


def status(item, today):
    """(라벨, 등급). 등급: expired(빨강) / urgent(노랑, 오늘~3일) / ok(초록)"""
    d = days_left(item, today)
    if d < 0:
        return f"{-d}일 지남", "expired"
    if d == 0:
        return "오늘까지", "urgent"
    if d <= URGENT_DAYS:
        return f"D-{d}", "urgent"
    return f"D-{d}", "ok"


def sort_by_expiry(items):
    return sorted(items, key=lambda x: (x["expiry"], normalize(x["name"])))


# ------------------------------------------------------------------ 재료 만들기 / 수정
def make_item(name, category, qty, unit, location, bought, expiry, item_id=None):
    name = " ".join(str(name).split())
    if not name:
        raise ValueError("재료 이름을 입력해 주세요.")
    qty = round(float(qty), 2)
    if qty <= 0:
        raise ValueError("수량은 0보다 커야 해요.")
    if expiry < bought:
        raise ValueError("유통기한이 산 날짜보다 빠를 수 없어요.")
    if location not in LOCATIONS:
        raise ValueError("보관 위치가 올바르지 않아요.")
    return {"id": item_id or uuid.uuid4().hex[:8], "name": name,
            "category": category if category in CATEGORIES else "기타",
            "qty": qty, "unit": unit or "개", "location": location,
            "bought": bought.isoformat(), "expiry": expiry.isoformat()}


def update_item(items, item_id, **fields):
    """수정한 목록을 새로 돌려준다 (검사 포함)."""
    out = []
    for it in items:
        if it["id"] == item_id:
            merged = {**it, **fields}
            it = make_item(merged["name"], merged["category"], merged["qty"], merged["unit"], merged["location"],
                           _d(merged["bought"]), _d(merged["expiry"]), item_id=item_id)
        out.append(it)
    return out


def _d(x):
    return x if isinstance(x, date) else date.fromisoformat(x)


# ------------------------------------------------------------------ 재고 / 요리 추천
def stock(items, today):
    """먹을 수 있는 재고: {대표이름: [재료(유통기한 빠른 순)]}. 기한 지남, 수량 0은 제외."""
    out = {}
    for it in sort_by_expiry(items):
        if days_left(it, today) >= 0 and it["qty"] > 0:
            out.setdefault(normalize(it["name"]), []).append(it)
    return out


def _amount(lst, unit):
    return round(sum(x["qty"] for x in lst if x["unit"] == unit), 2)


def recommend(items, today, max_missing=2):
    """(바로 가능한 요리, 1~max_missing개 부족한 요리). 곧 상하는 재료를 주재료로 쓰는 요리가 먼저."""
    st = stock(items, today)
    soon = {n: days_left(lst[0], today) for n, lst in st.items()}
    ready, almost = [], []
    for r in RECIPES:
        missing = [n for n in r["need"] if n not in st]
        used = [n for n in list(r["need"]) + list(r["plus"]) if n in st]
        if not used or len(missing) > max_missing:
            continue
        shortage = []
        for n, amt in r["need"].items():
            if n in st:
                unit = unit_of(n)
                have = _amount(st[n], unit)
                if any(x["unit"] == unit for x in st[n]) and have < amt:
                    shortage.append(f"{n} {fmt_qty(amt)}{unit} 필요 ({fmt_qty(have)}{unit} 있음)")
        urgent_main = [n for n in r["need"] if n in st and soon[n] <= URGENT_DAYS]
        urgent_used = [n for n in used if soon[n] <= URGENT_DAYS]
        entry = {**r, "missing": missing, "used": used, "shortage": shortage,
                 "urgent_main": urgent_main, "urgent_used": urgent_used,
                 "urgency": sum(1 / (soon[n] + 1) for n in used)}
        (ready if not missing else almost).append(entry)
    key = lambda e: (not e["urgent_main"], len(e["missing"]), -e["urgency"], -len(e["used"]))
    ready.sort(key=key)
    almost.sort(key=key)
    return ready, almost


# ------------------------------------------------------------------ 이번 주 요약
def week_end(today):
    """이번 주 일요일 (오늘이 일요일이면 오늘)"""
    return today + timedelta(days=6 - today.weekday())


def week_summary(items, today):
    end = week_end(today)
    due = [x for x in sort_by_expiry(items) if 0 <= days_left(x, today) and _d(x["expiry"]) <= end]
    expired = [x for x in sort_by_expiry(items) if days_left(x, today) < 0]
    due_names = []
    for x in due:
        n = normalize(x["name"])
        if n not in due_names:
            due_names.append(n)
    ready, _ = recommend(items, today)
    best = None
    for r in ready:  # 이번 주 재료를 가장 많이 쓰는 요리
        hit = [n for n in r["used"] if n in due_names]
        if hit and (best is None or len(hit) > len(best[1])):
            best = (r, hit)
    lines = []
    span = "오늘" if end == today else f"이번 주 일요일({end.month}/{end.day})까지"
    if due_names:
        lines.append(f"{span} 먹어야 할 재료는 **{', '.join(due_names)}** {len(due_names)}가지예요.")
        today_names = [normalize(x["name"]) for x in due if days_left(x, today) == 0]
        if today_names:
            names = list(dict.fromkeys(today_names))
            lines.append(f"특히 **{', '.join(names)}**{josa(names[-1])} 오늘까지예요.")
        if best:
            r, hit = best
            lines.append(f"**{r['name']}**{josa(r['name'], '을를')} 만들면 {with_josa(hit, '을를')} 한 번에 쓸 수 있어요.")
    else:
        lines.append(f"{span} 급하게 먹어야 할 재료는 없어요. 여유 있어요! 😊")
    if expired:
        names = list(dict.fromkeys(normalize(x["name"]) for x in expired))
        lines.append(f"⚠️ {with_josa(names, '은는')} 유통기한이 지났어요. 상태를 확인하고 정리해 주세요.")
    return {"due": due, "due_names": due_names, "expired": expired, "best": best, "lines": lines, "end": end}


# ------------------------------------------------------------------ 요리 후 수량 차감
def plan_usage(items, recipe, today):
    """'만들었어요'를 눌렀을 때 보여 줄 기본 사용량. 단위가 다르면 자동으로 정하지 않음(0)."""
    st = stock(items, today)
    plan = []
    for n, amt in list(recipe["need"].items()) + list(recipe["plus"].items()):
        if n not in st:
            continue
        unit = st[n][0]["unit"]
        have = _amount(st[n], unit)
        same = unit == unit_of(n)
        plan.append({"name": n, "unit": unit, "have": have, "mismatch": not same,
                     "use": min(amt, have) if same else 0.0, "recipe_amt": amt, "recipe_unit": unit_of(n)})
    return plan


def apply_usage(items, uses, today):
    """uses = {재료이름: 사용량(그 재료 단위)}. 유통기한 빠른 것부터 차감.
    돌려주는 값: (새 목록, 다 쓴 재료 이름 목록)"""
    items = [dict(x) for x in items]
    st = stock(items, today)
    by_id = {x["id"]: x for x in items}
    used_up = []
    for name, amount in uses.items():
        n = normalize(name)
        amount = round(float(amount), 2)
        if amount <= 0 or n not in st:
            continue
        unit = st[n][0]["unit"]
        for it in st[n]:
            if it["unit"] != unit or amount <= 0:
                continue
            take = min(it["qty"], amount)
            by_id[it["id"]]["qty"] = round(it["qty"] - take, 2)
            amount = round(amount - take, 2)
        if all(by_id[it["id"]]["qty"] <= 0 for it in st[n] if it["unit"] == unit):
            used_up.append(n)
    left = [x for x in items if x["qty"] > 0]
    return left, used_up


# ------------------------------------------------------------------ 장보기
def add_shopping(shopping, name, reason=""):
    """장보기 목록에 추가. 이미 있으면(표기 차이 포함) 추가하지 않고 False."""
    name = " ".join(str(name).split())
    if not name:
        return False
    n = normalize(name)
    if any(normalize(s["name"]) == n and not s.get("done") for s in shopping):
        return False
    shopping.append({"id": uuid.uuid4().hex[:8], "name": n if preset(n) else name, "reason": reason, "done": False})
    return True


# ------------------------------------------------------------------ 저장 / 예시
def empty_fridge():
    return {"version": 3, "items": [], "shopping": []}


def to_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def from_json(text):
    """저장 파일 읽기 + 검사. v2 파일(카테고리, 단위 없음)도 기본값을 채워서 읽는다."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("JSON 파일이 아니에요.")
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("냉장고 저장 파일 형식이 아니에요.")
    items = []
    for i, it in enumerate(data["items"], 1):
        try:
            p = preset(it["name"]) or {}
            items.append(make_item(
                it["name"], it.get("category") or p.get("category", "기타"), it.get("qty", 1),
                it.get("unit") or p.get("unit", "개"),
                it["location"] if it.get("location") in LOCATIONS else "냉장",
                date.fromisoformat(it["bought"]), date.fromisoformat(it["expiry"])))
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ValueError(f"{i}번째 재료의 형식이 올바르지 않아요.")
    shopping = []
    raw = data.get("shopping") if isinstance(data.get("shopping"), list) else []
    for s in raw:
        if not (isinstance(s, dict) and str(s.get("name", "")).strip()):
            continue
        if s.get("done"):  # 산 항목은 중복 검사 없이 그대로 보관
            shopping.append({"id": uuid.uuid4().hex[:8], "name": str(s["name"]).strip(),
                             "reason": str(s.get("reason", "")), "done": True})
        else:
            add_shopping(shopping, s["name"], str(s.get("reason", "")))
    return {"version": 3, "items": items, "shopping": shopping}


def sample_data(today):
    """체험용 예시 냉장고: (이름, 수량, 위치, 며칠 전에 샀는지, 유통기한까지 남은 날)"""
    ex = [("계란", 6, "냉장", 9, 12), ("두부", 1, "냉장", 4, 1), ("대파", 1, "냉장", 4, 3),
          ("김치", 800, "냉장", 20, 40), ("우유", 500, "냉장", 8, -1), ("밥", 3, "실온", 30, 150),
          ("라면", 4, "실온", 10, 140), ("양파", 2, "실온", 10, 20), ("돼지고기", 400, "냉동", 5, 25),
          ("콩나물", 300, "냉장", 3, 0), ("햄", 1, "실온", 30, 200), ("애호박", 1, "냉장", 2, 5)]
    items = []
    for n, q, loc, b, d in ex:
        p = INGREDIENTS[n]
        items.append(make_item(n, p["category"], q, p["unit"], loc, today - timedelta(days=b), today + timedelta(days=d)))
    shopping = []
    add_shopping(shopping, "우유", "유통기한 지남")
    return {"version": 3, "items": items, "shopping": shopping}
