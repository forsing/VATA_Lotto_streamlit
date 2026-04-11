## Inspiration - Inspiracija
### https://github.com/jasminkotraining-eng/VATA_Lotto


"""
Jezgro bez tkinter-a: 
isti algoritam kao VATA_Lotto.run_engine 
i validate istorije (CSV/tekst).
"""


import itertools
import math
import random
import re
from collections import Counter

# Fiksni seed: isti ulaz (isti pool redosled) -> isti tiketi i ista NEXT kombinacija.
SEED = 39


def parse_draw_lines(text: str, k: int, n_max: int):
    """Kao validate_history u VATA_Lotto: vraca (rows, formatted_lines)."""
    rows = []
    formatted = []
    for line in text.splitlines():
        line_content = line.strip()
        if not line_content:
            continue
        parts = line_content.replace(",", " ").split()
        if parts and str(parts[0]).lower().startswith("num"):
            continue
        try:
            nums = sorted(int(x) for x in parts if x.strip())
        except ValueError:
            continue
        if len(nums) == k and all(1 <= x <= n_max for x in nums):
            rows.append(list(nums))
            formatted.append(", ".join(f"{x:02d}" for x in nums))
    return rows, formatted


def rows_to_pool(rows):
    """Istorija kao lista setova (jedinstvene kombinacije po indeksu)."""
    return [set(row) for row in rows]


def get_pattern(nums):
    nums = sorted(nums)
    gs, ct = [], 1
    for i in range(len(nums) - 1):
        if nums[i + 1] == nums[i] + 1:
            ct += 1
        else:
            gs.append(ct)
            ct = 1
    gs.append(ct)
    return " ".join(map(str, sorted(gs, reverse=True)))


def get_all_possible_patterns(k: int):
    def ps(n):
        if n == 0:
            yield []
        else:
            for i in range(1, n + 1):
                for p in ps(n - i):
                    yield sorted([i] + p, reverse=True)

    u = set(tuple(p) for p in ps(k))
    return [" ".join(map(str, p)) for p in sorted(u, reverse=True, key=lambda x: (len(x), x))]


def get_consec_theo(p, n: int, k: int) -> float:
    try:
        parts = [int(x) for x in str(p).split()]
        m = len(parts)
        c = Counter(parts)
        np = math.factorial(m)
        for v in c.values():
            np //= math.factorial(v)
        return (math.comb(n - k + 1, m) * np) / math.comb(n, k)
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0.0


def get_repeats_theo(rep_k: int, n: int, draws: int) -> float:
    r = draws
    try:
        return (math.comb(r, rep_k) * math.comb(n - r, r - rep_k)) / math.comb(n, r)
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0.0


def get_stats_v2(seq, window: int):
    if not seq:
        return [0, "", "0.0", "0.00", 0, 0, 0]

    rv = seq[-1]
    rc = 0
    for v in reversed(seq):
        if v == rv:
            rc += 1
        else:
            break

    hr, sr = [], []
    cv, ct = seq[0], 1
    for i in range(1, len(seq)):
        if seq[i] == cv:
            ct += 1
        else:
            if cv == 1:
                hr.append(ct)
            else:
                sr.append(ct)
            cv, ct = seq[i], 1
    if cv == 1:
        hr.append(ct)
    else:
        sr.append(ct)

    sign = "+" if rv == 1 else "-"
    rel = hr if rv == 1 else sr
    avg = sum(rel) / len(rel) if rel else 1.0
    ra = rc / avg if avg != 0 else 0
    emp = sum(seq)
    vol = (len(hr) + len(sr)) / len(seq) if len(seq) > 0 else 0
    sub = seq[-window:]
    trnd = (sum(sub) / len(sub)) - (emp / len(seq)) if (sub and len(seq) > 0) else 0
    return [rc, sign, f"{sign}{avg:.1f}", f"{sign}{ra:.2f}", vol, trnd, emp]


def _sequence_for_item(mode: str, item: str, history: list, draws: int):
    if not history:
        return []
    if mode == "numbers":
        return [1 if int(item) in d else 0 for d in history]
    if mode == "sum_oe":
        return [
            1
            if (sum(d) % 2 != 0 if item == "Odd Sum" else sum(d) % 2 == 0)
            else 0
            for d in history
        ]
    if mode == "consec":
        return [1 if get_pattern(d) == item else 0 for d in history]
    if mode == "repeats":
        t = int(item)
        return [
            1
            if len(set(history[i]).intersection(set(history[i - 1]))) == t
            else 0
            for i in range(1, len(history))
        ]
    return []


