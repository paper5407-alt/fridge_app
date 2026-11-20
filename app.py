"""자취 냉장고 - 유통기한 관리 · 이번 주 브리핑 · 요리 추천 · 수량 차감 · 장보기 (Streamlit)

실행:  streamlit run app.py
"""
import html
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from logic import (
    CATEGORIES, INGREDIENTS, LOCATION_ICONS, LOCATIONS, QUICK_ADD, UNITS, URGENT_DAYS, add_shopping, apply_usage,
    empty_fridge, fmt_qty, from_json, icon_for, josa, make_item, plan_usage, preset, recommend,
    sample_data, sort_by_expiry, status, suggest_expiry, to_json, update_item, week_summary,
)

st.set_page_config(page_title="자취 냉장고", page_icon="🧊", layout="centered")
WEEKDAYS = "월화수목금토일"
# 배포 서버는 UTC라서 한국 날짜와 하루 어긋날 수 있음 → 한국 시간 기준
today = datetime.now(ZoneInfo("Asia/Seoul")).date()

# ================================================================ 스타일
st.markdown("""
<style>
[data-testid="stToolbar"], [data-testid="stDecoration"] {display:none;}
.block-container {padding-top: 1.6rem; padding-bottom: 4rem; max-width: 640px;}
h3 {margin-bottom: .2rem !important;}
.hero {background: linear-gradient(135deg,#0ea5a4 0%,#2563eb 100%); color:#fff; border-radius:20px;
       padding:18px 22px; margin:6px 0 12px 0; box-shadow:0 8px 24px rgba(14,165,164,.22);}
.hero .label {font-size:.88rem; opacity:.9;}
.hero .amount {font-size:2.1rem; font-weight:800; letter-spacing:-1px; margin:0 0 8px 0;}
.hero .sub {display:flex; gap:8px; font-size:.84rem; flex-wrap:wrap;}
.hero .pill {background:rgba(255,255,255,.18); border-radius:999px; padding:3px 10px;}
.brief {background:#fff; border:1px solid #d7ecec; border-radius:16px; padding:12px 16px; margin-bottom:14px;}
.brief .t {font-weight:800; font-size:.95rem; margin-bottom:4px; color:#0b7f7e;}
.brief p {margin:3px 0; font-size:.92rem; line-height:1.55;}
.group {font-weight:800; font-size:.98rem; margin:14px 0 6px 0; display:flex; align-items:center; gap:6px;}
.group .n {color:#7b8494; font-weight:600; font-size:.85rem;}
.info {display:flex; align-items:center; gap:12px; min-width:0; padding:2px 0;}
.icon {width:42px; height:42px; border-radius:12px; background:#eef6f6; display:flex; align-items:center;
       justify-content:center; font-size:1.3rem; flex-shrink:0;}
.txt {min-width:0;}
.name {font-weight:700; font-size:.98rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.qty {color:#475569; font-weight:600; font-size:.85rem;}
.meta {color:#7b8494; font-size:.78rem; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.badge {display:inline-block; border-radius:999px; padding:1px 8px; font-size:.72rem; font-weight:800; margin-left:2px;}
.b-expired {background:#fee2e2; color:#dc2626;}
.b-urgent {background:#fef3c7; color:#b45309;}
.b-ok {background:#dcfce7; color:#15803d;}
.section {font-weight:800; font-size:1.02rem; margin:14px 0 8px 0;}
.rtitle {font-weight:800; font-size:1.02rem;}
.chip {display:inline-block; background:#eef2f7; border-radius:999px; padding:1px 9px; font-size:.78rem; margin:5px 4px 0 0;}
.chip.hot {background:#fef3c7; color:#b45309; font-weight:700;}
.chip.miss {background:#fff; border:1px dashed #9aa3b2; color:#6b7280;}
.warn {color:#b45309; font-size:.8rem; margin-top:4px;}
.empty {text-align:center; color:#7b8494; padding:22px 0 8px 0;}
.empty .big {font-size:2.5rem;}
.shopdone {color:#9aa3b2; text-decoration:line-through;}
/* 폰에서도 [정보 | 버튼]이 한 줄에 오도록 (Streamlit 기본은 좁은 화면에서 세로로 쌓음) */
[class*="st-key-row_"] [data-testid="stHorizontalBlock"] {flex-wrap:nowrap; gap:.35rem; align-items:center;}
[class*="st-key-row_"] [data-testid="stColumn"] {min-width:0 !important; width:auto !important;}
[class*="st-key-row_"] [data-testid="stColumn"]:not(:first-child) {flex:0 0 auto !important;}
[class*="st-key-row_"] {background:#fff; border:1px solid #e6e9ef; border-radius:16px; padding:8px 10px;}
[class*="st-key-row_"] button {padding:4px 9px; min-height:0;}
[class*="st-key-row_"] [data-testid="stMarkdownContainer"], [class*="st-key-row_"] [data-testid="stMarkdown"] {margin-bottom:0 !important;}
.st-key-quick [data-testid="stHorizontalBlock"], .st-key-qtyrow [data-testid="stHorizontalBlock"]
  {flex-wrap:nowrap; gap:.4rem;}
.st-key-quick [data-testid="stColumn"], .st-key-qtyrow [data-testid="stColumn"] {min-width:0 !important;}
.st-key-quick button {padding:6px 2px; font-size:.85rem;}
[class*="st-key-recipe_"] {background:#fff;}
[data-testid="stDialog"] [data-testid="stHorizontalBlock"], [data-testid="stForm"] [data-testid="stHorizontalBlock"]
  {flex-wrap:nowrap; gap:.5rem;}
[data-testid="stDialog"] [data-testid="stColumn"], [data-testid="stForm"] [data-testid="stColumn"] {min-width:0 !important;}
</style>
""", unsafe_allow_html=True)

