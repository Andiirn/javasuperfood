import customtkinter as ctk
import json
import time
import random
import datetime
import os
import pandas as pd
import threading
import sys
import subprocess
from playwright.sync_api import sync_playwright
from tkinter import messagebox # Untuk menggantikan input() terminal
import multiprocessing

# WAJIB untuk Windows EXE agar tidak terbuka dua kali
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Konfigurasi Tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ShopeeScraperUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Java Shopee Scraper")
        self.geometry("600x650")

        # --- Variabel ---
        self.SESSION_FILE = "session.json"
        self.ITEM_PER_PAGE = 20

        # --- UI Layout ---
        self.grid_columnconfigure(0, weight=1)
        
        self.label_header = ctk.CTkLabel(self, text="Shopee Data Scraper", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_header.pack(pady=20)

        # Frame Input
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=20, fill="x")

        self.label_kw = ctk.CTkLabel(self.input_frame, text="Keyword Pencarian:")
        self.label_kw.pack(pady=(10, 0))
        self.entry_kw = ctk.CTkEntry(self.input_frame, placeholder_text="Contoh: kimchi", width=300)
        self.entry_kw.pack(pady=5)

        self.label_page = ctk.CTkLabel(self.input_frame, text="Jumlah Halaman (Max Page):")
        self.label_page.pack(pady=(10, 0))
        self.entry_page = ctk.CTkEntry(self.input_frame, placeholder_text="Contoh: 1", width=100)
        self.entry_page.insert(0, "1") # Default 1
        self.entry_page.pack(pady=5)

        # Tombol
        self.btn_run = ctk.CTkButton(self, text="MULAI SCRAPING", command=self.start_thread, 
                                     fg_color="#ee4d2d", hover_color="#ff5722", height=40, font=ctk.CTkFont(weight="bold"))
        self.btn_run.pack(pady=20)

        # Log Box
        self.log_label = ctk.CTkLabel(self, text="Status/Log:")
        self.log_label.pack(anchor="w", padx=30)
        self.log_box = ctk.CTkTextbox(self, height=200, width=540)
        self.log_box.pack(pady=5, padx=20)
        self.log_box.configure(state="disabled")

    def write_log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.update_idletasks()

    def check_browser(self):
        self.write_log("Checking browser engine...")
        try:
            # Perintah ini akan mendownload chromium jika belum ada
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], capture_output=True, check=True)
            self.write_log("✅ Browser engine ready.")
        except Exception as e:
            self.write_log(f"❌ Gagal menyiapkan browser: {e}")

    def human_delay(self, a=1.2, b=2.8):
        time.sleep(random.uniform(a, b))

    def save_session(self, context):
        context.storage_state(path=self.SESSION_FILE)
        self.write_log("✅ Session saved!")

    def start_thread(self):
        # Jalankan scraping di background dengan daemon=True agar ikut mati jika GUI ditutup
        t = threading.Thread(target=self.main_logic, daemon=True)
        t.start()

    def main_logic(self):
        # Ambil input dari UI
        KEYWORD = self.entry_kw.get()
        if not KEYWORD:
            self.write_log("⚠️ Error: Keyword tidak boleh kosong!")
            return

        try:
            MAX_PAGE = int(self.entry_page.get())
        except ValueError:
            self.write_log("⚠️ Input halaman tidak valid, menggunakan default: 1")
            MAX_PAGE = 1

        self.btn_run.configure(state="disabled", text="SEDANG BERJALAN...")
        
        try:
            self.check_browser()
            
            # Memaksa Playwright mencari browser di folder permanen user
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.environ["LOCALAPPDATA"], "ms-playwright")
            
            with sync_playwright() as p:
                self.write_log("🚀 Launching browser...")
                
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--disable-notifications",
                        "--no-sandbox"
                    ]
                )

                # ================= SESSION =================
                session_exists = os.path.exists(self.SESSION_FILE)
                config_context = {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                    "locale": "id-ID",
                    "timezone_id": "Asia/Jakarta"
                }

                if session_exists:
                    try:
                        context = browser.new_context(storage_state=self.SESSION_FILE, **config_context)
                        self.write_log("🔄 Loaded previous session")
                    except:
                        self.write_log("⚠️ Failed to load session, create new")
                        context = browser.new_context(**config_context)
                        session_exists = False
                else:
                    context = browser.new_context(**config_context)

                page = context.new_page()
                page.goto("https://shopee.co.id/", timeout=60000)

                if not session_exists:
                    self.write_log("🔐 LOGIN MANUAL DIBUTUHKAN!")
                    self.write_log("👉 Silahkan login di jendela browser yang terbuka.")
                    
                    # POP-UP menggantikan input() terminal
                    messagebox.showinfo("Login Shopee", "Silahkan login di browser sampai masuk Beranda.\n\nJika sudah sukses login, Klik OK pada kotak ini.")
                    
                    self.save_session(context)
                
                self.human_delay()

                # ================= SCRAPE =================
                self.write_log(f"🔍 Searching: {KEYWORD}")
                all_items = []

                for page_idx in range(MAX_PAGE):
                    newest = page_idx * self.ITEM_PER_PAGE
                    self.write_log(f"📄 Scraping Page {page_idx + 1}...")

                    data = page.evaluate(
                        """async ({ keyword, newest }) => {
                            const url = `/api/v4/search/search_items?by=relevancy&keyword=${encodeURIComponent(keyword)}&limit=20&newest=${newest}&page_type=search&scenario=PAGE_GLOBAL_SEARCH`;
                            const res = await fetch(url, { method: "GET", credentials: "include" });
                            return await res.json();
                        }""",
                        {"keyword": KEYWORD, "newest": newest}
                    )

                    if "items" not in data or not data["items"]:
                        self.write_log("❌ Search diblok / Tidak ada data.")
                        break

                    for it in data["items"]:
                        item = it.get("item_basic")
                        if not item: continue

                        monthly_sold = item.get("sold", 0)
                        total_sold = item.get("historical_sold", 0)
                        if monthly_sold is None: monthly_sold = 0
                        weekly_sold = int(monthly_sold / 4)

                        image_id = item.get("image", "")
                        image_url = f"https://down-id.img.susercontent.com/file/{image_id}"
                        clean_name = "".join(c if c.isalnum() else "-" for c in item["name"])
                        product_url = f"https://shopee.co.id/{clean_name}-i.{item['shopid']}.{item['itemid']}"

                        all_items.append({
                            "itemid": item["itemid"],
                            "shopid": item["shopid"],
                            "name": item["name"],
                            "price": item["price"] / 100000,
                            "monthly_sold": monthly_sold,
                            "weekly_sold": weekly_sold,
                            "total_sold": total_sold,
                            "shop_name": item.get("shop_name"),
                            "location": item.get("shop_location"),
                            "image": image_url,
                            "product_url": product_url,
                            "scraped_at": datetime.datetime.now().strftime("%Y-%m-%d")
                        })
                    self.human_delay(1, 3)

                # ================= SAVE =================
                if all_items:
                    json_file = f"{KEYWORD}_data.json"
                    xlsx_file = f"{KEYWORD}_data.xlsx"
                    
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(all_items, f, indent=2, ensure_ascii=False)

                    df = pd.DataFrame(all_items)
                    df.to_excel(xlsx_file, index=False)

                    self.write_log(f"✅ Berhasil menyimpan {len(all_items)} item!")
                    self.write_log(f"📁 {xlsx_file}")
                
                browser.close()
                self.write_log("🎉 Selesai!")

        except Exception as e:
            self.write_log(f"❌ Error: {str(e)}")
        
        self.btn_run.configure(state="normal", text="MULAI SCRAPING")

if __name__ == "__main__":
    app = ShopeeScraperUI()
    app.mainloop()