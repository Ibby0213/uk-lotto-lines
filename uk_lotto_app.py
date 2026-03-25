import streamlit as st
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="UK Lotto Lines", page_icon="🎰", layout="wide")

st.title("🎰 UK Lotto Line Generator")
st.markdown("**One-button statistical lines** based on frequency, due scores, machine/ball-set patterns, and trends. *Data from Merseyworld.*")

if st.button("🚀 Generate Latest Lines", type="primary", use_container_width=True):
    with st.spinner("Fetching latest draws & computing..."):
        # Fetch data (same logic as before)
        resp = requests.get("https://lottery.merseyworld.com/lottery/lottery.htm")
        soup = BeautifulSoup(resp.text, "html.parser")
        tables = soup.find_all("table")
        main_table = max(tables, key=lambda t: len(t.find_all("tr")))
        rows = main_table.find_all("tr")
        data = []
        for tr in rows:
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) < 8: continue
            try:
                draw_no = int(tds[0])
                if draw_no < 2066: continue  # 1-59 era only
                balls = list(map(int, tds[2:8]))
                bonus = int(tds[8]) if len(tds) > 8 else None
                machine = tds[9] if len(tds) > 9 else None
                ball_set = tds[10] if len(tds) > 10 else None
                data.append({
                    "Draw": draw_no, "Ball1":balls[0], "Ball2":balls[1], "Ball3":balls[2],
                    "Ball4":balls[3], "Ball5":balls[4], "Ball6":balls[5], "Bonus":bonus,
                    "Machine":machine, "Set":ball_set
                })
            except: continue
        era = pd.DataFrame(data).sort_values("Draw")
        
        # Compute simplified composite scores (matching your PDF logic)
        balls = era[["Ball1","Ball2","Ball3","Ball4","Ball5","Ball6"]]
        freq = balls.stack().value_counts().reindex(range(1,60), fill_value=0)
        
        # Due scores
        due_raw = []
        for n in range(1,60):
            draws_with_n = era[balls.eq(n).any(axis=1)]["Draw"]
            if draws_with_n.empty:
                due_raw.append(0); continue
            gaps = draws_with_n.diff().dropna()
            avg_gap = gaps.mean()
            cur_gap = era["Draw"].max() - draws_with_n.iloc[-1]
            due_raw.append(max(0, (cur_gap - avg_gap)/avg_gap) if avg_gap else 0)
        max_due = max(due_raw)
        due_norm = [r/max_due if max_due else 0 for r in due_raw]
        
        # Simple composite: 60% freq + 40% due
        f_norm = [(f - freq.min()) / max(1, freq.max()-freq.min()) for f in freq]
        s_star = [0.6*f + 0.4*d for f,d in zip(f_norm, due_norm)]
        comp_df = pd.DataFrame({"Number":list(range(1,60)), "S_star":s_star, "DueNorm":due_norm})
        
        # Latest machine/set
        latest = era.iloc[-1]
        machine = latest["Machine"] or "Unknown"
        ball_set = latest["Set"] or "Unknown"
        next_draw = int(era["Draw"].max() + 1)
        
        # Build lines
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Next Draw", f"#{next_draw}")
            st.metric("Latest Machine", machine)
            st.metric("Latest Ball Set", ball_set)
        
        strategies = [("Composite", "S_star"), ("Due-weighted", "DueNorm")]
        lines = []
        for strategy, col in strategies:
            df_sorted = comp_df.sort_values(col, ascending=False).head(20)
            chosen = df_sorted["Number"].head(6).tolist()
            avg_score = df_sorted["S_star"].head(6).mean()
            lines.append({
                "Type": strategy, "Numbers": " - ".join(map(str, sorted(chosen))),
                "Avg Score": f"{avg_score:.3f}"
            })
        
        st.subheader("📊 Recommended Lines")
        st.dataframe(pd.DataFrame(lines), use_container_width=True)
        
        st.caption("*Statistical analysis only. Lotto is random. Play responsibly.*")