def build_filter_table_rows(
    mode: str,
    items: list,
    history: list,
    total_nums: int,
    draws: int,
    trend_window: int,
    trend_weight: float,
    vol_penalty: float,
    sensitivity: float,
    use_history: bool,
    selected: set,
):
    """
    Vraca listu dictova (kolone kao Tk Treeview) za prikaz tabele filtera.
    """
    has_hist = bool(use_history and history)
    w = max(1, int(trend_window))

    stats_list = []
    for item in items:
        if mode == "numbers":
            theo = 1.0 / total_nums
        elif mode == "sum_oe":
            theo = 0.5
        elif mode == "repeats":
            theo = get_repeats_theo(int(item), total_nums, draws)
        else:
            theo = get_consec_theo(item, total_nums, draws)

        seq = _sequence_for_item(mode, item, history, draws) if has_hist else []
        if has_hist and seq:
            s = get_stats_v2(seq, w)
            stats_list.append((item, s, seq, theo))
        else:
            stats_list.append((item, None, seq, theo))

    ra_m = 1
    t_max = 1
    v_max = 1
    for item, s, seq, theo in stats_list:
        if s is None:
            continue
        try:
            ra_m = max(ra_m, abs(float(s[3][1:])))
        except (ValueError, IndexError, TypeError):
            pass
        t_max = max(t_max, s[5])
        v_max = max(v_max, s[4])
    if ra_m == 0:
        ra_m = 1

    rows_out = []
    for item, s, seq, theo in stats_list:
        sel_mark = "✓" if item in selected else ""
        if has_hist and s is not None:
            ra_norm = (ra_m - abs(float(s[3][1:]))) / ra_m if ra_m else 0
            t_norm = s[5] / t_max if t_max else 0
            v_norm = s[4] / v_max if v_max else 0
            comp_val = max(
                0,
                (
                    (ra_norm * (1 - trend_weight))
                    + (t_norm * trend_weight)
                    - (v_norm * vol_penalty)
                )
                * 100,
            )
            thr = (1 - sensitivity) * 100
            sym = (
                ("001 ↑" if s[1] == "-" else "111 →")
                if comp_val >= thr
                else ("000 →" if s[1] == "-" else "110 ↑")
            )
            play = "YES" if comp_val >= thr else "NO"

            if mode == "numbers":
                total_balls = len(seq) * draws
                exp_val = total_balls * theo
            else:
                exp_val = len(seq) * theo
            exp = f"{exp_val:.2f}"
            ee = f"{s[6] - exp_val:.2f}"
            emp = str(s[6])
            recent = f"{s[1]}{s[0]}"
            avg_run = s[2]
            ra_val = s[3]
            vol = f"{s[4]:.2f}"
            trend = f"{s[5]:.2f}"
            comp = f"{comp_val:.2f}"
            theo_pct = f"{theo * 100:.2f}%"
        else:
            exp = emp = ee = recent = avg_run = ra_val = vol = trend = comp = sym = play = "--"
            theo_pct = f"{theo * 100:.2f}%"

        rows_out.append(
            {
                "Item": item,
                "Sel": sel_mark,
                "Theo%": theo_pct,
                "Exp": exp,
                "Emp": emp,
                "E-E": ee,
                "Recent": recent,
                "AvgRun": avg_run,
                "R/A": ra_val,
                "Vol": vol,
                "Trend": trend,
                "Composite": comp,
                "Symbol": sym,
                "Play?": play,
            }
        )
    return rows_out


def filter_table_to_tsv(rows: list) -> str:
    if not rows:
        return ""
    cols = list(rows[0].keys())
    lines = ["\t".join(cols)]
    for r in rows:
        lines.append("\t".join(str(r[c]) for c in cols))
    return "\n".join(lines)


def fill_pool_from_filters(
    committed_numbers: set,
    committed_sum_oe: set,
    committed_consec: set,
    committed_repeats: set,
    history: list,
    total_nums: int,
    draws: int,
):
    if not committed_numbers:
        return []
    nums = sorted(int(n) for n in committed_numbers)
    pool = []
    last = set(history[-1]) if history else set()
    for c in itertools.combinations(nums, draws):
        if committed_sum_oe:
            iso = sum(c) % 2 != 0
            if iso and "Odd Sum" not in committed_sum_oe:
                continue
            if not iso and "Even Sum" not in committed_sum_oe:
                continue
        if committed_consec and get_pattern(c) not in committed_consec:
            continue
        if committed_repeats and last:
            if str(len(set(c).intersection(last))) not in committed_repeats:
                continue
        pool.append(set(c))
        if len(pool) > 500_000:
            break
    return pool


def fill_pool_random(count: int, total_nums: int, draws: int):
    random.seed(SEED)
    return [
        set(random.sample(range(1, total_nums + 1), draws))
        for _ in range(max(0, int(count)))
    ]


