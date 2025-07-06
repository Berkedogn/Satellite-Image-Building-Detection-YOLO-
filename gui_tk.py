import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ImageTk
from detector import load_model, detect_objects
from image_utils import draw_boxes  # Kutuları çizmek için
from config import OUTPUT_FOLDER, CONFIDENCE_THRESHOLD
import os
import csv
import cv2

class SatelliteDetectionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Uydu Görüntüsü Nesne Tespiti")
        self.geometry("1000x700")
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Temalar
        self.themes = {
            "Light": {"bg": "#f2f2f2", "fg": "#000000"},
            "Dark": {"bg": "#2b2b2b", "fg": "#ffffff"}
        }
        self.current_theme = "Light"
        self.style = ttk.Style(self)

        # Menü, toolbar, içerik, status
        self.create_menu()
        self.create_toolbar()
        self.create_main_frames()
        self.create_status_frames()

        # Model ve durum
        self.model = None
        self.load_model()
        self.image_list = []
        self.current_index = -1
        self.last_output = None
        self.apply_theme()

        # Ölçek faktörü: 1 piksel = 0.05m, dolayısıyla alan dönüşüm = 0.05*0.05 = 0.0025 m²
        self._m2_per_px2 = 0.05 * 0.05

    def create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Görsel Aç...", command=self.open_image)
        file_menu.add_command(label="Klasör Aç...", command=self.open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış", command=self.on_exit)
        menubar.add_cascade(label="Dosya", menu=file_menu)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Model Seç...", command=self.select_model)
        settings_menu.add_command(label="Eşik Ayarla...", command=self.set_confidence)
        menubar.add_cascade(label="Ayarlar", menu=settings_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Light Mode", command=lambda: self.change_theme("Light"))
        view_menu.add_command(label="Dark Mode", command=lambda: self.change_theme("Dark"))
        view_menu.add_separator()
        view_menu.add_command(label="Orijinal Görseli Görüntüle", command=self.show_original_popup)
        view_menu.add_command(label="Tespit Sonrası Görüntüyü Görüntüle", command=self.show_result_popup)
        menubar.add_cascade(label="Görünüm", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Hakkında", command=self.show_about)
        menubar.add_cascade(label="Yardım", menu=help_menu)

        self.config(menu=menubar)

    def create_toolbar(self):
        toolbar = ttk.Frame(self)
        ttk.Button(toolbar, text="◀ Önceki", command=self.prev_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="▶ Sonraki", command=self.next_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Tespiti Başlat", command=self.run_detection).pack(side=tk.LEFT, padx=10)
        ttk.Button(toolbar, text="Geri Al", command=self.undo_last_action).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Yeniden Başlat", command=self.restart_app).pack(side=tk.LEFT, padx=2)
        toolbar.pack(fill=tk.X)

    def create_main_frames(self):
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Orijinal Görsel
        self.orig_canvas = tk.Label(frame, bg="#ddd")
        self.orig_canvas.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        # Sonuç Görsel
        self.res_canvas = tk.Label(frame, bg="#ddd")
        self.res_canvas.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        # Bilgi Paneli
        info_frame = ttk.Frame(frame)
        info_frame.grid(row=0, column=2, sticky="ns", padx=5)
        ttk.Label(info_frame, text="Tespit Bilgileri").pack(pady=5)

        # Sütunlara ID ve P.Alan (m²) ekledik
        columns = ("ID", "Sınıf", "Güven", "x1", "y1", "x2", "y2", "P.Alan (m²)")
        self.tree = ttk.Treeview(info_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=(50 if col == "ID" else 80))
        self.tree.pack(fill=tk.Y)

    def create_status_frames(self):
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        self.progress = ttk.Progressbar(status_frame, orient='horizontal', mode='determinate')
        self.progress.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.log_box = tk.Text(status_frame, height=4)
        self.log_box.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=5)

    def log(self, msg):
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)

    def apply_theme(self):
        colors = self.themes[self.current_theme]
        self.configure(bg=colors['bg'])
        for widget in self.winfo_children():
            try:
                widget.configure(bg=colors['bg'], fg=colors['fg'])
            except:
                pass

    def change_theme(self, theme):
        self.current_theme = theme
        self.apply_theme()
        self.log(f"🌓 Tema değiştirildi: {theme}")

    def load_model(self):
        self.log("🔍 Model yükleniyor...")
        try:
            self.model = load_model()
            self.log("✅ Model yüklendi.")
        except Exception as e:
            self.log(f"❌ Model yüklenemedi: {e}")

    def select_model(self):
        path = filedialog.askopenfilename(title="Model Seç", filetypes=[("PyTorch Model","*.pt")])
        if path:
            from config import MODEL_PATH
            MODEL_PATH = path
            self.load_model()

    def set_confidence(self):
        val = simpledialog.askfloat("Eşik Değeri", "Güven eşiği (0-1):", initialvalue=CONFIDENCE_THRESHOLD)
        if val is not None:
            from config import CONFIDENCE_THRESHOLD
            CONFIDENCE_THRESHOLD = val
            self.log(f"⚙️ Güven eşiği ayarlandı: {val}")

    def open_image(self):
        self.progress.start()
        file = filedialog.askopenfilename(filetypes=[("Image files","*.jpg *.png *.jpeg")])
        if file:
            self.image_list = [file]
            self.current_index = 0
            self.progress['maximum'] = 1
            self.progress['value'] = 0
            self.display_image(file)
            self.log(f"📷 Görsel açıldı: {file}")
        self.progress.stop()

    def open_folder(self):
        self.progress.start()
        folder = filedialog.askdirectory()
        if folder:
            exts = ('.jpg','.png','.jpeg')
            self.image_list = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith(exts)
            ]
            self.current_index = 0
            self.progress['maximum'] = len(self.image_list)
            self.log(f"📁 Klasör açıldı: {folder} ({len(self.image_list)} dosya)")
            if self.image_list:
                self.display_image(self.image_list[0])
        self.progress.stop()

    def display_image(self, path):
        img = Image.open(path)
        max_w = self.orig_canvas.winfo_width() or 600
        max_h = self.orig_canvas.winfo_height() or 600
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        self.tk_orig = ImageTk.PhotoImage(img)
        self.orig_canvas.config(image=self.tk_orig)
        self.res_canvas.config(image='')
        self.tree.delete(*self.tree.get_children())

    def prev_image(self):
        if self.image_list and self.current_index > 0:
            self.current_index -= 1
            self.display_image(self.image_list[self.current_index])
            self.progress['value'] = self.current_index
            self.log(f"◀ Önceki: {self.image_list[self.current_index]}")

    def next_image(self):
        if self.image_list and self.current_index < len(self.image_list)-1:
            self.current_index += 1
            self.display_image(self.image_list[self.current_index])
            self.progress['value'] = self.current_index
            self.log(f"▶ Sonraki: {self.image_list[self.current_index]}")

    def run_detection(self):
        if not self.image_list:
            messagebox.showwarning("Uyarı","Önce görsel veya klasör açın.")
            return
        total = len(self.image_list)
        self.progress.start()
        self.progress['value'] = 0
        # Txt log dosyasını hazırla
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        log_path = os.path.join(OUTPUT_FOLDER, "log.txt")
        with open(log_path, 'a') as log_file:
            log_file.write(f"--- Yeni Tespit: {self.image_list[self.current_index]} ---\n")
            for idx, path in enumerate(self.image_list, start=1):
                self.log(f"🚀 Tespit {idx}/{total}: {path}")
                results = detect_objects(self.model, path)
                output = draw_boxes(path, results, self.model)
                self.last_output = output
                self.update_tree(results)
                self.display_result(output)
                # Her bbox'u log dosyasına yaz
                boxes = results[0].boxes.xyxy.cpu().numpy()
                classes = results[0].boxes.cls.cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()
                for i, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs), start=1):
                    x1,y1,x2,y2 = map(int, box)
                    px_area = (x2-x1)*(y2-y1)
                    real_m2 = px_area * self._m2_per_px2
                    log_file.write(
                        f"ID:{i}, Class:{self.model.names[int(cls_id)]}, "
                        f"Conf:{conf:.2f}, BBox:[{x1},{y1},{x2},{y2}], "
                        f"P.Alan:{real_m2:.2f} m2\n"
                    )
                self.progress['value'] = idx
            log_file.write("\n")
        self.progress.stop()
        self.save_csv()
        self.log("✅ Tüm tespitler tamamlandı.\nLog dosyasına kaydedildi.")

    def update_tree(self, results):
        self.tree.delete(*self.tree.get_children())
        for idx, r in enumerate(results[0].boxes.xyxy.cpu().numpy(), start=1):
            cls_id = results[0].boxes.cls.cpu().numpy()[idx-1]
            conf = results[0].boxes.conf.cpu().numpy()[idx-1]
            x1,y1,x2,y2 = map(int, r)
            pixel_area = (x2-x1)*(y2-y1)
            real_m2 = pixel_area * self._m2_per_px2
            self.tree.insert(
                '', tk.END,
                values=(
                    idx,
                    self.model.names[int(cls_id)],
                    f"{conf:.2f}",
                    x1, y1, x2, y2,
                    f"{real_m2:.2f}"
                )
            )

    def display_result(self, path):
        img = Image.open(path)
        max_w = self.res_canvas.winfo_width() or 600
        max_h = self.res_canvas.winfo_height() or 600
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        self.tk_res = ImageTk.PhotoImage(img)
        self.res_canvas.config(image=self.tk_res)

    def undo_last_action(self):
        if self.last_output:
            self.res_canvas.config(image='')
            self.tree.delete(*self.tree.get_children())
            self.log("↩️ Son tespit geri alındı.")
        else:
            self.log("⚠️ Geri alınacak tespit bulunamadı.")

    def restart_app(self):
        self.image_list = []
        self.current_index = -1
        self.last_output = None
        self.orig_canvas.config(image='')
        self.res_canvas.config(image='')
        self.tree.delete(*self.tree.get_children())
        self.progress['value'] = 0
        self.log_box.delete(1.0, tk.END)
        self.log("🔄 Uygulama sıfırlandı.")

    def show_original_popup(self):
        if self.current_index < 0 or not self.image_list:
            messagebox.showwarning("Uyarı","Öncelikle bir görsel açın.")
            return
        self._show_image_popup(self.image_list[self.current_index], "Orijinal Görsel")

    def show_result_popup(self):
        if not self.last_output:
            messagebox.showwarning("Uyarı","Öncelikle tespit yapın.")
            return
        self._show_image_popup(self.last_output, "Tespit Sonrası Görsel")

    def _show_image_popup(self, path, title):
        popup = tk.Toplevel(self)
        popup.title(title)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        img = Image.open(path)
        img.thumbnail((sw*0.8, sh*0.8), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        lbl = tk.Label(popup, image=tk_img)
        lbl.image = tk_img
        lbl.pack()

    def save_csv(self):
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        csv_path = os.path.join(OUTPUT_FOLDER, "detection_results.csv")
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Image","ID","Class","Confidence","x1","y1","x2","y2","P.Alan (m²)"])
            for path in self.image_list:
                results = detect_objects(self.model, path)
                boxes = results[0].boxes.xyxy.cpu().numpy()
                classes = results[0].boxes.cls.cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()
                for i, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs), start=1):
                    x1,y1,x2,y2 = map(int, box)
                    px_area = (x2-x1)*(y2-y1)
                    real_m2 = px_area * self._m2_per_px2
                    writer.writerow([
                        os.path.basename(path),
                        i,
                        self.model.names[int(cls_id)],
                        f"{conf:.2f}",
                        x1, y1, x2, y2,
                        f"{real_m2:.2f}"
                    ])
        self.log(f"📊 Sonuçlar CSV olarak kaydedildi: {csv_path}")

    def show_about(self):
        messagebox.showinfo("Hakkında",
            "Uydu Görüntüsü Nesne Tespiti v1.0\nGeliştirici: Berke DOĞAN"
        )

    def on_exit(self):
        if messagebox.askokcancel("Çıkış",
            "Uygulamadan çıkmak istediğinize emin misiniz?"):
            self.destroy()

if __name__ == "__main__":
    app = SatelliteDetectionApp()
    app.mainloop()