# ================================================================ 상태 (사람마다 따로)
if "fridge" not in st.session_state:
    st.session_state.fridge = empty_fridge()
if "form_id" not in st.session_state:
    st.session_state.form_id = 0
fridge = st.session_state.fridge


def fmt_date(d):
    d = d if isinstance(d, date) else date.fromisoformat(d)
    return f"{d.month}월 {d.day}일({WEEKDAYS[d.weekday()]})"


def md_bold(text):
    """**굵게** → <b>굵게</b> (나머지는 HTML 이스케이프)"""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(text))


def set_items(items):
    st.session_state.fridge["items"] = items


def add_to_shop(name, reason):
    return add_shopping(st.session_state.fridge["shopping"], name, reason)


def quick_add(name):
    p = INGREDIENTS[name]
    exp = suggest_expiry(name, p["location"], today)
    st.session_state.fridge["items"].append(
        make_item(name, p["category"], p["qty"], p["unit"], p["location"], today, exp))
    st.toast(f"✅ {name} {fmt_qty(p['qty'])}{p['unit']} 넣었어요 · {fmt_date(exp)}까지 (✏️로 수정 가능)")


def load_sample():
    st.session_state.fridge = sample_data(today)


# ================================================================ 대화 상자
@st.dialog("✏️ 재료 수정")
def edit_dialog(item_id):
    it = next((x for x in st.session_state.fridge["items"] if x["id"] == item_id), None)
    if it is None:
        st.info("이미 삭제된 재료예요.")
        return
    name = st.text_input("이름", it["name"])
    c1, c2 = st.columns(2)
    cat = c1.selectbox("카테고리", list(CATEGORIES), index=list(CATEGORIES).index(it["category"]))
    loc = c2.selectbox("보관 위치", LOCATIONS, index=LOCATIONS.index(it["location"]))
    c1, c2 = st.columns([3, 2])
    qty = c1.number_input("수량", min_value=0.0, value=float(it["qty"]), step=1.0 if it["unit"] not in ("g", "ml") else 50.0,
                          format="%g")
    units = UNITS if it["unit"] in UNITS else UNITS + [it["unit"]]
    unit = c2.selectbox("단위", units, index=units.index(it["unit"]))
    c1, c2 = st.columns(2)
    bought = c1.date_input("산 날짜", date.fromisoformat(it["bought"]), format="YYYY.MM.DD")
    expiry = c2.date_input("유통기한", date.fromisoformat(it["expiry"]), format="YYYY.MM.DD")
    if st.button("저장", type="primary", use_container_width=True):
        if qty == 0:
            st.error("수량이 0이면 아래 '다 먹었어요'나 '삭제'를 눌러 주세요.")
            return
        try:
            set_items(update_item(st.session_state.fridge["items"], item_id, name=name, category=cat, qty=qty,
                                  unit=unit, location=loc, bought=bought, expiry=expiry))
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    c1, c2 = st.columns(2)
    if c1.button("😋 다 먹었어요", use_container_width=True, help="냉장고에서 빼고 장보기 목록에 담아요"):
        set_items([x for x in st.session_state.fridge["items"] if x["id"] != item_id])
        add_to_shop(it["name"], "다 먹음")
        st.rerun()
    if c2.button("🗑️ 삭제", use_container_width=True):
        set_items([x for x in st.session_state.fridge["items"] if x["id"] != item_id])
        st.rerun()


