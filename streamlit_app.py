## Inspiration - Inspiracija
### https://github.com/jasminkotraining-eng/VATA_Lotto


"""
VATA_Lotto — Streamlit GUI (bez tkinter) 

cd /Users/4c/Desktop/GHQ/kurzor/VATA_Lotto-main
streamlit run streamlit_app.py
"""


from pathlib import Path

import streamlit as st

from vata_engine import (
    SEED,
    build_filter_table_rows,
    fill_pool_from_filters,
    fill_pool_random,
    filter_table_to_tsv,
    freq_table_lines,
    get_all_possible_patterns,
    next_ticket_closest_to_100_pct,
    parse_draw_lines,
    rows_to_pool,
    run_engine,
)

DEFAULT_CSV = Path("/Users/4c/Desktop/GHQ/kurzor/data/loto7hh_4596_k29.csv")

st.set_page_config(
    page_title="VATA_Lotto",
    layout="wide",
    initial_sidebar_state="expanded",
)

for _k, _def in (
    ("hist_ta", ""),
    ("history", []),
    ("ms_numbers", []),
    ("ms_sums", []),
    ("ms_consec", []),
    ("ms_repeats", []),
    ("committed_numbers", set()),
    ("committed_sum_oe", set()),
    ("committed_consec", set()),
    ("committed_repeats", set()),
    ("cfg_total_nums", 39),
    ("cfg_draws", 6),
    ("display_next_only", False),
    ("hint_opt", False),
):
    if _k not in st.session_state:
        st.session_state[_k] = _def


def flush_pending_hist_ta():
    """Pre widgeta sa key=hist_ta: primeni izmenu iz hist_ta_new (Streamlit zabrana direktnog seta posle widgeta)."""
    if "hist_ta_new" in st.session_state:
        st.session_state.hist_ta = st.session_state.pop("hist_ta_new")


def filter_subtab(
    mode: str,
    items: list,
    ms_key: str,
    com_key: str,
    history: list,
    total_nums: int,
    draws: int,
    trend_window: int,
    trend_w: float,
    vol_p: float,
    sens: float,
    use_hist: bool,
):
    sel_set = set(st.session_state[ms_key])
    rows = build_filter_table_rows(
        mode,
        items,
        history,
        total_nums,
        draws,
        trend_window,
        trend_w,
        vol_p,
        sens,
        use_hist,
        sel_set,
    )
    tsv = filter_table_to_tsv(rows)

    top_a, top_b = st.columns([1.2, 3])
    with top_a:
        st.download_button(
            "Preuzmi tabelu (TSV)",
            tsv.encode("utf-8"),
            file_name=f"vata_filter_{mode}.tsv",
            mime="text/tab-separated-values",
            key=f"dl_{mode}",
        )
    with top_b:
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("Select All", key=f"sa_{mode}"):
                st.session_state[ms_key] = list(items)
                st.rerun()
        with b2:
            if st.button("Deselect All", key=f"sn_{mode}"):
                st.session_state[ms_key] = []
                st.rerun()
        with b3:
            if st.button("Invert", key=f"si_{mode}"):
                cur = set(st.session_state[ms_key])
                st.session_state[ms_key] = [x for x in items if x not in cur]
                st.rerun()
        with b4:
            st.metric("Selected", len(st.session_state[ms_key]))

    st.multiselect(
        "Izbor stavki (Sel)",
        options=list(items),
        key=ms_key,
    )

    st.dataframe(rows, use_container_width=True, height=min(520, 120 + 28 * len(rows)))

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Commit", type="primary", key=f"com_{mode}"):
            st.session_state[com_key] = set(st.session_state[ms_key])
            st.success(f"Commit: {len(st.session_state[com_key])} stavki.")
    with c2:
        st.caption(f"U Commit memoriji: {len(st.session_state[com_key])}")


