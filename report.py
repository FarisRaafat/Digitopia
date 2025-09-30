from io import BytesIO
from typing import Optional

from fpdf import FPDF
import matplotlib.pyplot as plt
import pandas as pd


def _fig_to_png_bytes(fig) -> bytes:
    bio = BytesIO()
    fig.savefig(bio, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    return bio.getvalue()


def build_pdf_report(df: pd.DataFrame, title: str = "Security Report") -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cover
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Arial", size=12)
    pdf.ln(5)

    total_findings = 0 if df is None or df.empty else int(df["rule"].count())
    severities = (df["severity"].str.upper().value_counts() if df is not None and not df.empty else pd.Series(dtype=int))

    pdf.multi_cell(0, 8, f"Total findings: {total_findings}")
    if not severities.empty:
        sev_str = ", ".join(f"{k}: {int(v)}" for k, v in severities.items())
        pdf.multi_cell(0, 8, f"By severity: {sev_str}")

    # Severity chart
    if not severities.empty:
        fig, ax = plt.subplots(figsize=(5, 3))
        severities.sort_index().plot(kind="bar", ax=ax, color="#ef4444")
        ax.set_title("Findings by Severity")
        ax.set_xlabel("Severity")
        ax.set_ylabel("Count")
        img_bytes = _fig_to_png_bytes(fig)
        img_stream = BytesIO(img_bytes)
        pdf.ln(5)
        pdf.image(img_stream, w=170)

    # Findings table (first 40 rows)
    if df is not None and not df.empty:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Findings (first 40)", ln=True)
        pdf.set_font("Arial", size=9)
        headers = ["file", "line", "rule", "severity"]
        data = df[headers].head(40).fillna("")
        for _, row in data.iterrows():
            line = f"{row['file']}:{row['line']} | {row['rule']} | {row['severity']}"
            pdf.multi_cell(0, 6, line)

    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


