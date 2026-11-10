from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


st.set_page_config(
    page_title="Analytics | Ανάλυση δεδομένων",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px;}
    [data-testid="stMetric"] {background: #f5f8fb; border: 1px solid #e4ebf1;
        padding: 1rem; border-radius: 0.8rem;}
    div[data-testid="stFileUploader"] {background: #f8fafc; padding: 1rem;
        border: 1px dashed #a8bac8; border-radius: 0.8rem;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## Analytics")
    st.caption("Εργαλείο διερευνητικής ανάλυσης επιχειρηματικών δεδομένων")
    st.divider()
    st.markdown("**Υποστηριζόμενα αρχεία**")
    st.caption("CSV, XLSX και XLS")
    st.markdown("**Ιδιωτικότητα**")
    st.caption("Το αρχείο επεξεργάζεται στη συνεδρία της εφαρμογής και δεν αποθηκεύεται από τον κώδικα σε βάση δεδομένων.")
    st.divider()
    st.caption("Οι προτάσεις είναι ενδεικτικές και υποστηρίζουν, δεν αντικαθιστούν, την ανθρώπινη κρίση.")

st.title("Ανάλυση επιχειρηματικών δεδομένων")
st.markdown("Μετέτρεψε τα δεδομένα προϊόντων σε σαφή εικόνα πωλήσεων, τάσεων και σημείων προς διερεύνηση.")
st.divider()


def read_upload(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(uploaded_file, sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            try:
                return pd.read_csv(uploaded_file, sep=None, engine="python", encoding="cp1253")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, sep=None, engine="python", encoding="latin-1")
    return pd.read_excel(uploaded_file)


def guess_column(columns, words):
    for col in columns:
        label = str(col).strip().lower()
        if any(word in label for word in words):
            return col
    return None


def euro(value):
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def make_pdf(data, product_col, sales_col, quantity_col, date_col, summary, advice, grouped):
    buffer = BytesIO()
    font_path_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    font_path = next((p for p in font_path_candidates if p.exists()), None)
    font_name = "Helvetica"
    if font_path:
        pdfmetrics.registerFont(TTFont("GreekFont", str(font_path)))
        font_name = "GreekFont"

    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=17*mm, bottomMargin=17*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="GreekTitle", parent=styles["Title"], fontName=font_name,
                              alignment=TA_CENTER, fontSize=18, leading=23, textColor=colors.HexColor("#15324b")))
    styles.add(ParagraphStyle(name="GreekBody", parent=styles["BodyText"], fontName=font_name,
                              fontSize=9.5, leading=14, spaceAfter=5))
    styles.add(ParagraphStyle(name="GreekHeading", parent=styles["Heading2"], fontName=font_name,
                              fontSize=13, leading=17, textColor=colors.HexColor("#15324b"), spaceBefore=10))
    story = [Paragraph("Αναφορά Ανάλυσης Επιχειρηματικών Δεδομένων", styles["GreekTitle"]),
             Spacer(1, 4*mm),
             Paragraph(f"Ημερομηνία δημιουργίας: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["GreekBody"]),
             Paragraph(f"Εγγραφές: {len(data):,} · Στήλες: {len(data.columns)}", styles["GreekBody"]),
             Paragraph("Βασικά στατιστικά", styles["GreekHeading"])]
    rows = [["Δείκτης", "Τιμή"]]
    rows.extend([[str(k), str(v)] for k, v in summary.items()])
    table = Table(rows, colWidths=[85*mm, 80*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15324b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#d5dee5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([table, Paragraph("Ευρήματα και προτάσεις", styles["GreekHeading"])])
    story.extend(Paragraph("• " + escape(item), styles["GreekBody"]) for item in advice)

    if product_col and not grouped.empty:
        fig, ax = plt.subplots(figsize=(8, 4.4))
        top = grouped.head(8).sort_values("value")
        ax.barh(top["product"].astype(str), top["value"], color="#2385a5")
        ax.set_title("Κορυφαία προϊόντα")
        ax.set_xlabel(str(sales_col or "Πλήθος εγγραφών"))
        fig.tight_layout()
        chart_buffer = BytesIO()
        fig.savefig(chart_buffer, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        chart_buffer.seek(0)
        story.extend([Paragraph("Επίδοση ανά προϊόν", styles["GreekHeading"]),
                      Image(chart_buffer, width=165*mm, height=90*mm)])
    if date_col and sales_col:
        date_values = pd.to_datetime(data[date_col], errors="coerce")
        trend = data.assign(_date=date_values, _sales=pd.to_numeric(data[sales_col], errors="coerce"))
        trend = trend.dropna(subset=["_date", "_sales"]).groupby(trend["_date"].dt.to_period("M"))["_sales"].sum()
        if len(trend) > 1:
            fig, ax = plt.subplots(figsize=(8, 3.5))
            ax.plot(trend.index.astype(str), trend.values, marker="o", color="#2385a5")
            ax.set_title("Πωλήσεις ανά μήνα")
            ax.tick_params(axis="x", rotation=35)
            fig.tight_layout()
            chart_buffer = BytesIO()
            fig.savefig(chart_buffer, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            chart_buffer.seek(0)
            story.extend([Paragraph("Τάση πωλήσεων", styles["GreekHeading"]),
                          Image(chart_buffer, width=165*mm, height=75*mm)])
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Η αναφορά περιγράφει τα δεδομένα που παρασχέθηκαν. Οι προτάσεις αποτελούν ενδείξεις για περαιτέρω διερεύνηση και όχι αυτόματες επιχειρηματικές αποφάσεις.", styles["GreekBody"]))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


uploaded = st.file_uploader("Επιλογή αρχείου", type=["csv", "xlsx", "xls"])
if not uploaded:
    st.info("Ξεκίνησε ανεβάζοντας ένα αρχείο. Για πλήρη ανάλυση, χρησιμοποίησε στήλες προϊόντος, πωλήσεων, ποσότητας ή ημερομηνίας.")
    st.stop()

try:
    df = read_upload(uploaded)
except Exception as exc:
    st.error(f"Δεν ήταν δυνατή η ανάγνωση του αρχείου: {exc}")
    st.stop()

if df.empty or len(df.columns) == 0:
    st.error("Το αρχείο δεν περιέχει δεδομένα.")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]
df = df.dropna(how="all").copy()
if df.empty:
    st.error("Το αρχείο δεν περιέχει γραμμές με δεδομένα.")
    st.stop()
cols = list(df.columns)
numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
none_option = "— Χωρίς επιλογή —"

st.subheader("1. Προεπισκόπηση δεδομένων")
st.dataframe(df.head(10), use_container_width=True)
st.caption(f"{len(df):,} γραμμές · {len(cols)} στήλες")

st.subheader("2. Αντιστοίχιση στηλών")
product_guess = guess_column(cols, ["product", "προϊόν", "προιον", "item", "είδος"])
sales_guess = guess_column(cols, ["sales", "revenue", "πωλή", "έσοδ", "τζίρ", "amount", "σύνολο"])
quantity_guess = guess_column(cols, ["quantity", "qty", "ποσότ", "τεμάχ", "units"])
date_guess = guess_column(cols, ["date", "ημερομην", "μην", "χρόνο"])

def selector(label, options, default, key):
    items = [none_option] + options
    index = items.index(default) if default in items else 0
    choice = st.selectbox(label, items, index=index, key=key)
    return None if choice == none_option else choice

product_col = selector("Στήλη προϊόντος", cols, product_guess, "product")
sales_col = selector("Στήλη πωλήσεων/εσόδων", numeric_cols, sales_guess if sales_guess in numeric_cols else None, "sales")
quantity_col = selector("Στήλη ποσότητας", numeric_cols, quantity_guess if quantity_guess in numeric_cols else None, "quantity")
date_col = selector("Στήλη ημερομηνίας", cols, date_guess, "date")

if not product_col:
    st.warning("Επίλεξε μια στήλη προϊόντος για ανάλυση ανά προϊόν.")
    st.stop()

metric_col = sales_col or quantity_col
if metric_col:
    values = pd.to_numeric(df[metric_col], errors="coerce")
    valid = df.assign(_metric=values).dropna(subset=["_metric"])
    grouped = valid.groupby(product_col, dropna=False)["_metric"].sum().sort_values(ascending=False).rename("value").reset_index()
    grouped.columns = ["product", "value"]
else:
    grouped = df[product_col].fillna("(κενό)").value_counts().rename_axis("product").reset_index(name="value")

total_sales = pd.to_numeric(df[sales_col], errors="coerce").sum() if sales_col else None
total_quantity = pd.to_numeric(df[quantity_col], errors="coerce").sum() if quantity_col else None
summary = {"Πλήθος εγγραφών": f"{len(df):,}", "Μοναδικά προϊόντα": f"{df[product_col].nunique(dropna=True):,}"}
if total_sales is not None:
    summary["Συνολικές πωλήσεις/έσοδα"] = euro(total_sales)
if total_quantity is not None:
    summary["Συνολική ποσότητα"] = f"{total_quantity:,.2f}"
if sales_col:
    summary["Μέση τιμή πώλησης ανά εγγραφή"] = euro(pd.to_numeric(df[sales_col], errors="coerce").mean())

advice = []
if len(grouped):
    leader = grouped.iloc[0]
    leader_value = euro(leader["value"]) if sales_col else f"{leader['value']:,.2f}"
    advice.append(f"Το προϊόν με τη μεγαλύτερη συνολική επίδοση είναι το «{leader['product']}» ({leader_value}). Εξέτασε αν η διαθεσιμότητα και η προβολή του ανταποκρίνονται στη ζήτησή του.")
    if len(grouped) >= 2 and grouped["value"].sum() != 0:
        share = grouped.iloc[0]["value"] / grouped["value"].sum() * 100
        advice.append(f"Το κορυφαίο προϊόν αντιστοιχεί περίπου στο {share:.1f}% της συνολικής αξίας της επιλεγμένης μέτρησης. Παρακολούθησε τη συγκέντρωση πωλήσεων σε λίγα προϊόντα.")
    if len(grouped) >= 3:
        tail = grouped.tail(max(1, len(grouped)//4))
        advice.append(f"Τα προϊόντα με χαμηλότερη επίδοση είναι: {', '.join(map(str, tail['product'].head(4)))}. Έλεγξε περιθώριο κέρδους, απόθεμα και εποχικότητα πριν αποφασίσεις αλλαγές.")
if date_col:
    parsed = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if len(parsed):
        advice.append(f"Η περίοδος που καλύπτουν τα δεδομένα είναι από {parsed.min().strftime('%d/%m/%Y')} έως {parsed.max().strftime('%d/%m/%Y')}. Σύγκρινε αντίστοιχες περιόδους για να εντοπίσεις τάσεις με μεγαλύτερη αξιοπιστία.")
if not sales_col:
    advice.append("Δεν επιλέχθηκε στήλη πωλήσεων/εσόδων. Η σύγκριση βασίζεται στην ποσότητα ή στο πλήθος εγγραφών και δεν αποτυπώνει κερδοφορία.")

st.subheader("3. Αποτελέσματα")
metric_labels = list(summary.items())
cards = st.columns(min(4, max(1, len(metric_labels))))
for i, (label, value) in enumerate(metric_labels):
    cards[i % len(cards)].metric(label, value)

left, right = st.columns(2)
top = grouped.head(10)
value_label = sales_col or quantity_col or "Πλήθος εγγραφών"
with left:
    st.plotly_chart(px.bar(top.sort_values("value"), x="value", y="product", orientation="h",
                           title=f"Κορυφαία προϊόντα βάσει {value_label}", labels={"value": value_label, "product": "Προϊόν"},
                           color_discrete_sequence=["#2385a5"]), use_container_width=True)
with right:
    pie_data = top.head(8)
    pie_data = pie_data[pie_data["value"] >= 0]
    if not pie_data.empty and pie_data["value"].sum() > 0:
        st.plotly_chart(px.pie(pie_data, names="product", values="value", title="Μερίδιο κορυφαίων προϊόντων",
                               hole=.25), use_container_width=True)
    else:
        st.info("Δεν υπάρχουν τιμές κατάλληλες για γράφημα μεριδίων.")

if date_col and sales_col:
    trend_df = df[[date_col, sales_col]].copy()
    trend_df[date_col] = pd.to_datetime(trend_df[date_col], errors="coerce")
    trend_df[sales_col] = pd.to_numeric(trend_df[sales_col], errors="coerce")
    trend_df = trend_df.dropna().set_index(date_col).resample("MS")[sales_col].sum().reset_index()
    if not trend_df.empty:
        st.plotly_chart(px.line(trend_df, x=date_col, y=sales_col, markers=True, title="Πωλήσεις ανά μήνα"), use_container_width=True)

st.subheader("4. Συμβουλές υποστήριξης αποφάσεων")
for item in advice:
    st.markdown(f"- {item}")
st.caption("Οι προτάσεις είναι ενδείξεις για περαιτέρω διερεύνηση και δεν αντικαθιστούν την επιχειρηματική κρίση.")

pdf_bytes = make_pdf(df, product_col, sales_col, quantity_col, date_col, summary, advice, grouped)
st.download_button(" Λήψη αναφοράς PDF", data=pdf_bytes,
                   file_name=f"anafora_epixeirimatikon_dedomenon_{datetime.now().strftime('%Y%m%d')}.pdf",
                   mime="application/pdf", type="primary")