@st.dialog("🍳 요리했어요")
def cook_dialog(recipe):
    items = st.session_state.fridge["items"]
    plan = plan_usage(items, recipe, today)
    st.markdown(f"**{recipe['icon']} {recipe['name']}**에 쓴 양만큼 냉장고에서 빼 드릴게요. 실제로 쓴 양으로 고쳐도 돼요.")
    uses = {}
    for p in plan:
        uses[p["name"]] = st.number_input(
            f"{icon_for(p['name'])} {p['name']} · {p['unit']} 단위 (남은 양 {fmt_qty(p['have'])}{p['unit']})",
            min_value=0.0, max_value=float(p["have"]), value=float(p["use"]),
            step=1.0 if p["unit"] not in ("g", "ml") else 50.0, format="%g", key=f"use_{recipe['name']}_{p['name']}")
        if p["mismatch"]:
            st.caption(f"⚠️ 레시피는 {fmt_qty(p['recipe_amt'])}{p['recipe_unit']} 기준인데 냉장고엔 "
                       f"{p['unit']} 단위로 있어서 자동으로 못 정했어요. 쓴 양을 직접 넣어 주세요.")
    if not plan:
        st.info("냉장고에 이 요리에 쓸 재료가 없어요.")
    if st.button("냉장고에서 빼기", type="primary", use_container_width=True, disabled=not plan):
        left, used_up = apply_usage(items, uses, today)
        set_items(left)
        for n in used_up:
            add_to_shop(n, "다 씀")
        msg = f"✅ {recipe['name']} 완성! 재료를 정리했어요."
        if used_up:
            msg += f" {', '.join(used_up)}{josa(used_up[-1], '은는')} 다 써서 장보기에 담았어요."
        st.session_state.flash = msg
        st.rerun()


# ================================================================ 헤더 + 요약
items = sort_by_expiry(fridge["items"])
grades = [status(x, today)[1] for x in items]
ready, almost = recommend(items, today)
brief = week_summary(items, today)

st.markdown(f"### 🧊 자취 냉장고 <span style='font-size:.85rem;color:#7b8494;font-weight:400'>{fmt_date(today)}</span>",
            unsafe_allow_html=True)
# 알림 자리는 항상 만들어 둔다: 알림이 있을 때만 생기면 아래 탭의 위치가 바뀌어 탭이 첫 화면으로 돌아감
flash_box = st.empty()
if "flash" in st.session_state:
    flash_box.success(st.session_state.pop("flash"))
st.markdown(f"""<div class="hero"><div class="label">냉장고 속 재료</div>
<div class="amount">{len(items)}가지</div>
<div class="sub"><span class="pill">🟡 임박 {grades.count('urgent')}</span>
<span class="pill">🔴 기한 지남 {grades.count('expired')}</span>
<span class="pill">🍳 바로 가능한 요리 {len(ready)}</span></div></div>""", unsafe_allow_html=True)

# 탭 이름은 고정해야 함: 이름이 바뀌면(예: "장보기 2") Streamlit이 새 탭으로 보고 첫 탭으로 돌아가 버림
tab_home, tab_add, tab_cook, tab_shop, tab_set = st.tabs(["🧊 냉장고", "➕ 넣기", "🍳 요리", "🛒 장보기", "⚙️ 설정"])