def main_tab():
    st.title("VATA_Lotto — THE LOTTERY OF THE LAST RUN")

    st.subheader("System Configuration")
    cc1, cc2, cc3 = st.columns([1, 1, 2])
    with cc1:
        total_nums = st.number_input(
            "Total Nums", 1, 99, st.session_state.cfg_total_nums, step=1, key="cfg_total_nums"
        )
    with cc2:
        draws = st.number_input(
            "Draw Size", 1, 20, st.session_state.cfg_draws, step=1, key="cfg_draws"
        )
    with cc3:
        use_hist = st.checkbox("Use History", value=bool(st.session_state.history))

    c1, c2 = st.columns([1.1, 1], gap="medium")

    with c1:
        st.subheader("Draw History")
        st.text_area(
            "Istorija",
            height=280,
            key="hist_ta",
            label_visibility="collapsed",
        )
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Validate"):
                ta = st.session_state.hist_ta
                rows, fmt = parse_draw_lines(ta, int(draws), int(total_nums))
                if rows:
                    st.session_state.history = rows
                    st.session_state.hist_ta_new = "\n".join(fmt)
                    st.success(f"Uvezeno {len(rows)} izvlacenja.")
                    st.rerun()
                else:
                    st.warning(f"Nijedan red ne odgovara (Pick {draws} from {total_nums}).")
        with b2:
            uploaded = st.file_uploader("Import", type=["csv", "txt"], key="csv_uploader")
            if uploaded is not None:
                up_key = f"{uploaded.name}-{uploaded.size}"
                if st.session_state.get("_import_key") != up_key:
                    st.session_state._import_key = up_key
                    st.session_state.hist_ta_new = uploaded.read().decode(
                        "utf-8", errors="replace"
                    )
                    st.rerun()
        with b3:
            if st.button("Clear"):
                st.session_state.history = []
                st.session_state.hist_ta_new = ""
                st.session_state.pop("_import_key", None)
                st.session_state.pop("opt_bundle", None)
                st.session_state.display_next_only = False
                st.rerun()
        st.caption("Paste u polje, ili Import, pa Validate.")

    with c2:
        st.subheader("Parametri")
        hist_ok = bool(st.session_state.history) and use_hist
        tw = st.number_input(
            "Trend Window",
            1,
            1000,
            20,
            step=1,
            disabled=not hist_ok,
            key="tw_main",
        )
        twg = st.slider(
            "Trend Weight",
            0.0,
            1.0,
            0.3,
            0.1,
            disabled=not hist_ok,
            key="twg_main",
        )
        volp = st.slider(
            "Volatility Penalty",
            0.0,
            1.0,
            0.2,
            0.1,
            disabled=not hist_ok,
            key="volp_main",
        )
        sens = st.slider(
            "Sensitivity",
            0.1,
            0.9,
            0.5,
            0.1,
            disabled=not hist_ok,
            key="sens_main",
        )
        if st.button("Clear All Filter Selections", key="clr_all_sel"):
            st.session_state.ms_numbers = []
            st.session_state.ms_sums = []
            st.session_state.ms_consec = []
            st.session_state.ms_repeats = []
            st.rerun()
        if st.button("Clear Commitments", key="clr_all_com"):
            st.session_state.committed_numbers = set()
            st.session_state.committed_sum_oe = set()
            st.session_state.committed_consec = set()
            st.session_state.committed_repeats = set()
            st.rerun()
        if st.button("OPTIMIZE!", type="primary", key="main_optimize"):
            st.session_state.hint_opt = True
        if st.session_state.hint_opt:
            st.info("Otvorite tab **Optimizacija** ispod i pokrenite motor (pool + Cond + režim).")
        if not hist_ok:
            st.caption("Use History + validirana istorija potrebni za Trend kolone.")

    st.divider()
    st.subheader("Filteri (Numbers / Sums / Patterns / Repeats)")
    items_num = [str(i) for i in range(1, int(total_nums) + 1)]
    items_sum = ["Odd Sum", "Even Sum"]
    items_pat = get_all_possible_patterns(int(draws))
    items_rep = [str(i) for i in range(int(draws) + 1)]

    ft1, ft2, ft3, ft4 = st.tabs(["Numbers", "Sums O/E", "Patterns", "Repeats"])
    with ft1:
        filter_subtab(
            "numbers",
            items_num,
            "ms_numbers",
            "committed_numbers",
            st.session_state.history,
            int(total_nums),
            int(draws),
            int(tw),
            float(twg),
            float(volp),
            float(sens),
            use_hist,
        )
    with ft2:
        filter_subtab(
            "sum_oe",
            items_sum,
            "ms_sums",
            "committed_sum_oe",
            st.session_state.history,
            int(total_nums),
            int(draws),
            int(tw),
            float(twg),
            float(volp),
            float(sens),
            use_hist,
        )
    with ft3:
        filter_subtab(
            "consec",
            items_pat,
            "ms_consec",
            "committed_consec",
            st.session_state.history,
            int(total_nums),
            int(draws),
            int(tw),
            float(twg),
            float(volp),
            float(sens),
            use_hist,
        )
    with ft4:
        filter_subtab(
            "repeats",
            items_rep,
            "ms_repeats",
            "committed_repeats",
            st.session_state.history,
            int(total_nums),
            int(draws),
            int(tw),
            float(twg),
            float(volp),
            float(sens),
            use_hist,
        )