def run_engine(pool, mode, t_then, progress_callback=None, stop_check=None):
    """
    Isto kao VATA_LottoEnhanced.run_engine (bez GUI / stop).
    Vraca: tickets (lista listi), freq (Counter), output_lines (T1... sa %).
    """
    random.seed(SEED)
    pool = list(pool)
    if not pool:
        return [], Counter(), []

    if mode == "Det":
        idx = random.randint(0, len(pool) - 1)
        pool = pool[idx:] + pool[:idx]
    else:
        pool = list(pool)
        random.shuffle(pool)

    covered, tickets, freq = set(), [], Counter()
    total_size = len(pool)
    lines = []

    while len(covered) < total_size:
        if stop_check and stop_check():
            break

        best_t, best_c = None, set()
        sample = (
            pool[:2000]
            if mode == "Det"
            else random.sample(pool, min(len(pool), 1000))
        )

        for t in sample:
            c = {
                i
                for i, cand in enumerate(pool)
                if i not in covered and len(t.intersection(cand)) >= t_then
            }
            if len(c) > len(best_c):
                best_c = c
                best_t = t

        if not best_t:
            break

        covered.update(best_c)
        tickets.append(sorted(list(best_t)))
        for n in best_t:
            freq[n] += 1

        prog = (len(covered) / total_size) * 100
        lines.append(
            f"T{len(tickets)}\t{', '.join(f'{x:02d}' for x in sorted(best_t))}\t{prog:.1f}%"
        )
        if progress_callback:
            progress_callback(prog)

    return tickets, freq, lines


def next_ticket_closest_to_100_pct(tickets, lines):
    """
    Posle pune optimizacije: jedan 'next' — korak sa najvecim kumulativnim % (najblize 100).
    Vraca (tiket_brojevi, kumulativ_pct, redni_broj_T) ili (None, 0.0, 0).
    """
    if not tickets or not lines:
        return None, 0.0, 0
    best_i, best_p = 0, -1.0
    for i, line in enumerate(lines):
        m = re.search(r"([\d.]+)%\s*$", line.strip())
        p = float(m.group(1)) if m else 0.0
        if p >= best_p:
            best_p = p
            best_i = i
    return tickets[best_i], best_p, best_i + 1


def freq_table_lines(freq: Counter):
    """Kolone kao u GUI Num|Cnt."""
    out = ["Num|Cnt", "-" * 7]
    for n, c in freq.most_common():
        out.append(f"{n:2d}|{c:3d}")
    return "\n".join(out)