# ================================================================ 냉장고
with tab_home:
    if not items:
        st.markdown('<div class="empty"><div class="big">🧊</div>냉장고가 비어 있어요.<br>'
                    '<b>➕ 넣기</b> 탭에서 재료를 넣거나, 예시로 먼저 둘러보세요.</div>', unsafe_allow_html=True)
        st.button("예시 냉장고로 체험하기", on_click=load_sample, use_container_width=True, type="primary")
    else:
        st.markdown('<div class="brief"><div class="t">🤖 이번 주 냉장고 브리핑</div>'
                    + "".join(f"<p>{md_bold(line)}</p>" for line in brief["lines"]) + "</div>", unsafe_allow_html=True)
        where = st.segmented_control("보관 위치", ["전체"] + LOCATIONS, default="전체", label_visibility="collapsed")
        shown = [x for x in items if where in (None, "전체") or x["location"] == where]
        groups = [("expired", "🔴 기한 지남", "상태를 확인하고 정리해 주세요"),
                  ("urgent", f"🟡 임박 ({URGENT_DAYS}일 이내)", "먼저 먹어요"), ("ok", "🟢 여유", "")]
        for grade, title, hint in groups:
            rows = [x for x in shown if status(x, today)[1] == grade]
            if not rows:
                continue
            st.markdown(f'<div class="group">{title} <span class="n">{len(rows)}개{" · " + hint if hint else ""}</span></div>',
                        unsafe_allow_html=True)
            for x in rows:
                label, _ = status(x, today)
                with st.container(key=f"row_{x['id']}"):
                    c1, c2 = st.columns([7, 1], vertical_alignment="center")
                    c1.markdown(f"""<div class="info"><div class="icon">{icon_for(x['name'], x['category'])}</div>
<div class="txt"><div class="name">{html.escape(x['name'])} <span class="qty">{fmt_qty(x['qty'])}{html.escape(x['unit'])}</span>
<span class="badge b-{grade}">{label}</span></div>
<div class="meta">{x['category']} · {LOCATION_ICONS[x['location']]} {x['location']} · {fmt_date(x['expiry'])}까지</div></div></div>""",
                                unsafe_allow_html=True)
                    if c2.button("✏️", key=f"edit_{x['id']}", help="수정 / 삭제"):
                        edit_dialog(x["id"])
        if not shown:
            st.info(f"{where} 칸이 비어 있어요.")

# ================================================================ 넣기
with tab_add:
    st.markdown('<div class="section">⚡ 빠른 추가 <span style="font-size:.8rem;color:#7b8494;font-weight:400">'
                '한 번 누르면 기본 수량·유통기한으로 바로 넣어요</span></div>', unsafe_allow_html=True)
    with st.container(key="quick"):
        for row in (QUICK_ADD[:4], QUICK_ADD[4:]):
            cols = st.columns(4)
            for c, n in zip(cols, row):
                c.button(f"{INGREDIENTS[n]['icon']} {n}", key=f"q_{n}", on_click=quick_add, args=(n,),
                         use_container_width=True)

    st.markdown('<div class="section">✍️ 자세히 넣기</div>', unsafe_allow_html=True)
    fid = st.session_state.form_id
    options = [f"{v['icon']} {k}" for k, v in INGREDIENTS.items()] + ["✏️ 직접 입력"]
    choice = st.selectbox("재료", options, index=None, placeholder="재료를 고르거나 검색 (예: 계란)", key=f"choice{fid}")
    if choice == "✏️ 직접 입력":
        name = st.text_input("재료 이름", placeholder="예: 고수", key=f"name{fid}")
    else:
        name = choice.split(" ", 1)[1] if choice else ""
    p = preset(name) if name else None
    k = f"{fid}_{name}"
    cat = st.selectbox("카테고리", list(CATEGORIES), index=list(CATEGORIES).index(p["category"] if p else "기타"),
                       format_func=lambda c: f"{CATEGORIES[c]} {c}", key=f"cat{k}")
    with st.container(key="qtyrow"):
        c1, c2 = st.columns([3, 2])
        unit0 = p["unit"] if p else "개"
        qty = c1.number_input("수량", min_value=0.0, value=float(p["qty"]) if p else 1.0,
                              step=50.0 if unit0 in ("g", "ml") else 1.0, format="%g", key=f"qty{k}")
        unit = c2.selectbox("단위", UNITS, index=UNITS.index(unit0), key=f"unit{k}")
    loc = st.radio("보관 위치", LOCATIONS, index=LOCATIONS.index(p["location"] if p else "냉장"), horizontal=True,
                   key=f"loc{k}", format_func=lambda l: f"{LOCATION_ICONS[l]} {l}")
    bought = st.date_input("산 날짜", value=today, max_value=today, format="YYYY.MM.DD", key=f"bought{fid}")
    suggested = suggest_expiry(name, loc, bought) if name else None
    expiry = st.date_input("유통기한 (이 날짜까지)", value=suggested or bought + timedelta(days=7), min_value=bought,
                           format="YYYY.MM.DD", key=f"exp{k}_{loc}_{bought}")
    if suggested:
        st.caption(f"💡 {name}{josa(name)} {loc} 보관 시 보통 {(suggested - bought).days}일 정도라 "
                   f"{fmt_date(suggested)}로 넣어 뒀어요. 포장지 날짜가 있으면 그걸로 바꿔 주세요.")
    elif name:
        st.caption("📦 포장지에 적힌 유통기한을 확인해서 넣어 주세요.")
    if st.button("냉장고에 넣기", type="primary", use_container_width=True):
        try:
            fridge["items"].append(make_item(name, cat, qty, unit, loc, bought, expiry))
            st.session_state.form_id += 1
            st.session_state.flash = f"✅ {name.strip()} {fmt_qty(qty)}{unit} 넣었어요!"
            st.rerun()
        except ValueError as e:
            st.error(str(e) if name.strip() else "재료를 골라 주세요.")