def optimize_tab():
    st.subheader("Optimization Engine")
    st.caption(f"Fiksni seed motora: **{SEED}** (isti ulaz → ista NEXT).")

    total_nums = int(st.session_state.get("cfg_total_nums", 39))
    draws = int(st.session_state.get("cfg_draws", 6))

    src = st.radio(
        "Izvor pool-a",
        ["Istorija (ceo validiran CSV)", "Iz filtera (Commit brojeva)", "Slučajno", "Datoteka (samo pool)"],
        horizontal=True,
        key="pool_src",
    )

    pool = []
    pool_note = ""

    if src == "Istorija (ceo validiran CSV)":
        if not st.session_state.history:
            st.info("Učitaj istoriju u tabu **Glavni** (Validate).")
            return
        pool = rows_to_pool(st.session_state.history)
        pool_note = "Pool = sve validirane kombinacije iz istorije."

    elif src == "Iz filtera (Commit brojeva)":
        if not st.session_state.committed_numbers:
            st.warning("Prvo u tabu **Glavni → Numbers** uradite **Commit** na skupu brojeva.")
            return
        pool = fill_pool_from_filters(
            st.session_state.committed_numbers,
            st.session_state.committed_sum_oe,
            st.session_state.committed_consec,
            st.session_state.committed_repeats,
            st.session_state.history,
            total_nums,
            draws,
        )
        pool_note = f"Iz filtera: **{len(pool):,}** kombinacija (granica 500k)."

    elif src == "Slučajno":
        cnt = st.number_input("Broj slučajnih kombinacija", 1, 500_000, 2000, step=100, key="rand_pool_n")
        pool = fill_pool_random(int(cnt), total_nums, draws)
        pool_note = f"Slučajno: **{len(pool):,}** (seed={SEED})."

    else:
        up = st.file_uploader("Pool fajl (csv/txt, isti format kao istorija)", type=["csv", "txt"], key="pool_file")
        if up is None:
            st.info("Izaberite datoteku za pool.")
            return
        raw = up.read().decode("utf-8", errors="replace")
        rows, _ = parse_draw_lines(raw, draws, total_nums)
        pool = rows_to_pool(rows)
        pool_note = f"Iz datoteke: **{len(pool):,}** kombinacija."

    st.write(f"**Pool:** {len(pool):,} kombinacija. {pool_note}")
    if len(pool) >= 800:
        st.warning("Veliki pool — može potrajati.")

    colp, colc = st.columns([2, 1])
    with colc:
        t_then = st.number_input("Cond", 1, 10, 3)
        t_if = st.number_input("if", 1, 20, draws)
        st.caption("Napomena: motor koristi **Cond** pri poklapanju sa članovima pool-a (polje **if** ostaje kao u Tk GUI).")
    with colp:
        mode = st.radio("Režim", ["Det", "Heur"], horizontal=True, key="opt_mode")

    prog = st.progress(0)

    c_run, c_clr = st.columns([1, 1])
    with c_clr:
        if st.button("Obriši izlaz optimizacije", key="clr_opt_out"):
            st.session_state.pop("opt_bundle", None)
            st.session_state.display_next_only = False
            st.rerun()

    run_clicked = c_run.button("Pokreni optimizaciju", type="primary", key="run_opt")

    if run_clicked:
        st.session_state.display_next_only = False

        def on_prog(p):
            prog.progress(min(1.0, max(0.0, p / 100.0)))

        with st.spinner("Optimizacija..."):
            tickets, freq, lines = run_engine(
                pool,
                "Det" if mode == "Det" else "Heur",
                int(t_then),
                progress_callback=on_prog,
            )
        prog.progress(1.0)
        nxt, pct, tn = next_ticket_closest_to_100_pct(tickets, lines)
        st.session_state.opt_bundle = {
            "lines": "\n".join(lines),
            "freq": freq_table_lines(freq),
            "nxt": nxt,
            "pct": pct,
            "tn": tn,
            "caption": (
                f"Ukupno tiketa: {len(tickets)} | if={t_if} (GUI) | Cond={t_then} | "
                f"izvor: {src}"
            ),
        }
        st.rerun()

    ob = st.session_state.get("opt_bundle")
    if ob:
        left, right = st.columns([1.4, 1])
        with left:
            st.text_area("Tiketi", ob["lines"], height=400, key="ta_tickets")
        with right:
            st.text_area("Frekvencije", ob["freq"], height=400, key="ta_freq")

        full_txt = ob["lines"] + "\n\n" + ob["freq"]
        st.download_button(
            "Preuzmi za Excel (TXT)",
            full_txt.encode("utf-8"),
            file_name="vata_optimizacija.txt",
            mime="text/plain",
            key="dl_excel",
        )

        st.divider()
        if st.button("NEXT KOMBINACIJA", type="primary", key="btn_next"):
            st.session_state.display_next_only = True

        if st.session_state.display_next_only and ob.get("nxt") is not None:
            nums = ", ".join(f"{x:02d}" for x in ob["nxt"])
            st.markdown(f"### NEXT: `{nums}`")
            st.caption(f"T{ob['tn']} · kumulativ {ob['pct']:.1f}%")
        elif not st.session_state.display_next_only and ob.get("nxt") is not None:
            st.caption("Pritisnite **NEXT KOMBINACIJA** za izdvojen ispis jedne kombinacije.")

        st.caption(ob["caption"])

    st.caption(
        "Zaustavljanje tokom jednog pokretanja (STOP) u čistom Streamlit-u nije pouzdano; "
        "koristite manji pool ili drugi izvor."
    )


