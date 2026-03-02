"""tkinter user interface."""

import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any
from pathlib import Path

from finance_dashboard.config import DEFAULT_COLUMNS, DB_FILE
from finance_dashboard import database
from finance_dashboard.fetcher import fetch_asset_stats
from finance_dashboard.parsing import parse_csv_file, parse_manual_input


class AssetViewerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Asset Statistics Viewer")
        self.geometry("1200x650")

        self.db_path = Path(DB_FILE)
        self.conn = database.connect(self.db_path)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.tab_fetch = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_fetch, text="Fetch")
        self.notebook.add(self.tab_history, text="History")

        self._build_fetch_tab()
        self._build_history_tab()
        self.refresh_history_list()

        self._is_fetching = False

    def _build_fetch_tab(self) -> None:
        top = ttk.Frame(self.tab_fetch, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Tickers (comma-separated):").grid(row=0, column=0, sticky="w")
        self.tickers_entry = ttk.Entry(top)
        self.tickers_entry.grid(row=0, column=1, sticky="ew", padx=8)

        self.btn_fetch_manual = ttk.Button(top, text="Fetch", command=self.on_fetch_manual)
        self.btn_fetch_manual.grid(row=0, column=2, padx=4)

        self.btn_load_csv = ttk.Button(top, text="Load CSV…", command=self.on_load_csv)
        self.btn_load_csv.grid(row=0, column=3, padx=4)

        top.columnconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self.tab_fetch, textvariable=self.status_var, padding=(10, 0)).pack(fill="x")

        self.fetch_table_frame, self.fetch_tree = self._make_table(self.tab_fetch)
        self.fetch_table_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_history_tab(self) -> None:
        container = ttk.Frame(self.tab_history, padding=10)
        container.pack(fill="both", expand=True)

        left = ttk.Frame(container)
        right = ttk.Frame(container)
        left.pack(side="left", fill="y", padx=(0, 10))
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Past queries:").pack(anchor="w")
        self.history_list = tk.Listbox(left, height=25, width=45)
        self.history_list.pack(fill="y", expand=False)
        self.history_list.bind("<<ListboxSelect>>", self.on_history_select)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(8, 0))

        self.btn_refresh_history = ttk.Button(btns, text="Refresh", command=self.refresh_history_list)
        self.btn_refresh_history.pack(side="left")
        ttk.Button(btns, text="Clear History", command=self.on_clear_history).pack(
            side="left", padx=6
        )

        self.history_status_var = tk.StringVar(value="Select a query to view stored results.")
        ttk.Label(right, textvariable=self.history_status_var).pack(anchor="w")

        self.history_table_frame, self.history_tree = self._make_table(right)
        self.history_table_frame.pack(fill="both", expand=True, pady=(8, 0))

        self._history_index_map: list[int] = []

    def _make_table(self, parent: tk.Widget) -> tuple[ttk.Frame, ttk.Treeview]:
        frame = ttk.Frame(parent)

        columns = tuple(DEFAULT_COLUMNS)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        tree["displaycolumns"] = columns

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        for c in columns:
            tree.heading(c, text=c)
            if c == "Error":
                tree.column(c, width=500, anchor="w")
            elif c == "Name":
                tree.column(c, width=220, anchor="w")
            else:
                tree.column(c, width=120, anchor="w")

        return frame, tree

    def set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.update_idletasks()

    def on_load_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Select CSV file", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            tickers = parse_csv_file(path)
            if not tickers:
                messagebox.showwarning("No tickers", "Could not find any tickers in the CSV.")
                return
            self.tickers_entry.delete(0, tk.END)
            self.tickers_entry.insert(0, ", ".join(tickers))
            self.start_fetch(tickers, source="csv", input_text=path)
        except Exception as e:
            messagebox.showerror("CSV Error", str(e))

    def on_fetch_manual(self) -> None:
        text = self.tickers_entry.get().strip()
        tickers = parse_manual_input(text)
        if not tickers:
            messagebox.showwarning("No tickers", "Please enter at least one ticker.")
            return
        self.start_fetch(tickers, source="manual", input_text=text)

    def start_fetch(self, tickers: list[str], source: str, input_text: str) -> None:
        self._is_fetching = True
        self.btn_fetch_manual.config(state="disabled")
        self.btn_load_csv.config(state="disabled")
        self.btn_refresh_history.config(state="disabled")
        self.set_status(f"Fetching {len(tickers)} assets…")

        def worker() -> None:
            try:
                start = time.time()
                stats = fetch_asset_stats(tickers)
                elapsed = time.time() - start

                conn = database.connect(self.db_path)
                try:
                    qid = database.insert_query(conn, source, input_text, tickers)
                    rows_for_db = [
                        (s.ticker, {k: v for k, v in s.row.items() if k != "Ticker"})
                        for s in stats
                    ]
                    database.insert_results(conn, qid, rows_for_db)
                finally:
                    conn.close()

                self.after(0, lambda: self._finish_fetch(stats, elapsed, qid))

            except Exception as e:
                self.after(0, lambda: self._fetch_failed(e))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_fetch(self, stats: list, elapsed: float, qid: int) -> None:
        self._is_fetching = False
        self._populate_tree(self.fetch_tree, [s.row for s in stats])
        self.set_status(
            f"Done. Stored query #{qid}. Fetched {len(stats)} assets in {elapsed:.2f}s."
        )
        self.btn_fetch_manual.config(state="normal")
        self.btn_load_csv.config(state="normal")
        self.btn_refresh_history.config(state="normal")
        self.refresh_history_list()

        errors = [s.row.get("Error") for s in stats if s.row.get("Error")]
        if errors:
            messagebox.showwarning(
                "Some tickers failed", f"{len(errors)} tickers failed. See 'Error' column."
            )

    def _fetch_failed(self, e: Exception) -> None:
        self._is_fetching = False
        messagebox.showerror("Fetch failed", str(e))
        self.set_status("Fetch failed.")
        self.btn_fetch_manual.config(state="normal")
        self.btn_load_csv.config(state="normal")
        self.btn_refresh_history.config(state="normal")

    def _populate_tree(self, tree: ttk.Treeview, rows: list[dict]) -> None:
        tree.delete(*tree.get_children())
        cols = tree["columns"]
        for r in rows:
            values = []
            for c in cols:
                v = r.get(c)
                if isinstance(v, float):
                    if c in ("1D %", "Dividend Yield"):
                        values.append(f"{v:.3f}")
                    elif c in ("Close", "Adj Close", "Trailing P/E", "Forward P/E"):
                        values.append(f"{v:.4f}")
                    else:
                        values.append(f"{v:.4f}")
                elif isinstance(v, int) and c in ("Volume", "Market Cap"):
                    values.append(f"{v:,}")
                else:
                    values.append("" if v is None else str(v))
            tree.insert("", "end", values=values)

    def refresh_history_list(self) -> None:
        self.history_list.delete(0, tk.END)
        self._history_index_map.clear()

        items = database.list_queries(self.conn)
        for qid, created_at, source, input_text in items:
            label = f"#{qid}  {created_at}  [{source}]  {input_text[:40]}"
            self.history_list.insert(tk.END, label)
            self._history_index_map.append(qid)

        if not items:
            self.history_list.insert(tk.END, "(no history yet)")

    def on_history_select(self, _event: Any = None) -> None:
        self.load_selected_history()

    def load_selected_history(self) -> None:
        sel = self.history_list.curselection()
        if not sel or not self._history_index_map:
            return
        idx = int(sel[0])
        if idx >= len(self._history_index_map):
            return
        qid = self._history_index_map[idx]
        tickers, rows = database.load_query_results(self.conn, qid)
        self._populate_tree(self.history_tree, rows)
        self.history_status_var.set(f"Loaded query #{qid} ({len(tickers)} tickers) from history")

    def on_clear_history(self) -> None:
        if self._is_fetching:
            messagebox.showwarning("Fetching Data", "Cannot clear history while fetching asset data. Try again later.")
            return

        if not messagebox.askyesno("Confirm", "Delete all query history? This cannot be undone."):
            return
        try:
            database.clear_all(self.conn)
            self.refresh_history_list()
            self.history_status_var.set("History cleared")
            self.history_tree.delete(*self.history_tree.get_children())
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def destroy(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
        super().destroy()


def main() -> None:
    app = AssetViewerApp()
    app.mainloop()


if __name__ == "__main__":
    main()