# ================================================================ 요리
def chips(r, missing=False):
    out = "".join(f'<span class="chip{" hot" if n in r["urgent_used"] else ""}">{icon_for(n)} {n}</span>'
                  for n in r["used"])
    if missing:
        out += "".join(f'<span class="chip miss">+ {n}</span>' for n in r["missing"])
    return out


with tab_cook:
    if not items:
        st.markdown('<div class="empty"><div class="big">🍳</div>재료를 넣으면 만들 수 있는 요리를 알려드려요.</div>',
                    unsafe_allow_html=True)
    else:
        st.caption("소금, 간장, 고추장, 된장, 식용유 같은 기본 양념은 있다고 가정했어요. 기한 지난 재료는 빼고 계산해요. "
                   "노란 재료는 곧 상하는 재료예요.")
        st.markdown('<div class="section">지금 바로 만들 수 있어요</div>', unsafe_allow_html=True)
        if not ready:
            st.info("지금 재료로 바로 만들 수 있는 요리는 없어요. "
                    + ("아래 요리는 재료 1~2개만 더 있으면 돼요." if almost else "계란, 밥, 라면 같은 기본 재료를 넣어 보세요."))
        for i, r in enumerate(ready):
            with st.container(border=True, key=f"recipe_r{i}"):
                hot = (f' · <b style="color:#b45309">곧 상하는 {", ".join(r["urgent_main"])} 해결!</b>'
                       if r["urgent_main"] else "")
                warn = "".join(f'<div class="warn">⚠️ 양 부족: {s}</div>' for s in r["shortage"])
                st.markdown(f'<div class="rtitle">{r["icon"]} {r["name"]}</div>'
                            f'<div class="meta">⏱ 약 {r["min"]}분{hot}</div><div>{chips(r)}</div>{warn}',
                            unsafe_allow_html=True)
                if st.button("🍳 만들었어요 (재료 차감)", key=f"cook_{i}", use_container_width=True):
                    cook_dialog(r)
        if almost:
            st.markdown('<div class="section">재료 1~2개만 더 있으면 돼요</div>', unsafe_allow_html=True)
            for i, r in enumerate(almost[:8]):
                with st.container(border=True, key=f"recipe_a{i}"):
                    hot = (f' · <b style="color:#b45309">곧 상하는 {", ".join(r["urgent_main"])} 사용</b>'
                           if r["urgent_main"] else "")
                    st.markdown(f'<div class="rtitle">{r["icon"]} {r["name"]}</div>'
                                f'<div class="meta">⏱ 약 {r["min"]}분 · {len(r["missing"])}개 부족{hot}</div>'
                                f'<div>{chips(r, missing=True)}</div>', unsafe_allow_html=True)
                    if st.button(f"🛒 {', '.join(r['missing'])} 장보기에 담기", key=f"shopadd_{i}",
                                 use_container_width=True):
                        added = [n for n in r["missing"] if add_to_shop(n, f"{r['name']} 재료")]
                        st.toast(f"🛒 {', '.join(added)} 담았어요" if added else "이미 장보기 목록에 있어요")
                        st.rerun()

