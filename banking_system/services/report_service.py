"""Statement and report generator (PDF, CSV, TXT)."""

import csv
from datetime import datetime
from pathlib import Path
from typing import List
from config import Config
from models.account import Account
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ReportService:
    @staticmethod
    def export_csv(account: Account) -> Path:
        out_path = Config.EXPORTS_DIR / f"Statement_{account.account_number}_{int(datetime.utcnow().timestamp())}.csv"
        records = [
            {
                "Transaction ID": tx.id,
                "Timestamp": tx.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Type": tx.type,
                "Amount ($)": float(tx.amount),
                "Balance After ($)": float(tx.balance_after),
                "Description": tx.description,
            }
            for tx in account.transactions
        ]
        df = pd.DataFrame(records)
        df.to_csv(out_path, index=False)
        return out_path

    @staticmethod
    def export_txt(account: Account) -> Path:
        out_path = Config.EXPORTS_DIR / f"Statement_{account.account_number}_{int(datetime.utcnow().timestamp())}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("========================================================================================\n")
            f.write("                             APEX DIGITAL BANK - STATEMENT                             \n")
            f.write("========================================================================================\n")
            f.write(f"Account Number : {account.account_number}\n")
            f.write(f"Account Holder : {account.owner.full_name}\n")
            f.write(f"Account Type   : {account.account_type}\n")
            f.write(f"Current Balance: ${float(account.balance):,.2f}\n")
            f.write(f"Generated On   : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
            f.write("----------------------------------------------------------------------------------------\n")
            f.write(f"{'Date/Time':<20} | {'Type':<18} | {'Amount':<12} | {'Balance':<12} | {'Details'}\n")
            f.write("----------------------------------------------------------------------------------------\n")
            for tx in account.transactions:
                f.write(
                    f"{tx.timestamp.strftime('%Y-%m-%d %H:%M:%S'):<20} | "
                    f"{tx.type:<18} | "
                    f"${float(tx.amount):<11,.2f} | "
                    f"${float(tx.balance_after):<11,.2f} | "
                    f"{tx.description}\n"
                )
            f.write("========================================================================================\n")
        return out_path

    @staticmethod
    def export_pdf(account: Account) -> Path:
        out_path = Config.EXPORTS_DIR / f"Statement_{account.account_number}_{int(datetime.utcnow().timestamp())}.pdf"
        doc = SimpleDocTemplate(str(out_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6,
        )
        meta_style = ParagraphStyle(
            "DocMeta",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#475569"),
            spaceAfter=4,
        )

        story.append(Paragraph("<b>APEX DIGITAL COMMERCIAL BANK</b>", title_style))
        story.append(Paragraph("Official Transaction Record & Account Statement", meta_style))
        story.append(Spacer(1, 14))

        meta_data = [
            [
                f"Account Holder: {account.owner.full_name}",
                f"Account Type: {account.account_type}",
            ],
            [
                f"Account Number: {account.account_number}",
                f"Current Balance: ${float(account.balance):,.2f}",
            ],
            [
                f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                f"Account Status: {account.status}",
            ],
        ]
        meta_table = Table(meta_data, colWidths=[270, 270])
        meta_table.setStyle(
            TableStyle(
                [
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 16))

        table_data = [["Timestamp", "Type", "Amount", "Balance After", "Description"]]
        for tx in account.transactions:
            table_data.append(
                [
                    tx.timestamp.strftime("%Y-%m-%d %H:%M"),
                    tx.type,
                    f"${float(tx.amount):,.2f}",
                    f"${float(tx.balance_after):,.2f}",
                    tx.description[:32] + ("..." if len(tx.description) > 32 else ""),
                ]
            )

        t = Table(table_data, colWidths=[100, 95, 80, 85, 180])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f8fafc")],
                    ),
                ]
            )
        )
        story.append(t)
        doc.build(story)
        return out_path