def extra_tab(name: str, script: str):
    st.subheader(name)
    st.caption("Tk verzija na ovoj mašini nije dostupna — pokretanje iz terminala.")
    st.code(
        "cd /Users/4c/Desktop/GHQ/kurzor/VATA_Lotto-main\npython3 " + script,
        language="bash",
    )


flush_pending_hist_ta()

tab_g, tab_o, tab_s, tab_v, tab_h = st.tabs(
    ["Glavni", "Optimizacija", "SimPro", "Validator", "CSV podrazumevano"]
)

with tab_g:
    main_tab()

with tab_o:
    optimize_tab()

with tab_s:
    extra_tab("VATA_SimPro", "VATA_SimPro.py")

with tab_v:
    extra_tab("VATA_Validator", "VATA_Validator.py")

with tab_h:
    st.subheader("Brzo učitavanje podrazumevanog CSV")
    path = st.text_input("Putanja", str(DEFAULT_CSV))
    if st.button("Učitaj fajl u polje istorije"):
        p = Path(path)
        if not p.is_file():
            st.error("Fajl ne postoji.")
        else:
            st.session_state.hist_ta_new = p.read_text(encoding="utf-8", errors="replace")
            st.rerun()




"""
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8502
  Network URL: http://192.168.1.23:8502



7/7
Det:  06, 09, 19, 25, 26, 34, 36
Heur: 01, 07, 09, 14, 24, 25, 34   


6/7
Det:  03, 05, 12, 17, 24, 27, 34
Heur: 04, 07, 12, 24, 27, 36, 38   


5/7
Det:  01, 09, 16, 19, 27, 32, 34
Heur: 08, 09, 11, 12, 31, 37, 39   


4/7
Det:  04, 05, 10, 27, 30, 38, 39
Heur: 07, 10, 22, 27, 29, 34, 38  


3/7
Det:   03, 17, 24, 25, 29, 31, 36
Heur:  03, 08, 15, 18, 26, 29, 37 


Num|Cnt
-------
 8|  9
34|  8
 7|  8
29|  8
32|  8
11|  7
38|  7
19|  7
21|  7
22|  7
16|  7
25|  7
27|  7
31|  7
33|  6
23|  6
35|  6
39|  6
17|  6
24|  6
37|  6
18|  6
26|  6
36|  6
13|  6
 9|  6
14|  6
15|  6
28|  6
 4|  6
 6|  6
 3|  5
12|  5
30|  5
 1|  5
 2|  5
 5|  5
10|  5
20|  4
"""





