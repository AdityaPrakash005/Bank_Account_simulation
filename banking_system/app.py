"""Master production-grade entrypoint for the Professional Digital Banking GUI."""

import datetime
from decimal import Decimal
import os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from database.connection import get_db, init_db
from database.seed import seed_data
from gui.theme import BankTheme
from models.account import Account, AccountStatus, AccountType
from models.audit import AuditLog
from models.transaction import Transaction
from models.user import User, UserRole
from security.mfa import MFAService
from security.session import SessionManager
from services.auth_service import AuthService
from services.banking_service import BankingService
from services.interest_service import InterestService
from services.report_service import ReportService

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class BankingApplication(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Apex Digital Commercial Bank - Core System")
        self.geometry("1240x820")
        self.minsize(1050, 720)

        # Initialize storage
        init_db()
        seed_data()

        # Session monitoring state
        self.active_account_id = None
        self.after(30000, self._session_idle_watchdog)

        self._render_login_view()

    def _clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _session_idle_watchdog(self):
        session = SessionManager.get_session()
        if session is None and hasattr(self, "sidebar"):
            messagebox.showwarning("Session Timeout", "Your session has expired due to inactivity.")
            self._render_login_view()
        else:
            self.after(30000, self._session_idle_watchdog)

    # ==========================================
    # LOGIN & MFA VIEW
    # ==========================================
    def _render_login_view(self):
        self._clear_window()
        SessionManager.destroy_session()

        container = ctk.CTkFrame(self, fg_color=BankTheme.BACKGROUND_DARK)
        container.pack(fill="both", expand=True)

        card = ctk.CTkFrame(
            container,
            fg_color=BankTheme.CARD_DARK,
            corner_radius=16,
            width=420,
            border_width=1,
            border_color=BankTheme.BORDER_COLOR,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card,
            text="APEX DIGITAL BANK",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=BankTheme.PRIMARY,
        ).pack(pady=(35, 4))
        ctk.CTkLabel(
            card,
            text="Core Banking Online Portal",
            font=ctk.CTkFont(size=13),
            text_color=BankTheme.TEXT_MUTED,
        ).pack(pady=(0, 25))

        self.login_user_entry = ctk.CTkEntry(
            card,
            placeholder_text="Username",
            width=320,
            height=42,
            font=ctk.CTkFont(size=14),
        )
        self.login_user_entry.pack(pady=10)
        self.login_user_entry.insert(0, "sarah")  # Seed preset for convenience

        self.login_pin_entry = ctk.CTkEntry(
            card,
            placeholder_text="Security PIN",
            show="*",
            width=320,
            height=42,
            font=ctk.CTkFont(size=14),
        )
        self.login_pin_entry.pack(pady=10)
        self.login_pin_entry.insert(0, "1234")

        self.login_err_lbl = ctk.CTkLabel(
            card,
            text="",
            text_color=BankTheme.ACCENT_RED,
            font=ctk.CTkFont(size=12),
        )
        self.login_err_lbl.pack(pady=4)

        btn_login = ctk.CTkButton(
            card,
            text="Sign In Securely",
            command=self._handle_login_step,
            width=320,
            height=44,
            fg_color=BankTheme.PRIMARY,
            hover_color=BankTheme.PRIMARY_HOVER,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        btn_login.pack(pady=15)

        ctk.CTkLabel(
            card,
            text="Demo Accounts:\n• Customer: sarah / PIN: 1234\n• Customer: johndoe / PIN: 4321\n• Admin: admin / PIN: 9999",
            font=ctk.CTkFont(size=11),
            text_color=BankTheme.TEXT_MUTED,
            justify="left",
        ).pack(pady=(10, 25))

    def _handle_login_step(self):
        username = self.login_user_entry.get().strip()
        pin = self.login_pin_entry.get().strip()

        ok, msg, session = AuthService.authenticate(username, pin)
        if not ok:
            self.login_err_lbl.configure(text=msg)
            return

        # Trigger simulated MFA OTP Challenge
        otp = MFAService.generate_otp(session.user_id)
        self._prompt_mfa_dialog(session, otp)

    def _prompt_mfa_dialog(self, session, simulated_otp: str):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Two-Factor Authentication")
        dialog.geometry("420x300")
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Enter MFA Code",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 5))
        ctk.CTkLabel(
            dialog,
            text=f"[Simulated SMS/Token Received]: {simulated_otp}",
            text_color=BankTheme.PRIMARY,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=5)

        otp_entry = ctk.CTkEntry(dialog, placeholder_text="6-digit OTP", width=220, height=40)
        otp_entry.pack(pady=15)
        otp_entry.insert(0, simulated_otp)

        err_lbl = ctk.CTkLabel(dialog, text="", text_color=BankTheme.ACCENT_RED)
        err_lbl.pack()

        def verify():
            if MFAService.verify_otp(session.user_id, otp_entry.get()):
                dialog.destroy()
                self._render_main_layout()
            else:
                err_lbl.configure(text="Invalid OTP entered.")

        ctk.CTkButton(
            dialog,
            text="Verify & Access",
            fg_color=BankTheme.PRIMARY,
            command=verify,
            width=220,
            height=40,
        ).pack(pady=10)

    # ==========================================
    # PRIMARY NAVIGATION & SHELL
    # ==========================================
    def _render_main_layout(self):
        self._clear_window()
        session = SessionManager.get_session()
        if not session:
            self._render_login_view()
            return

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0,
            fg_color=BankTheme.CARD_DARK,
            border_width=1,
            border_color=BankTheme.BORDER_COLOR,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            self.sidebar,
            text="APEX BANK",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=BankTheme.PRIMARY,
        ).pack(pady=(25, 5))
        ctk.CTkLabel(
            self.sidebar,
            text=f"User: {session.username} ({session.role})",
            font=ctk.CTkFont(size=12),
            text_color=BankTheme.TEXT_MUTED,
        ).pack(pady=(0, 20))

        nav_btns = [
            ("Dashboard", self._render_dashboard),
            ("Accounts", self._render_accounts_view),
            ("Transfer Funds", self._render_transfer_view),
            ("Transactions", self._render_transactions_view),
            ("Settings & PIN", self._render_settings_view),
        ]
        if session.role == UserRole.ADMIN.value:
            nav_btns.append(("Admin Panel", self._render_admin_view))

        for label, cmd in nav_btns:
            ctk.CTkButton(
                self.sidebar,
                text=label,
                command=cmd,
                height=42,
                fg_color="transparent",
                hover_color=BankTheme.BORDER_COLOR,
                anchor="w",
                font=ctk.CTkFont(size=14),
            ).pack(fill="x", padx=15, pady=4)

        ctk.CTkButton(
            self.sidebar,
            text="Sign Out",
            command=self._render_login_view,
            fg_color=BankTheme.ACCENT_RED,
            hover_color="#dc2626",
            height=40,
        ).pack(side="bottom", fill="x", padx=20, pady=25)

        # Content Main Panel
        self.main_content = ctk.CTkFrame(self, fg_color=BankTheme.BACKGROUND_DARK)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self._render_dashboard()

    # ==========================================
    # DASHBOARD
    # ==========================================
    def _render_dashboard(self):
        for w in self.main_content.winfo_children():
            w.destroy()

        session = SessionManager.get_session()
        ctk.CTkLabel(
            self.main_content,
            text=f"Welcome, {session.full_name}",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", pady=(5, 20))

        with get_db() as db:
            accounts = db.query(Account).filter(Account.user_id == session.user_id, Account.is_deleted == False).all()

            # Account Portfolio Cards View
            cards_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
            cards_frame.pack(fill="x", pady=10)

            if not accounts:
                ctk.CTkLabel(cards_frame, text="No accounts open. Create one in the Accounts tab.").pack()

            for acc in accounts:
                card = ctk.CTkFrame(
                    cards_frame,
                    fg_color=BankTheme.CARD_DARK,
                    corner_radius=12,
                    border_width=1,
                    border_color=BankTheme.BORDER_COLOR,
                    width=290,
                    height=160,
                )
                card.pack(side="left", padx=10, pady=5)
                card.pack_propagate(False)

                ctk.CTkLabel(
                    card,
                    text=f"{acc.account_type.upper()}",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=BankTheme.PRIMARY,
                ).pack(anchor="w", padx=15, pady=(15, 2))
                ctk.CTkLabel(
                    card,
                    text=f"#{acc.account_number}",
                    font=ctk.CTkFont(size=13),
                    text_color=BankTheme.TEXT_MUTED,
                ).pack(anchor="w", padx=15)
                ctk.CTkLabel(
                    card,
                    text=f"${float(acc.balance):,.2f}",
                    font=ctk.CTkFont(size=22, weight="bold"),
                ).pack(anchor="w", padx=15, pady=(10, 2))
                ctk.CTkLabel(
                    card,
                    text=f"Available: ${acc.available_balance:,.2f}",
                    font=ctk.CTkFont(size=11),
                    text_color=BankTheme.TEXT_MUTED,
                ).pack(anchor="w", padx=15)

            # Quick Action Toolbar
            action_bar = ctk.CTkFrame(
                self.main_content,
                fg_color=BankTheme.CARD_DARK,
                corner_radius=12,
                border_width=1,
                border_color=BankTheme.BORDER_COLOR,
            )
            action_bar.pack(fill="x", pady=20, padx=5)

            ctk.CTkLabel(
                action_bar,
                text="Quick Operations:",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(side="left", padx=20, pady=15)
            ctk.CTkButton(
                action_bar,
                text="Deposit",
                command=self._dialog_deposit,
                fg_color=BankTheme.PRIMARY,
                width=110,
            ).pack(side="left", padx=8)
            ctk.CTkButton(
                action_bar,
                text="Withdraw",
                command=self._dialog_withdraw,
                fg_color=BankTheme.PRIMARY,
                width=110,
            ).pack(side="left", padx=8)
            ctk.CTkButton(
                action_bar,
                text="Apply Interest",
                command=self._action_apply_interest,
                fg_color=BankTheme.SECONDARY,
                border_width=1,
                border_color=BankTheme.PRIMARY,
                width=130,
            ).pack(side="left", padx=8)

            # Recent 5 Transactions
            ctk.CTkLabel(
                self.main_content,
                text="Recent Account Transactions",
                font=ctk.CTkFont(size=18, weight="bold"),
            ).pack(anchor="w", pady=(15, 10))

            acc_ids = [a.id for a in accounts]
            recent_txs = (
                db.query(Transaction)
                .filter(Transaction.account_id.in_(acc_ids))
                .order_by(Transaction.timestamp.desc())
                .limit(5)
                .all()
            )

            tx_table = ctk.CTkScrollableFrame(self.main_content, fg_color=BankTheme.CARD_DARK, height=220)
            tx_table.pack(fill="x", padx=5)

            for tx in recent_txs:
                row = ctk.CTkFrame(tx_table, fg_color="transparent")
                row.pack(fill="x", pady=4, padx=10)
                ctk.CTkLabel(
                    row,
                    text=tx.timestamp.strftime("%Y-%m-%d %H:%M"),
                    width=140,
                    anchor="w",
                    text_color=BankTheme.TEXT_MUTED,
                ).pack(side="left")
                ctk.CTkLabel(
                    row,
                    text=tx.type,
                    width=150,
                    anchor="w",
                    font=ctk.CTkFont(weight="bold"),
                ).pack(side="left")
                ctk.CTkLabel(
                    row,
                    text=f"${float(tx.amount):,.2f}",
                    width=110,
                    anchor="w",
                    text_color=BankTheme.ACCENT_GREEN
                    if "Deposit" in tx.type or "Received" in tx.type or "Interest" in tx.type
                    else BankTheme.ACCENT_RED,
                ).pack(side="left")
                ctk.CTkLabel(row, text=tx.description, anchor="w").pack(side="left", fill="x", expand=True)

    # ==========================================
    # ACCOUNTS MANAGEMENT VIEW
    # ==========================================
    def _render_accounts_view(self):
        for w in self.main_content.winfo_children():
            w.destroy()

        session = SessionManager.get_session()
        top = ctk.CTkFrame(self.main_content, fg_color="transparent")
        top.pack(fill="x", pady=(5, 15))

        ctk.CTkLabel(
            top,
            text="Account Management",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            top,
            text="+ Open New Account",
            fg_color=BankTheme.PRIMARY,
            command=self._dialog_open_account,
        ).pack(side="right")

        with get_db() as db:
            accounts = db.query(Account).filter(Account.user_id == session.user_id, Account.is_deleted == False).all()
            container = ctk.CTkScrollableFrame(self.main_content, fg_color=BankTheme.CARD_DARK, height=520)
            container.pack(fill="both", expand=True)

            for acc in accounts:
                item = ctk.CTkFrame(
                    container,
                    fg_color=BankTheme.BACKGROUND_DARK,
                    corner_radius=8,
                    border_width=1,
                    border_color=BankTheme.BORDER_COLOR,
                )
                item.pack(fill="x", padx=10, pady=8)

                ctk.CTkLabel(
                    item,
                    text=f"#{acc.account_number} ({acc.account_type})",
                    font=ctk.CTkFont(size=15, weight="bold"),
                ).pack(side="left", padx=15, pady=15)
                ctk.CTkLabel(
                    item,
                    text=f"Status: {acc.status}",
                    text_color=BankTheme.ACCENT_GREEN if acc.status == "Active" else BankTheme.ACCENT_RED,
                ).pack(side="left", padx=15)
                ctk.CTkLabel(
                    item,
                    text=f"Balance: ${float(acc.balance):,.2f}",
                    font=ctk.CTkFont(size=14, weight="bold"),
                ).pack(side="left", padx=15)

                btn_pdf = ctk.CTkButton(
                    item,
                    text="Statement (PDF)",
                    width=120,
                    fg_color=BankTheme.SECONDARY,
                    border_width=1,
                    border_color=BankTheme.PRIMARY,
                    command=lambda a=acc: self._export_statement(a, "pdf"),
                )
                btn_pdf.pack(side="right", padx=10)
                btn_csv = ctk.CTkButton(
                    item,
                    text="CSV",
                    width=60,
                    fg_color=BankTheme.SECONDARY,
                    border_width=1,
                    border_color=BankTheme.PRIMARY,
                    command=lambda a=acc: self._export_statement(a, "csv"),
                )
                btn_csv.pack(side="right", padx=5)

    def _export_statement(self, account: Account, fmt: str):
        try:
            if fmt == "pdf":
                path = ReportService.export_pdf(account)
            else:
                path = ReportService.export_csv(account)
            messagebox.showinfo("Export Success", f"Statement generated:\n{path.resolve()}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not create statement: {e}")

    # ==========================================
    # FUND TRANSFER VIEW
    # ==========================================
    def _render_transfer_view(self):
        for w in self.main_content.winfo_children():
            w.destroy()

        session = SessionManager.get_session()
        ctk.CTkLabel(
            self.main_content,
            text="Transfer Funds",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(5, 20))

        card = ctk.CTkFrame(
            self.main_content,
            fg_color=BankTheme.CARD_DARK,
            corner_radius=12,
            border_width=1,
            border_color=BankTheme.BORDER_COLOR,
            width=540,
        )
        card.pack(anchor="w", pady=10)

        with get_db() as db:
            accounts = db.query(Account).filter(Account.user_id == session.user_id, Account.is_deleted == False).all()
            acc_options = {f"#{a.account_number} (${float(a.balance):,.2f})": a.id for a in accounts}

            ctk.CTkLabel(card, text="Origin Account:", font=ctk.CTkFont(weight="bold")).pack(
                anchor="w", padx=25, pady=(20, 5)
            )
            src_dropdown = ctk.CTkOptionMenu(card, values=list(acc_options.keys()), width=420)
            src_dropdown.pack(padx=25, pady=5)

            ctk.CTkLabel(
                card,
                text="Destination Account Number (10 digits):",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", padx=25, pady=(15, 5))
            target_entry = ctk.CTkEntry(card, placeholder_text="e.g. 2002002001", width=420)
            target_entry.pack(padx=25, pady=5)

            ctk.CTkLabel(card, text="Transfer Amount ($):", font=ctk.CTkFont(weight="bold")).pack(
                anchor="w", padx=25, pady=(15, 5)
            )
            amount_entry = ctk.CTkEntry(card, placeholder_text="0.00", width=420)
            amount_entry.pack(padx=25, pady=5)

            def execute_transfer():
                if not acc_options:
                    messagebox.showerror("Error", "No source accounts available.")
                    return
                src_id = acc_options[src_dropdown.get()]
                target_num = target_entry.get().strip()
                try:
                    val = float(amount_entry.get().strip())
                except ValueError:
                    messagebox.showerror("Invalid Amount", "Please input a valid numeric amount.")
                    return

                # Force re-authentication for transfers above threshold
                if val >= 1000.00:
                    pin = ctk.CTkInputDialog(
                        title="High-Value Authorization",
                        text=f"Transfer of ${val:,.2f} exceeds threshold.\nEnter PIN to authorize:",
                    ).get_input()
                    if not pin:
                        return
                    with get_db() as udb:
                        u = udb.query(User).filter(User.id == session.user_id).first()
                        from security.crypto import CryptoManager

                        if not CryptoManager.verify_pin(pin, u.pin_hash, u.pin_salt):
                            messagebox.showerror("Auth Failed", "Invalid PIN authorization.")
                            return

                ok, msg = BankingService.transfer(src_id, target_num, val, session.username)
                if ok:
                    messagebox.showinfo("Transfer Approved", msg)
                    self._render_transfer_view()
                else:
                    messagebox.showerror("Transfer Declined", msg)

            ctk.CTkButton(
                card,
                text="Execute Transfer",
                command=execute_transfer,
                fg_color=BankTheme.PRIMARY,
                width=420,
                height=42,
            ).pack(padx=25, pady=(25, 30))

    # ==========================================
    # TRANSACTIONS VIEW
    # ==========================================
    def _render_transactions_view(self):
        for w in self.main_content.winfo_children():
            w.destroy()

        session = SessionManager.get_session()
        ctk.CTkLabel(
            self.main_content,
            text="Ledger Transactions",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(5, 15))

        with get_db() as db:
            accounts = db.query(Account).filter(Account.user_id == session.user_id).all()
            acc_ids = [a.id for a in accounts]
            txs = (
                db.query(Transaction)
                .filter(Transaction.account_id.in_(acc_ids))
                .order_by(Transaction.timestamp.desc())
                .all()
            )

            container = ctk.CTkScrollableFrame(self.main_content, fg_color=BankTheme.CARD_DARK, height=560)
            container.pack(fill="both", expand=True)

            header = ctk.CTkFrame(container, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(
                header,
                text="Timestamp",
                width=160,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                header,
                text="Type",
                width=150,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                header,
                text="Amount",
                width=110,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                header,
                text="Balance After",
                width=120,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                header,
                text="Description",
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left", fill="x", expand=True)

            for tx in txs:
                row = ctk.CTkFrame(container, fg_color=BankTheme.BACKGROUND_DARK, corner_radius=6)
                row.pack(fill="x", padx=5, pady=3)
                ctk.CTkLabel(
                    row,
                    text=tx.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    width=160,
                    anchor="w",
                    text_color=BankTheme.TEXT_MUTED,
                ).pack(side="left", padx=5)
                ctk.CTkLabel(row, text=tx.type, width=150, anchor="w").pack(side="left")
                ctk.CTkLabel(
                    row,
                    text=f"${float(tx.amount):,.2f}",
                    width=110,
                    anchor="w",
                    text_color=BankTheme.ACCENT_GREEN
                    if "Deposit" in tx.type or "Received" in tx.type or "Interest" in tx.type
                    else BankTheme.ACCENT_RED,
                ).pack(side="left")
                ctk.CTkLabel(
                    row,
                    text=f"${float(tx.balance_after):,.2f}",
                    width=120,
                    anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(row, text=tx.description, anchor="w").pack(side="left", fill="x", expand=True, padx=5)

    # ==========================================
    # SETTINGS VIEW
    # ==========================================
    def _render_settings_view(self):
        for w in self.main_content.winfo_children():
            w.destroy()

        session = SessionManager.get_session()
        ctk.CTkLabel(
            self.main_content,
            text="Security & Settings",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(5, 20))

        card = ctk.CTkFrame(
            self.main_content,
            fg_color=BankTheme.CARD_DARK,
            corner_radius=12,
            border_width=1,
            border_color=BankTheme.BORDER_COLOR,
            width=460,
        )
        card.pack(anchor="w", pady=10)

        ctk.CTkLabel(
            card,
            text="Rotate Security PIN",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=25, pady=(20, 15))

        old_pin_entry = ctk.CTkEntry(card, placeholder_text="Current PIN", show="*", width=380)
        old_pin_entry.pack(padx=25, pady=8)

        new_pin_entry = ctk.CTkEntry(card, placeholder_text="New PIN (min 4 digits)", show="*", width=380)
        new_pin_entry.pack(padx=25, pady=8)

        def submit_pin_change():
            ok, msg = AuthService.change_pin(session.user_id, old_pin_entry.get(), new_pin_entry.get())
            if ok:
                messagebox.showinfo("Security", msg)
                old_pin_entry.delete(0, tk.END)
                new_pin_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", msg)

        ctk.CTkButton(
            card,
            text="Update PIN",
            command=submit_pin_change,
            fg_color=BankTheme.PRIMARY,
            width=380,
            height=40,
        ).pack(padx=25, pady=(20, 25))

    # ==========================================
    # ADMIN PANEL VIEW
    # ==========================================
    def _render_admin_view(self):
        for w in self.main_content.winfo_children():
            w.destroy()

        session = SessionManager.get_session()
        if session.role != UserRole.ADMIN.value:
            ctk.CTkLabel(self.main_content, text="Access Denied").pack()
            return

        ctk.CTkLabel(
            self.main_content,
            text="Central Administrative Operations",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(5, 15))

        # Admin Actions
        bar = ctk.CTkFrame(self.main_content, fg_color=BankTheme.CARD_DARK, corner_radius=10)
        bar.pack(fill="x", pady=10, padx=5)

        def run_batch_interest():
            count = InterestService.apply_batch_interest(session.username)
            messagebox.showinfo("Complete", f"Calculated and posted interest across {count} active accounts.")
            self._render_admin_view()

        ctk.CTkButton(
            bar,
            text="Run Systemwide Interest Calculation",
            command=run_batch_interest,
            fg_color=BankTheme.PRIMARY,
        ).pack(side="left", padx=15, pady=15)

        # Audit Logs View
        ctk.CTkLabel(
            self.main_content,
            text="Security Audit Log Trail",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", pady=(15, 10))

        with get_db() as db:
            logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(15).all()
            log_frame = ctk.CTkScrollableFrame(self.main_content, fg_color=BankTheme.CARD_DARK, height=420)
            log_frame.pack(fill="both", expand=True)

            for log in logs:
                r = ctk.CTkFrame(log_frame, fg_color=BankTheme.BACKGROUND_DARK)
                r.pack(fill="x", pady=3, padx=5)
                ctk.CTkLabel(
                    r,
                    text=log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    width=150,
                    text_color=BankTheme.TEXT_MUTED,
                ).pack(side="left", padx=5)
                ctk.CTkLabel(
                    r,
                    text=log.actor_username,
                    width=100,
                    font=ctk.CTkFont(weight="bold"),
                ).pack(side="left")
                ctk.CTkLabel(
                    r,
                    text=log.action,
                    width=160,
                    text_color=BankTheme.PRIMARY,
                ).pack(side="left")
                ctk.CTkLabel(r, text=log.details).pack(side="left", fill="x", expand=True)

    # ==========================================
    # MODAL DIALOGS
    # ==========================================
    def _dialog_deposit(self):
        session = SessionManager.get_session()
        with get_db() as db:
            accounts = db.query(Account).filter(Account.user_id == session.user_id).all()
            if not accounts:
                return

            d = ctk.CTkInputDialog(
                title="Deposit Cash",
                text=f"Enter deposit sum for Account #{accounts[0].account_number}:",
            )
            val = d.get_input()
            if val:
                try:
                    ok, msg = BankingService.deposit(accounts[0].id, float(val), session.username)
                    if ok:
                        messagebox.showinfo("Success", msg)
                        self._render_dashboard()
                    else:
                        messagebox.showerror("Error", msg)
                except ValueError:
                    messagebox.showerror("Error", "Invalid numeric format.")

    def _dialog_withdraw(self):
        session = SessionManager.get_session()
        with get_db() as db:
            accounts = db.query(Account).filter(Account.user_id == session.user_id).all()
            if not accounts:
                return

            d = ctk.CTkInputDialog(
                title="Withdraw Cash",
                text=f"Enter withdrawal sum for Account #{accounts[0].account_number}:",
            )
            val = d.get_input()
            if val:
                try:
                    ok, msg = BankingService.withdraw(accounts[0].id, float(val), session.username)
                    if ok:
                        messagebox.showinfo("Success", msg)
                        self._render_dashboard()
                    else:
                        messagebox.showerror("Error", msg)
                except ValueError:
                    messagebox.showerror("Error", "Invalid numeric format.")

    def _action_apply_interest(self):
        session = SessionManager.get_session()
        with get_db() as db:
            accounts = db.query(Account).filter(Account.user_id == session.user_id).all()
            if not accounts:
                return
            ok, msg = InterestService.apply_account_interest(accounts[0].id, session.username)
            if ok:
                messagebox.showinfo("Interest Applied", msg)
                self._render_dashboard()
            else:
                messagebox.showwarning("Notice", msg)

    def _dialog_open_account(self):
        session = SessionManager.get_session()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Open New Account")
        dialog.geometry("380x320")
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Open Account Tier",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=15)

        type_var = ctk.StringVar(value=AccountType.SAVINGS.value)
        ctk.CTkOptionMenu(
            dialog,
            variable=type_var,
            values=[
                AccountType.SAVINGS.value,
                AccountType.CHECKING.value,
                AccountType.MONEY_MARKET.value,
            ],
            width=260,
        ).pack(pady=10)

        dep_entry = ctk.CTkEntry(dialog, placeholder_text="Initial Deposit ($)", width=260)
        dep_entry.pack(pady=10)
        dep_entry.insert(0, "100.00")

        def submit():
            try:
                amt = float(dep_entry.get().strip())
            except ValueError:
                amt = 0.0
            ok, msg, num = BankingService.create_account(session.user_id, type_var.get(), amt)
            if ok:
                messagebox.showinfo("Success", f"Account created: #{num}")
                dialog.destroy()
                self._render_accounts_view()
            else:
                messagebox.showerror("Error", msg)

        ctk.CTkButton(
            dialog,
            text="Confirm Opening",
            command=submit,
            fg_color=BankTheme.PRIMARY,
            width=260,
        ).pack(pady=20)


if __name__ == "__main__":
    app = BankingApplication()
    app.mainloop()