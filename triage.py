import os
import shutil
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import cv2  
from send2trash import send2trash 

# --- CONFIGURATION ---
SOURCE_DIR = r"E:\Downloaded_Pics\Download"
DEST_DIR = r"E:\Gate of Babylon"

# Supported file extensions
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.jfif', '.gif', '.webp', '.bmp', '.mp4', '.webm', '.mkv', '.avi')
VIDEO_FORMATS = ('.mp4', '.webm', '.mkv', '.avi')
# ---------------------

class ImageSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gate of Babylon - Triage System")
        
        self.root.geometry("1600x900")
        try:
            self.root.state("zoomed")
        except:
            pass 
            
        self.root.configure(bg="#1e1e1e")

        self.target_folders = [f.name for f in os.scandir(DEST_DIR) if f.is_dir()]
        self.images = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(SUPPORTED_FORMATS)]
        self.current_index = 0
        
        self.current_pil_image = None
        self.resize_timer = None
        self.is_fullscreen = False
        
        self.action_history = []

        if not self.target_folders:
            messagebox.showerror("Error", "No subfolders found in the target directory!")
            self.root.destroy()
            return
            
        if not self.images:
            messagebox.showinfo("Done", "No files found in the source directory!")
            self.root.destroy()
            return

        # --- MAIN LAYOUT (Draggable PanedWindow) ---
        self.paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashwidth=8, bg="#555", borderwidth=0)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        self.left_frame = tk.Frame(self.paned_window, bg="#1e1e1e")
        self.right_frame = tk.Frame(self.paned_window, bg="#2a2a2a")

        self.paned_window.add(self.left_frame, minsize=350, stretch="never")
        self.paned_window.add(self.right_frame, minsize=600, stretch="always")
        self.paned_window.paneconfigure(self.left_frame, width=420)

        # --- LEFT UI (Top Bar: Locked Info & Sorting) ---
        self.top_bar = tk.Frame(self.left_frame, bg="#1e1e1e")
        self.top_bar.pack(fill=tk.X, pady=10, padx=20)
        
        self.top_bar.columnconfigure(0, weight=1) 
        self.top_bar.columnconfigure(1, weight=0) 
        self.top_bar.columnconfigure(2, weight=0) 
        
        self.file_label = tk.Label(self.top_bar, text="", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="white", anchor="w")
        self.file_label.grid(row=0, column=0, sticky="w")

        self.progress_label = tk.Label(self.top_bar, text="", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="#2e8b57")
        self.progress_label.grid(row=0, column=1, sticky="e", padx=(10, 20))

        sort_frame = tk.Frame(self.top_bar, bg="#1e1e1e")
        sort_frame.grid(row=0, column=2, sticky="e")
        
        tk.Label(sort_frame, text="Sort By:", font=("Arial", 10), bg="#1e1e1e", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.sort_var = tk.StringVar()
        self.sort_combo = ttk.Combobox(sort_frame, textvariable=self.sort_var, state="readonly", width=15)
        self.sort_combo['values'] = ("Default", "Name (A-Z)", "Name (Z-A)", "Date (Newest)", "Date (Oldest)", "Size (Largest)", "Size (Smallest)")
        self.sort_combo.current(0)
        self.sort_combo.pack(side=tk.LEFT)
        self.sort_combo.bind("<<ComboboxSelected>>", self.apply_sort)

        # --- LEFT UI (Image Display) ---
        self.canvas = tk.Canvas(self.left_frame, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        self.canvas.bind("<Configure>", self._schedule_resize)

        # --- LEFT UI (Responsive Control Buttons) ---
        self.control_frame = tk.Frame(self.left_frame, bg="#1e1e1e")
        self.control_frame.pack(fill=tk.X, padx=20, pady=15)
        
        for i in range(5):
            self.control_frame.columnconfigure(i, weight=1, uniform="group1")

        self.btn_skip_b = tk.Button(self.control_frame, text="<- Skip Backward", command=lambda: self.skip_image(-1), font=("Arial", 11), bg="#444", fg="white", borderwidth=0, pady=8)
        self.btn_trash = tk.Button(self.control_frame, text="🗑️ Trash", command=self.delete_image, font=("Arial", 11, "bold"), bg="#8b0000", fg="white", borderwidth=0, pady=8)
        self.btn_undo = tk.Button(self.control_frame, text="↩️ Undo Move", command=self.undo_action, font=("Arial", 11, "bold"), bg="#b8860b", fg="white", borderwidth=0, pady=8)
        self.btn_zoom = tk.Button(self.control_frame, text="🔍 Zoom (Space)", command=self.quick_zoom, font=("Arial", 11, "bold"), bg="#2471a3", fg="white", borderwidth=0, pady=8)
        self.btn_skip_f = tk.Button(self.control_frame, text="Skip Forward ->", command=lambda: self.skip_image(1), font=("Arial", 11), bg="#444", fg="white", borderwidth=0, pady=8)

        self.btn_skip_b.grid(row=0, column=0, sticky="ew", padx=5)
        self.btn_trash.grid(row=0, column=1, sticky="ew", padx=5)
        self.btn_undo.grid(row=0, column=2, sticky="ew", padx=5)
        self.btn_zoom.grid(row=0, column=3, sticky="ew", padx=5)
        self.btn_skip_f.grid(row=0, column=4, sticky="ew", padx=5)

        self._add_hover_effect(self.btn_skip_b, "#444", "#666")
        self._add_hover_effect(self.btn_trash, "#8b0000", "#b30000")
        self._add_hover_effect(self.btn_undo, "#b8860b", "#daa520")
        self._add_hover_effect(self.btn_zoom, "#2471a3", "#2980b9")
        self._add_hover_effect(self.btn_skip_f, "#444", "#666")

        self.buttons_compact = False 
        self.control_frame.bind("<Configure>", self._update_button_text)

        # --- RIGHT UI (Scrollable Button Grid) ---
        self.button_canvas = tk.Canvas(self.right_frame, bg="#2a2a2a", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.right_frame, orient="vertical", command=self.button_canvas.yview)
        self.scrollable_frame = tk.Frame(self.button_canvas, bg="#2a2a2a")

        self.button_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.button_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.button_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=15)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.folder_buttons = []
        for folder in sorted(self.target_folders):
            bg_color = self._get_button_color(folder)
            btn = tk.Button(
                self.scrollable_frame, 
                text=folder, 
                font=("Arial", 10, "bold"), 
                bg=bg_color, 
                fg="white", 
                activebackground="#ffffff", 
                activeforeground="black",
                borderwidth=0,
                width=20, 
                pady=8,
                command=lambda f=folder: self.move_image(f)
            )
            self._add_hover_effect(btn, bg_color, "#555555") 
            self.folder_buttons.append(btn)

        self.current_columns = 0 
        
        self.button_canvas.bind("<Configure>", self._reflow_buttons)
        self.scrollable_frame.bind("<Configure>", self._check_scrollbar)

        # --- KEY BINDINGS ---
        self.root.bind("<Right>", lambda e: self.skip_image(1))
        self.root.bind("<Left>", lambda e: self.skip_image(-1))
        self.root.bind("<Delete>", lambda e: self.delete_image())
        self.root.bind("<Control-z>", lambda e: self.undo_action()) 
        self.root.bind("<space>", lambda e: self.quick_zoom()) 
        
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind("<F12>", lambda e: self.root.iconify())

        self.root.update()
        self.load_image()

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self, event=None):
        self.is_fullscreen = False
        self.root.attributes("-fullscreen", False)

    def _check_scrollbar(self, event=None):
        self.button_canvas.configure(scrollregion=self.button_canvas.bbox("all"))
        
        req_height = self.scrollable_frame.winfo_reqheight()
        canvas_height = self.button_canvas.winfo_height()

        if req_height > canvas_height:
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.button_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        else:
            if self.scrollbar.winfo_ismapped():
                self.scrollbar.pack_forget()
            self.button_canvas.unbind_all("<MouseWheel>")

    def _update_button_text(self, event):
        threshold = 600 
        
        if event.width < threshold and not self.buttons_compact:
            self.btn_skip_b.config(text="⬅️")
            self.btn_trash.config(text="🗑️")
            self.btn_undo.config(text="↩️")
            self.btn_zoom.config(text="🔍")
            self.btn_skip_f.config(text="➡️")
            self.buttons_compact = True
        elif event.width >= threshold and self.buttons_compact:
            self.btn_skip_b.config(text="<- Skip Backward")
            self.btn_trash.config(text="🗑️ Trash")
            self.btn_undo.config(text="↩️ Undo Move")
            self.btn_zoom.config(text="🔍 Zoom (Space)")
            self.btn_skip_f.config(text="Skip Forward ->")
            self.buttons_compact = False

    def _add_hover_effect(self, button, default_color, hover_color):
        button.bind("<Enter>", lambda e: button.config(bg=hover_color))
        button.bind("<Leave>", lambda e: button.config(bg=default_color))

    def apply_sort(self, event=None):
        sort_mode = self.sort_combo.get()
        
        def get_path(filename):
            return os.path.join(SOURCE_DIR, filename)

        try:
            if sort_mode == "Name (A-Z)":
                self.images.sort(key=lambda x: x.lower())
            elif sort_mode == "Name (Z-A)":
                self.images.sort(key=lambda x: x.lower(), reverse=True)
            elif sort_mode == "Date (Newest)":
                self.images.sort(key=lambda x: os.path.getmtime(get_path(x)), reverse=True)
            elif sort_mode == "Date (Oldest)":
                self.images.sort(key=lambda x: os.path.getmtime(get_path(x)))
            elif sort_mode == "Size (Largest)":
                self.images.sort(key=lambda x: os.path.getsize(get_path(x)), reverse=True)
            elif sort_mode == "Size (Smallest)":
                self.images.sort(key=lambda x: os.path.getsize(get_path(x)))
            
            self.current_index = 0
            self.action_history.clear()
            self.load_image()
            
        except Exception as e:
            messagebox.showerror("Sorting Error", f"Failed to sort files:\n{e}")

    def _get_button_color(self, folder_name):
        palette = [
            "#4A235A", "#154360", "#0E6251", "#145A32", "#935116", "#78281F", 
            "#2C3E50", "#7D3C98", "#2471A3", "#1E8449", "#A04000", "#B03A2E"
        ]
        first_char = folder_name.strip()[0].upper() if folder_name.strip() else 'A'
        idx = ord(first_char) % len(palette)
        return palette[idx]

    def _reflow_buttons(self, event):
        btn_width_estimate = 175 
        cols = max(1, event.width // btn_width_estimate)
        
        if cols != self.current_columns:
            self.current_columns = cols
            for i, btn in enumerate(self.folder_buttons):
                btn.grid(row=i // cols, column=i % cols, padx=5, pady=5)
            
            self.root.after(50, self._check_scrollbar)

    def _on_mousewheel(self, event):
        self.button_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def load_image(self):
        if self.current_index >= len(self.images):
            messagebox.showinfo("Complete", "All files sorted!")
            self.root.destroy()
            return

        file_name = self.images[self.current_index]
        
        display_name = file_name
        name, ext = os.path.splitext(file_name)
        if len(name) > 25: 
            display_name = f"{name[:22]}...{ext}"
            
        self.file_label.config(text=f"File: {display_name}")
        self.progress_label.config(text=f"Progress: {self.current_index + 1} / {len(self.images)}")
        
        file_path = os.path.join(SOURCE_DIR, file_name)
        ext = os.path.splitext(file_name)[1].lower()
        
        try:
            if ext in VIDEO_FORMATS:
                cap = cv2.VideoCapture(file_path)
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000) 
                ret, frame = cap.read()
                
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()

                if ret:
                    cv2_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(cv2_im)
                else:
                    img = Image.new('RGB', (400, 300), color='#333333')
                cap.release()
            else:
                img = Image.open(file_path)
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    bg = Image.new('RGB', img.size, '#1e1e1e')
                    bg.paste(img.convert('RGBA'), (0, 0), img.convert('RGBA'))
                    img = bg
                else:
                    img = img.convert('RGB')
            
            self.current_pil_image = img
            self.render_image()
            
        except Exception as e:
            print(f"Error loading {file_name}: {e}")
            self.skip_image(1) 

    def _schedule_resize(self, event):
        if self.resize_timer:
            self.root.after_cancel(self.resize_timer)
        self.resize_timer = self.root.after(100, self.render_image)

    def render_image(self):
        if not self.current_pil_image:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1: canvas_width = 800
        if canvas_height <= 1: canvas_height = 500
            
        img_copy = self.current_pil_image.copy()
        img_copy.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        
        self.tk_img = ImageTk.PhotoImage(img_copy)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width//2, canvas_height//2, anchor=tk.CENTER, image=self.tk_img)

    # --- UPDATED: Safe Move Logic to prevent overwriting ---
    def move_image(self, target_folder):
        if self.current_index >= len(self.images):
            return

        original_file_name = self.images[self.current_index]
        src_path = os.path.join(SOURCE_DIR, original_file_name)
        base_dest_path = os.path.join(DEST_DIR, target_folder, original_file_name)

        final_dest_path = base_dest_path
        final_file_name = original_file_name
        counter = 1

        # If file exists, append a number exactly like Windows (e.g., "image (1).jpg")
        while os.path.exists(final_dest_path):
            name, ext = os.path.splitext(original_file_name)
            final_file_name = f"{name} ({counter}){ext}"
            final_dest_path = os.path.join(DEST_DIR, target_folder, final_file_name)
            counter += 1

        try:
            shutil.move(src_path, final_dest_path)
            
            if counter > 1:
                print(f"Moved & Renamed: {original_file_name} -> {target_folder}/{final_file_name}")
            else:
                print(f"Moved: {original_file_name} -> {target_folder}")
            
            self.action_history.append({
                "action": "move",
                "file_name": original_file_name, 
                "original_path": src_path,
                "current_path": final_dest_path, # We track the NEW name here for Undo
                "index": self.current_index
            })
            
            del self.images[self.current_index]
            self.load_image()
        except Exception as e:
            messagebox.showerror("Error", f"Could not move file:\n{e}")

    def delete_image(self):
        if self.current_index >= len(self.images):
            return

        file_name = self.images[self.current_index]
        file_path = os.path.join(SOURCE_DIR, file_name)

        try:
            send2trash(file_path)
            print(f"Sent to Recycle Bin: {file_name}")
            
            del self.images[self.current_index]
            self.load_image()
        except Exception as e:
            messagebox.showerror("Error", f"Could not trash file:\n{e}")

    # --- UPDATED: Undo seamlessly handles renames ---
    def undo_action(self):
        if not self.action_history:
            print("Nothing to undo! (Note: Recycle Bin deletions cannot be undone in-app)")
            return
            
        last_action = self.action_history.pop()
        
        if last_action["action"] == "move":
            try:
                # Moves the renamed file out of the folder and restores its original name in Downloads
                shutil.move(last_action["current_path"], last_action["original_path"])
                print(f"Undo: Restored {last_action['file_name']}")
                
                self.images.insert(last_action["index"], last_action["file_name"])
                self.current_index = last_action["index"]
                
                self.load_image()
            except Exception as e:
                messagebox.showerror("Undo Error", f"Could not undo action:\n{e}")

    def quick_zoom(self):
        if self.current_index >= len(self.images):
            return
        
        file_name = self.images[self.current_index]
        file_path = os.path.join(SOURCE_DIR, file_name)
        
        try:
            os.startfile(file_path)
        except Exception as e:
            print(f"Could not quick-zoom file: {e}")

    def skip_image(self, direction):
        if 0 <= self.current_index + direction < len(self.images):
            self.current_index += direction
            self.load_image()

if __name__ == "__main__":
    root = tk.Tk()
    root.update_idletasks()
    app = ImageSorterApp(root)
    root.mainloop()