"""
— jezgro bez Tkinter-a: 
parsiranje istorije (parse_draw_lines), 
gradnja pool-a kao liste skupova (rows_to_pool), 
filter matematika u duhu Tk VATA_Lotto 
(get_stats_v2, obrasci, Theo za sume/ponavljanja/obrasce, 
build_filter_table_rows, filter_table_to_tsv), 
punjenje pool-a iz Commit filtera (fill_pool_from_filters), 
slučajni pool (fill_pool_random, fiksni SEED), 
run_engine — isti heuristički motor kao u Tk 
(Det/Heur, uzorak po koraku, pokrivenost pool-a, 
opcioni progress_callback / stop_check), 
next_ticket_closest_to_100_pct za jednu „NEXT“ kombinaciju 
posle optimizacije, freq_table_lines za Num|Cnt.





ceo pool se koristi: 
total_size = len(pool) 
i pokrivenost se računa preko svih indeksa u pool-u

npr. 2000 (u Det režimu) je samo koliko kandidata-tiketa t 
gleda u jednoj iteraciji petlje: sample = pool[:2000]. 
Za svaki takav t i dalje se prolazi kroz ceo pool 
da se izračuna koliko još nepokrivenih kombinacija taj tiket pokriva.

U Heur režimu uzorak je min(len(pool), 1000) 
— opet ne skraćuje pool, 
samo koliko različitih t isproba po koraku.

Dakle: 
ograničenje je na širinu pretrage po koraku, 
ne na veličinu pool-a.

Zato što motor ne mora da stigne do 100% 
— petlja se prekida čim u jednom koraku nema napretka.

U run_engine posle izbora best_t iz uzorka, 
ako je best_t prazan (not best_t), izlazi se iz while 
— nijedan tiket iz uzorka (prvih 2000 u Det, ili do 1000 u Heur) 
ne pokriva više nijedan dosad nepokriveni indeks pool-a 
uz npr. Cond (len(t ∩ kombinacija) >= t_then).

Znači: na ~43.5% je verovatno ostalo puno kombinacija 
u pool-u koje više nijedan kandidat iz tog uzorka ne može da „uhvati“ sa zadatim Cond 
(ili je pokrivenje veoma retko pa algoritam zaglavi u smislu da uzorak ne daje best_t).

Šta utiče: 
visina Cond, oblik pool-a (istorija), 
i to što je pretraga heuristička 
(ne gledaju se svi mogući tiketi u svakom koraku, samo podskup).

Šta probati: 
smanjiti Cond, probati Heur (drugačiji uzorak), ili smanjiti pool (filteri) 
— bez menjanja koda, kao dijagnostika.

Ako se npr. vidi red „T2000“ i 43.5% na istom redu: 
to je kumulativni % posle 2000 tiketa; 
ako se tu zaustavilo, sledeći korak je verovatno bio best_t None 
(nema više napretka iz uzorka), 
ne zato što je „ograničenje 2000“ veličina pool-a.

Cond = 7: 
(mora svih 7 zajedničkih sa kombinacijom iz pool-a): 
gotovo nema tiketa koji „poveže“ veliki deo istorije 
— uzorak brzo nema best_t, kumulativ ostane nizak 
(npr. ~43%).

Cond = 3: 
mnogo kombinacija zadovoljava |t ∩ draw| ≥ 3, 
pokrivenost brzo raste — zato se vidi red tipa T35 
i puno bliže 100%.

To je stroga logika poklapanja + heuristički uzorak po koraku.



VATA method (Volatility, Agility, Trend, Analysis)  
— u filter tabelama se to vidi: Vol, Trend, R/A i Composite / Play? / YES / NO
su upravo takav sloj (fluktuacije + trend + agregat za odluku), 
a optimizacija posle toga radi na strukturisanom pool-u kombinacija.

VATA ovde prati obrasce u istoriji 
(volatilnost, trend, itd.) 
i pomaže da filtriraš / grupišeš kombinacije i pokrivanje pool-a. 

To nije dokaz da iz prošlih izvlačenja deterministički proizlazi sledeća kombinacija 
— u tipičnom lotou se pretpostavlja da su izvlačenja nezavisna, 
pa istorija ne daje statistički validno „predviđanje“ jedne sledeće kombinacije.

NEXT u ovoj aplikaciji dolazi iz optimizacije pokrivenosti 
(heuristika koja bira korak tiketa), 
ne iz modela koji je verifikovan kao prediktor sledećeg kola.

Može se koristiti model za strukturiran izbor kandidata; 
tretiranje toga kao sigurnog predviđanja žreba nije opravdano.

VATA kako je ovde implementiran prvenstveno 
meri i rangira stvari po istoriji (Vol, Trend, R/A, Composite…) 
i ne predstavlja zaseban, proveren prediktivni model 
sa trening/test podelom i metrikom greške na „sledećem“ vektoru.



„Last Run“ (Recent Run) = poslednji kraj niza
Recent = znak trenutnog niza 
+ dužina aktuelnog run-a od poslednjeg elementa seq, 
a seq ide redom kako je istorija u listi 
(najnovije = poslednji red u history). 
Ako CSV ikad bude obrnut, Recent gubi smisao 
— znaci da je bitno hronologija.



četiri filtera — Numbers, Sums O/E, Patterns, Repeats 
— kao minimalan skup za test VATA logike

tema za razvoj: koliko filtera i kojih.

To je čisto dizajn odluka: 
više filtera = bogatiji AND-ing i skuplji pool-build, 
ali i više posla (svaki filter treba seq, Theo, tabela). 
Četiri su dobar MVP; dalje se širi kad teorija i potreba kažu.

Za MVP i proveru VATA logike (istorija → statistika → Commit → AND na pool) 
— 4 su dobar broj: 
pokrivaju broj, sumu (p/n), oblik i vezu sa prethodnim kolom.

Dovoljno u smislu „radi celu priču bez raspadanja“. 
Nije gornja granica 
— kasnije se mogu dodati filtere kad teorija traži 
(npr. opsezi suma, paritet pojedinačnih brojeva, grupe), 
uz cenu složenosti i većeg pool-a.

Znači: dobar start, ne nužno konačan broj zauvek.



ide od npr. 35 do 4500 Tiketa
3 i 4 brže završe jer motor lakše nalazi pokrivenost; 
5-7 prirodno vuče više iteracija / sporiji napredak. 

~35 T — tipično kad Cond nizak (npr. 3/4): 
brzo pokrije veliki deo pool-a malo tiketa.
do ~4500 T — kad je Cond visok ili napredak po tiketu mali: 
treba mnogo koraka da se (pokuša) pokriti ceo pool; 
broj T može da bude reda veličine pool-a.
Det vs Heur menja redosled i izbor, 
ne nužno sam broj tiketa u istom scenariju, 
ali red veličine ostaje logičan.

— npr. pun istorijski pool x 5 Cond vrednosti x 2 režima 
= mnogo dugih prolaza, posebno dok motor u svakom koraku radi težak posao.

za skracivanje testiranja: 
privremeno manji pool (filter / manji CSV) 
ili samo jedan režim za grubo poređenje Cond 
— ali ako treba puna matrica, normalno je da se vrti dugo 
(na MacBook Pro to nije problem) 
"""