"""
Streamlit aplikacija VATA_Lotto — veb interfejs bez Tkinter. 
Učitava istoriju izvlačenja 
(paste, CSV upload, ili podrazumevana putanja u tabu „CSV podrazumevano“), 
validira redove prema Draw Size i Total Nums, 
čuva stanje u st.session_state. 
Tab Glavni: konfiguracija, istorija, parametri 
(Trend Window, klizači), 
dugmad za brisanje izbora/commitment-a, OPTIMIZE! 
uputstvo; pod-tabovi Numbers / Sums O/E / Patterns / Repeats 
sa tabelama (VATA statistika), multiselect, Select All / Invert, 
Commit u memoriju filtera. 
Tab Optimizacija: 
izvor pool-a (istorija, filteri, slučajno, fajl), Cond/if, Det/Heur, 
pokretanje run_engine iz vata_engine, prikaz tiketa i frekvencija, 
preuzimanje TXT, dugme NEXT KOMBINACIJA za izdvojen ispis jedne kombinacije. 
Tabovi SimPro i Validator: uputstvo za pokretanje odgovarajućih .py skripti iz terminala. 
Koristi flush_pending_hist_ta zbog Streamlit ograničenja sa text_area i key.



UI — istorija (paste / upload / default CSV putanja), 
tab Optimizacija zove run_engine i prikazuje tikete 
+ frekvencije + „sledeći“ tiket.

hist_ta_new + flush_pending_hist_ta 
rešava Streamlit ograničenje sa key na text_area.

(prikaz i dugmad) 
Glavni (konfiguracija, istorija, Import/Validate/Clear, 
parametri, dugmad za filtere, tabovi ili isti tok 
kao Numbers/Sums/Patterns/Repeats sa tabelom + Commit), 
Optimizacija (veličina pool-a, izvori pool-a, Cond/if, 
režim, izlaz T + Num|Cnt), 
posebno dugme NEXT KOMBINACIJA koje ispisuje 
samo jednu sledeću kombinaciju. 
SimPro i Validator kasnije u isti Streamlit

istorija, parametri povezani sa tabelama 
(Trend Window + klizači, onemogućeni bez istorije + Use History), 
Clear selections / Clear commitments, OPTIMIZE! 
+ kratko uputstvo za tab Optimizacija

Filteri u pod-tabovima Numbers / Sums O/E / Patterns / Repeats: 
tabela, Select All / Deselect All / Invert, Preuzmi TSV, multiselect, Commit

Optimizacija: 
izvor pool-a — istorija, iz filtera, slučajno (+ broj), datoteka; 
Cond + if (napomena da motor koristi Cond); progress; 
Obriši izlaz; Preuzmi za Excel (TXT); 
NEXT KOMBINACIJA 
→ posebno prikazuje samo jednu kombinaciju 
(prethodno sakrivena dok ne pritisneš dugme)

STOP nije dodat — u čistom Streamlit-u tokom jednog CPU ciklusa nije pouzdan; 
obrazloženje u caption-u ispod
"""