# ================================================================ 장보기
with tab_shop:
    with st.form("shop_form", clear_on_submit=True, border=False):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        new = c1.text_input("장볼 재료", placeholder="예: 우유")
        if c2.form_submit_button("추가", use_container_width=True):
            if not add_to_shop(new, "직접 추가"):
                st.toast("이미 목록에 있거나 이름이 비어 있어요")
    shop = fridge["shopping"]
    todo = [s for s in shop if not s["done"]]
    done = [s for s in shop if s["done"]]
    if not shop:
        st.markdown('<div class="empty"><div class="big">🛒</div>장보기 목록이 비어 있어요.<br>'
                    '요리하다 다 쓴 재료나, 요리 탭의 부족한 재료가 여기에 담겨요.</div>', unsafe_allow_html=True)
    if todo:
        st.markdown(f'<div class="group">살 것 <span class="n">{len(todo)}개</span></div>', unsafe_allow_html=True)
        for s in todo:
            with st.container(key=f"row_shop_{s['id']}"):
                c1, c2, c3 = st.columns([6, 1, 1], vertical_alignment="center")
                c1.markdown(f'<div class="info"><div class="icon">{icon_for(s["name"])}</div><div class="txt">'
                            f'<div class="name">{html.escape(s["name"])}</div>'
                            f'<div class="meta">{html.escape(s.get("reason") or "")}</div></div></div>',
                            unsafe_allow_html=True)
                if c2.button("✅", key=f"buy_{s['id']}", help="샀어요"):
                    s["done"] = True
                    st.rerun()
                if c3.button("✖️", key=f"del_{s['id']}", help="목록에서 지우기"):
                    fridge["shopping"] = [x for x in shop if x["id"] != s["id"]]
                    st.rerun()
    if done:
        st.markdown(f'<div class="group">산 것 <span class="n">{len(done)}개 · 🧊를 누르면 기본값으로 냉장고에 넣어요</span></div>',
                    unsafe_allow_html=True)
        for s in done:
            with st.container(key=f"row_done_{s['id']}"):
                c1, c2, c3 = st.columns([6, 1, 1], vertical_alignment="center")
                c1.markdown(f'<div class="info"><div class="icon">{icon_for(s["name"])}</div><div class="txt">'
                            f'<div class="name shopdone">{html.escape(s["name"])}</div></div></div>',
                            unsafe_allow_html=True)
                known = s["name"] in INGREDIENTS
                if c2.button("🧊", key=f"tofridge_{s['id']}", help="냉장고에 넣기" if known else "직접 입력 재료는 넣기 탭에서",
                             disabled=not known):
                    quick_add(s["name"])
                    fridge["shopping"] = [x for x in shop if x["id"] != s["id"]]
                    st.rerun()
                if c3.button("✖️", key=f"deldone_{s['id']}", help="목록에서 지우기"):
                    fridge["shopping"] = [x for x in shop if x["id"] != s["id"]]
                    st.rerun()

# ================================================================ 설정
with tab_set:
    st.markdown('<div class="section">💾 저장 / 불러오기</div>', unsafe_allow_html=True)
    st.caption("새로고침하거나 창을 닫으면 목록이 사라져요. 파일로 저장해 두었다가 다음에 불러오세요.")
    st.download_button("📥 내 냉장고 파일로 저장", to_json(fridge), "my_fridge.json", "application/json",
                       disabled=not (fridge["items"] or fridge["shopping"]), use_container_width=True)
    uploaded = st.file_uploader("📤 저장한 파일 불러오기", type="json")
    if uploaded is not None and st.session_state.get("loaded_file") != uploaded.file_id:
        try:
            st.session_state.fridge = from_json(uploaded.getvalue().decode("utf-8"))
            st.session_state.loaded_file = uploaded.file_id
            st.session_state.flash = "📤 불러왔어요!"
            st.rerun()
        except (ValueError, UnicodeDecodeError) as e:
            st.error(f"파일을 읽을 수 없어요: {e}")

    st.markdown('<div class="section">🧪 기타</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.button("예시 냉장고로 바꾸기", on_click=load_sample, use_container_width=True,
              help="지금 목록을 지우고 예시 재료 12가지로 바꿔요.")
    if c2.button("전부 비우기", use_container_width=True, disabled=not (fridge["items"] or fridge["shopping"])):
        st.session_state.fridge = empty_fridge()
        st.rerun()
    st.caption("ℹ️ 보관 기간은 일반적인 참고 기준이에요. 실제로는 포장지 날짜와 재료 상태를 먼저 확인하세요. "
               "이번 주 브리핑과 요리 추천은 냉장고 데이터를 규칙에 따라 분석해서 만들어요.")
